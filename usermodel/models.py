import datetime
import hashlib
import string
import urllib
import uuid
from django.db.models import Q
from django.db.models.signals import pre_delete
from django.dispatch import receiver

import pytz

from django.utils.safestring import mark_safe
from django.contrib.auth.models import (AbstractBaseUser, BaseUserManager,
                                        Group, PermissionsMixin)
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.core.validators import MaxValueValidator, MinValueValidator
from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.importlib import import_module
from django.utils.translation import ugettext_lazy as _

# from django.conf.settings import GRAVATAR_URL_PREFIX, GRAVATAR_URL_DEFAULT
# from registration import signals as custom_signals
# from mymessages.models import Message, MessageInfo
# from universal.helpers import get_domain, send_email

BAD_EMAIL = ['dropped', 'bounce']
STOP_SENDING = ['unsubscribe', 'spamreport']
DEACTIVE_TYPES_AND_NONE = ['none'] + BAD_EMAIL + STOP_SENDING


class CustomUserManager(BaseUserManager):
    # Characters used for passwor generation with ambiguous ones ignored.
    # string.strip() doesn't play nicely with quote characters...
    ALLOWED_CHARS = string.printable.translate(
        None, """iloILO01!<>{}()[]|^"'`,.:;~-_/\\\t\n\r\x0b\x0c """)

    def get_email_owner(self, email, only_verified=False):
        """
        Tests if the specified email is already in use.

        Inputs:
        :email: String representation of email to be checked
        :only_verified: Only check verified secondary addresses; Default: False

        Outputs:
        :user: User object if one exists; None otherwise
        """
        try:
            user = self.get(email__iexact=email)
        except User.DoesNotExist:
            prefix = 'profileunits__secondaryemail__%s'
            search = {prefix % 'email__iexact': email}
            if only_verified:
                search[prefix % 'verified'] = True
            # try:
            #     user = self.get(**search)
            # except User.DoesNotExist:
            user = None
        return user

    def make_random_password(self, length=8, allowed_chars=None):
        """
        Like django's built-in `make_random_password`, but with a default of
        8 characters, a larger character set, and validation.
        """
        password = ''
        allowed_chars = allowed_chars or self.ALLOWED_CHARS
        # continue to generate a new password until all constriants are met
        while not all(set(password).intersection(getattr(string, category))
                      for category in ['ascii_lowercase', 'ascii_uppercase',
                                       'digits', 'punctuation']):
            password = super(CustomUserManager, self).make_random_password(
                length=length, allowed_chars=allowed_chars)

        return password

    def create_user_by_type(self, **kwargs):
        """
        Creates users by user type (normal or superuser). If a user
        already exists

        Inputs (all kwargs):
        :email: Email for this account; required
        :send_email: Boolean defaulted to true to signal that an email needs to
            be sent
        :request: HttpRequest instance used to pull cookies related to creation
            source
        :user_type: String, must be either normal or superuser
        Additionally accepts values for all fields on the User model

        Outputs:
        :user: User object instance
        :created: Boolean indicating whether a new user was created
        """
        email = kwargs.get('email')
        if not email:
            raise ValueError('Email address required.')

        user_type = kwargs.get('user_type', 'normal')
        if user_type not in ['superuser', 'normal']:
            raise ValueError('Bad user_type: %s' % user_type)

        user = self.get_email_owner(email)
        created = False
        if user is None:
            email = self.normalize_email(email)
            user_args = {'email': email,
                         'gravatar': '',
                         'timezone': settings.TIME_ZONE,
                         'is_active': True,
                         'in_reserve': kwargs.get('in_reserve', False)
                         }

            if user_type == 'superuser':
                user_args.update({'is_staff': True, 'is_superuser': True})
            password_fields = ['password', 'password1']
            for password_field in password_fields:
                password = kwargs.get(password_field)
                if password:
                    break
            create_password = False
            if not password:
                create_password = True
                user_args['password_change'] = True
                password = self.make_random_password()

            kwarg_source = kwargs.get('source')
            request = kwargs.get('request')
            if request:
                last_microsite_source = request.COOKIES.get('lastmicrosite')
                request_source = request.GET.get('source')
            else:
                last_microsite_source = None
                request_source = None

            if kwarg_source:
                user_args['source'] = kwarg_source
            elif request_source:
                user_args['source'] = request_source
            elif last_microsite_source:
                user_args['source'] = last_microsite_source
            elif hasattr(settings, 'SITE') and settings.SITE:
                user_args['source'] = settings.SITE.domain

            user = self.model(**user_args)
            user.set_password(password)
            user.make_guid()
            user.full_clean()
            user.save()
            user.add_default_group()
            # custom_signals.email_created.send(sender=self, user=user,
            #                                   email=email)
            # send_email = kwargs.get('send_email', False)
            # if send_email:
            #     custom_msg = kwargs.get("custom_msg", None)
            #     activation_args = {
            #         'sender': self,
            #         'user': user,
            #         'email': email,
            #         'custom_msg': custom_msg,
            #     }
            #     if create_password:
            #         activation_args['password'] = password
            #     custom_signals.send_activation.send(**activation_args)

            created = True
        return user, created

    def create_user(self, **kwargs):
        """
        Creates an already activated user.

        """
        return self.create_user_by_type(user_type='normal', **kwargs)

    def create_superuser(self, **kwargs):
        user, _ = self.create_user_by_type(user_type='superuser', **kwargs)
        return user

    def not_disabled(self, user):
        """
        Used by the user_passes_test decorator to set view permissions.
        The user_passes_test method, passes in the user from the request,
        and gives permission to access the view if the value returned is true.
        This returns true as long as the user hasn't disabled their account.
        """

        if user.is_anonymous():
            return False
        else:
            return not user.is_disabled

    def is_verified(self, user):
        """
        Used by the user_passes_test decorator to set view permissions
        """

        if user.is_anonymous():
            return False
        else:
            return user.is_verified

    def is_group_member(self, user, group):
        """
        Used by the user_passes_test decorator to determine if the user's group
        membership is adequate for certain actions

        Example usage:
        Determine if user is in the 'Job Seeker' group:
        @user_passes_test(lambda u: User.objects.is_group_member(u, 'Job Seeker'))

        Inputs:
        :user: User instance, passed by the user_passes_test decorator
        :group: Name of the group that is being tested for

        Outputs:
        :is_member: Boolean representing the user's membership status
        """
        return user.groups.filter(name=group).count() >= 1
    






# New in Django 1.5. This is now the default auth user table.
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(verbose_name=_("email address"),
                              max_length=255, unique=True, db_index=True)
    date_joined = models.DateTimeField(_('date joined'), auto_now_add=True)
    gravatar = models.EmailField(verbose_name=_("gravatar email"),
                                 max_length=255, db_index=True, blank=True)

    profile_completion = models.IntegerField(validators=[MaxValueValidator(100),
                                                         MinValueValidator(0)],
                                             blank=False, default=0)

    # Permission Levels
    is_staff = models.BooleanField(_('staff status'), default=False,
                                   help_text=_("Designates whether the user "
                                               "can log into this admin site."))
    is_active = models.BooleanField(_('active'), default=True,
                                    help_text=_("Designates whether this "
                                                "corresponds to a valid"
                                                "email address. Deselect this"
                                                "instead of deleting "
                                                "accounts."))
    is_disabled = models.BooleanField(_('disabled'), default=False)
    is_verified = models.BooleanField(_('verified'),
                                      default=False,
                                      help_text=_("User has verified this "
                                                  "address and can access "
                                                  "most My.jobs features. "
                                                  "Deselect this instead of "
                                                  "deleting accounts."))
    in_reserve = models.BooleanField(_('reserved'), default=False,
                                     editable=False,
                                     help_text=_("This user will be held in "
                                                 "reserve until any "
                                                 "invitations associated "
                                                 "with it are processed."))

    # Communication Settings

    # opt_in_myjobs is current hidden on the top level, refer to forms.py
    opt_in_myjobs = models.BooleanField(_('Opt-in to non-account emails and '
                                          'Saved Search'),
                                        default=True,
                                        help_text=_('Checking this allows '
                                                    'My.jobs to send email '
                                                    'updates to you.'))

    opt_in_employers = models.BooleanField(_('Email is visible to Employers'),
                                           default=True,
                                           help_text=_('Checking this allows '
                                                       'employers to send '
                                                       'emails to you.'))

    last_response = models.DateField(default=datetime.datetime.now, blank=True)

    # Password Settings
    password_change = models.BooleanField(_('Password must be changed on next '
                                            'login'), default=False)

    user_guid = models.CharField(max_length=100, db_index=True, unique=True)

    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    timezone = models.CharField(max_length=255, default=settings.TIME_ZONE)

    source = models.CharField(max_length=255,
                              default='https://secure.my.jobs',
                              help_text=_('Site that initiated account '
                                          'creation'))
    deactivate_type = models.CharField(max_length=11,
                                       choices=zip(DEACTIVE_TYPES_AND_NONE,
                                                   DEACTIVE_TYPES_AND_NONE),
                                       blank=False,
                                       default=DEACTIVE_TYPES_AND_NONE[0])

    USERNAME_FIELD = 'email'
    objects = CustomUserManager()

    def __init__(self, *args, **kwargs):
        super(User, self).__init__(*args, **kwargs)
        # Get a copy of the original password so we can determine if
        # it has changed in the save().
        self.__original_password = getattr(self, 'password', None)
        self.__original_opt_in_myjobs = self.opt_in_myjobs

    def __unicode__(self):
        return self.email

    natural_key = __unicode__

   

    def get_username(self):
        return self.email

    def get_short_name(self):
        return self.email



    def get_companies(self):
        """
        Returns a QuerySet of all the Companies a User has access to.

        """
        from seo.models import Company
        return Company.objects.filter(admins=self).distinct()

    def get_sites(self):
        """
        Returns a QuerySet of all the SeoSites a User has access to.

        """
        from seo.models import SeoSite
        kwargs = {'business_units__company__admins': self}
        return SeoSite.objects.filter(**kwargs).distinct()

    

    def update_profile_completion(self):
        """
        Updates the percent of modules in
        settings.PROFILE_COMPLETION_MODULES that a user has completed.
        """
        profile_dict = self.profileunits_set.all()
        num_complete = len(list(set([unit.get_model_name() for unit
                           in profile_dict if unit.get_model_name()
                           in settings.PROFILE_COMPLETION_MODULES])))
        self.profile_completion = int(float(
            1.0 * num_complete / len(settings.PROFILE_COMPLETION_MODULES))*100)
        self.save()

    def add_default_group(self):
        group, _ = Group.objects.get_or_create(name='Job Seeker')
        self.groups.add(group.pk)

    def make_guid(self):
        """
        Creates a uuid for the User only if the User does not currently has
        a user_guid.  After the uuid is made it is checked to make sure there
        are no duplicates. If no duplicates, save the GUID.
        """
        if not self.user_guid:
            guid = uuid.uuid4().hex
            if User.objects.filter(user_guid=guid):
                self.make_guid()
            else:
                self.user_guid = guid


    # def get_full_name(self, default=""):
    #     """
    #     Returns the user's full name based off of first_name and last_name
    #     from the user model.
    # 
    #     Inputs:
    #     :default:   Can add a default if the user doesn't have a first_name
    #                 or last_name.
    #     """
    #     if self.first_name and self.last_name:
    #         return "%s %s" % (self.first_name, self.last_name)
    #     else:
    #         return default

    def add_primary_name(self, update=False, f_name="", l_name=""):
        """
        Primary function that adds the primary user's ProfileUnit.Name object
        first and last name to the user model, if Name object exists.

        Inputs:
        :update:    Update is a flag that should be used to determine if to use
                    this function as an update (must provide f_name and l_name
                    if that is the case) or if the function needs to be called
                    to set the user's first_name and last_name in the model.

        :f_name:    If the update flag is set to true this needs to have the
                    given_name value from the updating Name object.

        :l_name:    If the update flag is set to true this needs to have the
                    family_name value from the updating Name object.
        """
        if update and f_name != '' and l_name != '':
            self.first_name = f_name
            self.last_name = l_name
            self.save()
            return

        try:
            name_obj = self.profileunits_set.filter(
                content_type__name="name").get(name__primary=True)
        except ObjectDoesNotExist:
            name_obj = None

        if name_obj:
            self.first_name = name_obj.name.given_name
            self.last_name = name_obj.name.family_name
            self.save()
        else:
            self.first_name = ""
            self.last_name = ""
            self.save()

   

class CustomHomepage(Site):
    logo_url = models.URLField('Logo Image URL', max_length=200, null=True,
                               blank=True)
    show_signup_form = models.BooleanField(default=True)


class Ticket(models.Model):
    class Meta:
        unique_together = ['ticket', 'user']

    ticket = models.CharField(max_length=255)
    user = models.ForeignKey('User')

class FAQ(models.Model):
    question = models.CharField(max_length=255, verbose_name='Question')
    answer = models.TextField(verbose_name='Answer',
                              help_text='Answers allow use of HTML')
    is_visible = models.BooleanField(default=True, verbose_name='Is visible')