from datetime import datetime, timedelta
from os import path
from re import sub
from urllib import urlencode
from uuid import uuid4
import json

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.files.storage import default_storage
from django.core.urlresolvers import reverse
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver

from mypartners.location_data import states # from postajob.location_data import states

from universal.helpers import json_to_query

CONTACT_TYPE_CHOICES = (('email', 'Email'),
                        ('phone', 'Phone'),
                        ('meetingorevent', 'Meeting or Event'),
                        ('job', 'Job Followup'),
                        ('pssemail', "Partner Saved Search Email"))
CONTACT_TYPES = dict(CONTACT_TYPE_CHOICES)

ADDITION = 1
CHANGE = 2
DELETION = 3
EMAIL = 4

ACTIVITY_TYPES = {
    1: 'added',
    2: 'updated',
    3: 'deleted',
    4: 'sent',
}


class Status(models.Model):
    """
    Keeps track of a particular model's approval status.
    """
    UNPROCESSED, APPROVED, DENIED = range(3)
    CODES = {
        UNPROCESSED: 'Unprocessed',
        APPROVED: 'Approved',
        DENIED: 'Denied'
    }

    code = models.PositiveSmallIntegerField(
        default=APPROVED, choices=CODES.items(), verbose_name="Status Code")
    approved_by = models.ForeignKey(
        'usermodel.User', null=True, on_delete=models.SET_NULL)
    last_modified = models.DateTimeField(verbose_name="Last Modified",
                                         default=datetime.now,
                                         blank=True)

    def __unicode__(self):
        return dict(Status.CODES)[self.code]


class SearchParameterQuerySet(models.query.QuerySet):
    """
    Defines a query set with a `from_search` method for filtering by query
    parameters.
    """

    # TODO: Come up with a better name for this method
    def from_search(self, company=None, filters=None):
        """
        Intelligently filter based on query .

        Inputs:
            :company: The company to restrict results to
            :filters: A JSON string which is an object to be passed to
                      filter().                             
            :filters: A dict of field: term pairs where field is a field of
                         the `ContactRecord` model and term is search term
                         you'd like to filter against.

                         For `datetime`, pass `start_date` and/or `end_date`
                         instead.

        Example:
            If you want to filter partners where the related contact record's
            date time is before a certain date:
                Partner.objects.from_search(filters=json.dumps({
                    'contactrecord': {
                        'date_time': {
                            'lte': '2015-08-03 00:00:00.0'
                        }
                    }
                })

            The above is equivalent to:
                Partner.objects.filter(
                    contactrecord__date_time__lte='2015-08-03 00:00:00.0')

        """

        # default to an empty object
        filters = filters or "{}"

        if company:
            self = self.filter(**{
                getattr(self.model, 'company_ref', 'company'): company})

        query = json_to_query(json.loads(filters))

        if hasattr(self.model, 'approval_status'):
            query.update({'approval_status__code__iexact': Status.APPROVED})

        self = self.filter(**query).distinct()

        return self


class SearchParameterManager(models.Manager):
    use_for_related_fields = True

    def __init__(self, archived=False):
        """
        Adds a new argument to the manager constructor to allow us to specify
        if a given query should include archived models.

        If this isn't doing what you want, examine the model using it and pay
        special attention to what value of "archived" is being passed in.

        Inputs:
        :archived: True: query archived only, False: exclude
            archived; None: query all objects
        :type archived: bool, None
        """
        super(SearchParameterManager, self).__init__()
        self._archived = archived
        self._queryset = SearchParameterQuerySet

    def get_queryset(self):
        qs = self._queryset(self.model, using=self._db)
        # At the time of writing, this manager is used on models that don't
        # have the ability to be archived. This isn't a perfect solution
        # but changing everything is a bit out of scope at the moment.
        if ('archived_on' in self.model._meta.get_all_field_names()
                and self._archived is not None):
            qs = qs.exclude(archived_on__isnull=self._archived)
            if self.model in [ContactRecord, Contact]:
                qs = qs.exclude(partner__archived_on__isnull=self._archived)
                if self.model == ContactRecord:
                    qs = qs.exclude(contact__archived_on__isnull=self._archived)
        return qs

    def from_search(self, company=None, filters=None):
        return self.get_queryset().from_search(
            company, filters)

    def sort_by(self, *fields):
        return self.get_queryset().sort_by(*fields)


class ArchivedModel(models.Model):
    archived_on = models.DateTimeField(null=True)

    # These two managers do different things and may not exactly do what you
    # want unless you're paying attention. The first (objects) retrieves only
    # objects where archived_on is None. The second (all_objects) retrieves all
    # objects regardless of the state of archived_on. Managers used by related
    # objects exhibit some weirdness as shown below.
    #
    # A demo is available as test_archived_manager_weirdness in
    # mypartners/tests/test_models
    objects = SearchParameterManager()
    all_objects = SearchParameterManager(archived=None)

    class Meta:
        abstract = True

    def archive(self, *args, **kwargs):
        self.archived_on = datetime.now()
        self.save()


class Location(models.Model):
    address_line_one = models.CharField(max_length=255,
                                        verbose_name='Address Line One',
                                        blank=True,
                                        help_text='ie 123 Main St')
    address_line_two = models.CharField(max_length=255,
                                        verbose_name='Address Line Two',
                                        blank=True,
                                        help_text='ie Suite 100')
    city = models.CharField(max_length=255, verbose_name='City',
                            help_text='ie Chicago, Washington, Dayton')
    state = models.CharField(max_length=200, verbose_name='State/Region',
                             help_text='ie NY, WA, DC')
    country_code = models.CharField(max_length=3, verbose_name='Country',
                                    default='USA')
    postal_code = models.CharField(max_length=12, verbose_name='Postal Code',
                                   blank=True,
                                   help_text='ie 90210, 12345-7890')
    label = models.CharField(max_length=60, verbose_name='Address Name',
                             blank=True,
                             help_text='ie Main Office, Corporate, Regional')

    def __unicode__(self):
        return ", ".join(filter(bool, [self.city, self.state]))

    natural_key = __unicode__

    def save(self, **kwargs):
        super(Location, self).save(**kwargs)


class Contact(ArchivedModel):
    """
    Everything here is self explanatory except for one part. With the Contact
    object there is Contact.partner_set and .partners_set

    """
    user = models.ForeignKey('usermodel.User', blank=True, null=True,
                             on_delete=models.SET_NULL)
    partner = models.ForeignKey('Partner', 
                                null=True, on_delete=models.SET_NULL)
    # used if this partner was created by using the partner library
    library = models.ForeignKey('PartnerLibrary', null=True,
                                on_delete=models.SET_NULL)
    name = models.CharField(max_length=255, verbose_name='Full Name',
                            help_text='Contact\'s full name')
    email = models.EmailField(max_length=255, verbose_name='Email', blank=True,
                              help_text='Contact\'s email address')
    phone = models.CharField(max_length=30, verbose_name='Phone', blank=True,
                             default='', help_text='ie (123) 456-7890')
    locations = models.ManyToManyField('Location', related_name='contacts')
    tags = models.ManyToManyField('Tag', null=True)
    notes = models.TextField(max_length=1000, verbose_name='Notes',
                             blank=True, default="", 
                             help_text='Any additional information you want to record')
    approval_status = models.OneToOneField(
        'mypartners.Status', null=True, verbose_name="Approval Status")
    last_modified = models.DateTimeField(default=datetime.now, blank=True)

    company_ref = 'partner__owner'

    class Meta:
        verbose_name_plural = 'contacts'

    def __unicode__(self):
        if self.name:
            return self.name
        if self.email:
            return self.email
        return 'Contact object'

    natural_key = __unicode__

    def delete(self, *args, **kwargs):
        pre_delete.send(sender=Contact, instance=self, using='default')
        super(Contact, self).delete(*args, **kwargs)

    def archive(self, *args, **kwargs):
        pre_delete.send(sender=Contact, instance=self, using='default')
        super(Contact, self).archive(*args, **kwargs)

    def get_contact_url(self):
        base_urls = {
            'contact': reverse('edit_contact'),
        }
        params = {
            'partner': self.partner.pk,
            'company': self.partner.owner.pk,
            'id': self.pk,
            'ct': ContentType.objects.get_for_model(Contact).pk
        }
        query_string = urlencode(params)
        return "%s?%s" % (base_urls[self.content_type.name], query_string)


@receiver(pre_delete, sender=Contact, dispatch_uid='pre_delete_contact_signal')
def delete_contact(sender, instance, using, **kwargs):
    """
    Signalled when a Contact is deleted to deactivate associated partner saved
    searches, if any exist
    """

    if instance.user is not None:
        # user.partnersavedsearch_set filters on partnersavedsearch.owner, not
        # .user
        to_disable = instance.user.savedsearch_set.filter(
            partnersavedsearch__isnull=False)

        for pss in to_disable:
            pss.is_active = False
            note = ('\nThe contact for this partner saved search ({name}) '
                    'was deleted by the partner. As a result, this search '
                    'has been disabled.').format(name=instance.name)
            pss.notes += note
            pss.save()


@receiver(pre_save, sender=Contact, dispatch_uid='pre_save_contact_signal')
def save_contact(sender, instance, **kwargs):
    if not instance.approval_status:
        # if no relation exists, instance.user will raise an attribute error
        instance.approval_status = Status.objects.create(
            approved_by=instance.user)


class Partner(ArchivedModel):
    """
    Object that this whole app is built around.

    """
    name = models.CharField(max_length=255,
                            verbose_name='Partner Organization',
                            help_text='Name of the Organization')
    data_source = models.CharField(max_length=255,
                                   verbose_name='Source',
                                   blank=True, 
                                   help_text='Website, event, or other source where you found the partner')
    uri = models.URLField(verbose_name='URL', blank=True, 
                        help_text='Full url. ie http://partnerorganization.org')
    primary_contact = models.ForeignKey('Contact', null=True,
                                        related_name='primary_contact',
                                        on_delete=models.SET_NULL,
                                        help_text='Denotes who the primary contact is for this organization.')
    # used if this partner was created by using the partner library
    library = models.ForeignKey('PartnerLibrary', null=True,
                                on_delete=models.SET_NULL)
    tags = models.ManyToManyField('Tag', null=True, 
        help_text='ie \'Disability\', \'veteran-outreach\', etc. Separate tags with a comma.')
    # owner is the Company that owns this partner.
    owner = models.ForeignKey('seo.Company', null=True,
                              on_delete=models.SET_NULL)
    approval_status = models.OneToOneField(
        'mypartners.Status', null=True, verbose_name="Approval Status")
    last_modified = models.DateTimeField(default=datetime.now, blank=True)

    company_ref = 'owner'

    def __unicode__(self):
        return self.name

    natural_key = __unicode__

    # get_searches_for_partner
    def get_searches(self):
        saved_searches = self.partnersavedsearch_set.all()
        saved_searches = saved_searches.order_by('-created_on')
        return saved_searches

    # get_logs_for_partner
    def get_logs(self, content_type_id=None, num_items=10):
        logs = ContactLogEntry.objects.filter(partner=self)
        if content_type_id:
            logs = logs.filter(content_type_id=content_type_id)
        return logs.order_by('-action_time')[:num_items]

    def get_contact_locations(self):
        """Return a list of unique contact locations as strings."""

        # Unique city and state pairs attached to contacts belonging to this
        # partner.
        locs = Location.objects.filter(
            contacts__in=self.contact_set.all()).exclude(
                contacts__archived_on__isnull=False).values(
                    'city', 'state').distinct().order_by('state', 'city')

        # Convert these city/state pairs into comma separated strings
        return [", ".join(filter(bool, [l['city'], l['state']])) for l in locs]

    # get_contact_records_for_partner
    def get_contact_records(self, contact_name=None, record_type=None,
                            created_by=None, date_start=None, date_end=None,
                            order_by=None, keywords=None, tags=None):

        records = self.contactrecord_set.prefetch_related('tags').all()
        if contact_name:
            records = records.filter(contact__name=contact_name)
        if date_start:
            records = records.filter(date_time__gte=date_start)
        if date_end:
            date_end = date_end + timedelta(1)
            records = records.filter(date_time__lte=date_end)
        if record_type:
            records = records.filter(contact_type=record_type)
        if created_by:
            records = records.filter(created_by=created_by)
        if tags:
            for tag in tags:
                records = records.filter(tags__name__icontains=tag)
        if keywords:
            query = models.Q()
            for keyword in keywords:
                query &= (models.Q(contact_email__icontains=keyword) |
                          models.Q(contact_phone__icontains=keyword) |
                          models.Q(subject__icontains=keyword) |
                          models.Q(notes__icontains=keyword) |
                          models.Q(job_id__icontains=keyword))

            records = records.filter(query)

        if order_by:
            records = records.order_by(order_by)
        else:
            records = records.order_by('-date_time')

        return records

    def get_all_tags(self):
        """Gets unique tags for partner and its contacts"""
        tags = set(self.tags.all())
        tags.update(
            Tag.objects.filter(contact__in=self.contact_set.all()))

        return tags


@receiver(pre_save, sender=Partner, dispatch_uid='pre_save_partner_signal')
def save_partner(sender, instance, **kwargs):
    if not instance.approval_status:
        # TODO: find out how to get a user for approved_by
        # if no relation exists, instance.user will raise an attribute error    
        instance.approval_status = Status.objects.create()


class PartnerLibrary(models.Model):
    """
    Partners curated from the Office of Federal Contract Compliance
    Programs (OFCCP).

    .. note:: For the differences between `state` and `st`, see the ofccp
    module.

    """

    def __init__(self, *args, **kwargs):
        """
        Regular initialization with a custom has_valid_location property.
        Rather than modify the data on import, we mark the location as invalid.
        """

        super(PartnerLibrary, self).__init__(*args, **kwargs)
        self.has_valid_location = self.st.upper() in states.keys()

    # Where the data was pulled from
    data_source = models.CharField(
        max_length=255,
        default='Employment Referral Resource Directory')

    # Organization Info
    name = models.CharField(max_length=255,
                            verbose_name='Partner Organization')
    uri = models.URLField(blank=True)
    region = models.CharField(max_length=30, blank=True)
    # long state name
    state = models.CharField(max_length=30, blank=True)
    area = models.CharField(max_length=255, blank=True)

    # Contact Info
    contact_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    phone_ext = models.CharField(max_length=10, blank=True)
    alt_phone = models.CharField(max_length=30, blank=True)
    fax = models.CharField(max_length=30, blank=True)
    email = models.CharField(max_length=255, blank=True)

    # Location info
    street1 = models.CharField(max_length=255, blank=True)
    street2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=255, blank=True)
    # short state name
    st = models.CharField(max_length=10, blank=True)
    zip_code = models.CharField(max_length=12, blank=True)

    # Demographic Info
    is_minority = models.BooleanField('minority', default=False)
    is_female = models.BooleanField('female', default=False)
    is_disabled = models.BooleanField('disabled', default=False)
    is_veteran = models.BooleanField('veteran', default=False)
    is_disabled_veteran = models.BooleanField('disabled_veteran',
                                              default=False)

    def __unicode__(self):
        return self.name

    natural_key = __unicode__

    def save(self, *args, **kwargs):
        self.has_valid_location = self.st.upper() in states.keys()

        super(PartnerLibrary, self).save(*args, **kwargs)


class ContactRecordQuerySet(SearchParameterQuerySet):
    @property
    def communication_activity(self):
        return self.exclude(contact_type='job')

    @property
    def referral_activity(self):
        activity = self.filter(contact_type='job').aggregate(
            applications=models.Sum('job_applications'),
            interviews=models.Sum('job_interviews'),
            hires=models.Sum('job_hires'))

        return {key: int(value or 0) for key, value in activity.items()}

    @property
    def emails(self):
        return self.communication_activity.filter(
            contact_type='email').count()

    @property
    def calls(self):
        return self.communication_activity.filter(
            contact_type='phone').count()

    @property
    def meetings(self):
        return self.communication_activity.filter(
            contact_type='meetingorevent').count()

    @property
    def searches(self):
        return self.communication_activity.filter(
            contact_type='pssemail').count()

    @property
    def applications(self):
        return self.referral_activity['applications']

    @property
    def interviews(self):
        return self.referral_activity['interviews']

    @property
    def hires(self):
        return self.referral_activity['hires']

    @property
    def referrals(self):
        return self.filter(contact_type='job').count()

    @property
    def contacts(self):
        """ 
        Returns a queryset annotated by the number of referrals (contact_type =
        'job') and number of records (contact_type != 'job'). Django doesn't
        allow annotated values to be filtered without also filtering the base
        result set, which is why we annotate separately then attach the values
        to the resulting objects.
        """

        all_contacts = self.values(
            'partner__name', 'partner', 'contact__name',
            'contact_email').distinct()
    
        records = dict(self.exclude(contact_type='job').values_list(
            'contact__name').annotate(
                records=models.Count('contact__name')).distinct())

        referrals = dict(self.filter(contact_type='job').values_list(
            'contact__name').annotate(
                referrals=models.Count('contact__name')).distinct())

        for contact in all_contacts:
            contact['referrals'] = referrals.get(contact['contact__name'], 0)
            contact['records'] = records.get(contact['contact__name'], 0)

        return sorted(all_contacts, key=lambda c: c['records'], reverse=True)


class ContactRecordManager(SearchParameterManager):
    def __init__(self, *args, **kwargs):
        super(ContactRecordManager, self).__init__(*args, **kwargs)
        self._queryset = ContactRecordQuerySet

    def communication_activity(self):
        return self.get_queryset().communication_activity


class ContactRecord(ArchivedModel):
    """
    Object for Communication Records
    """

    company_ref = 'partner__owner'
    objects = ContactRecordManager()
    all_objects = ContactRecordManager(archived=None)

    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('usermodel.User', null=True, on_delete=models.SET_NULL)
    partner = models.ForeignKey(Partner, null=True, on_delete=models.SET_NULL)
    contact = models.ForeignKey(Contact, null=True, on_delete=models.SET_NULL)
    contact_type = models.CharField(choices=CONTACT_TYPE_CHOICES,
                                    max_length=50,
                                    verbose_name="Communication Type")
    # contact type fields, fields required depending on contact_type. Enforced
    # on the form level.
    contact_email = models.CharField(max_length=255,
                                     verbose_name="Contact Email",
                                     blank=True)
    contact_phone = models.CharField(verbose_name="Contact Phone Number",
                                     max_length=30, blank=True, default="")
    location = models.CharField(verbose_name="Meeting Location",
                                max_length=255, blank=True, default="")
    length = models.TimeField(verbose_name="Meeting Length", blank=True,
                              null=True)
    subject = models.CharField(verbose_name="Subject or Topic", max_length=255,
                               blank=True, default="")
    date_time = models.DateTimeField(verbose_name="Date & Time", blank=True)
    notes = models.TextField(max_length=1000,
                             verbose_name='Details, Notes or Transcripts',
                             blank=True, default="")
    job_id = models.CharField(max_length=40, verbose_name='Job Number/ID',
                              blank=True, default="")
    job_applications = models.CharField(max_length=6,
                                        verbose_name="Number of Applications",
                                        blank=True, default="")
    job_interviews = models.CharField(max_length=6,
                                      verbose_name="Number of Interviews",
                                      blank=True, default="")
    job_hires = models.CharField(max_length=6, verbose_name="Number of Hires",
                                 blank=True, default="")
    tags = models.ManyToManyField('Tag', null=True)
    approval_status = models.OneToOneField(
        'mypartners.Status', null=True, verbose_name="Approval Status")
    last_modified = models.DateTimeField(default=datetime.now, blank=True)

    def __unicode__(self):
        return "%s Communication Record - %s" % (self.contact_type, self.subject)

    def save(self, *args, **kwargs):
        if not self.pk and self.contact:
            self.contact_email = self.contact_email or self.contact.email
            self.contact_phone = self.contact_phone or self.contact.phone

        super(ContactRecord, self).save(*args, **kwargs)

    def get_record_description(self):
        """
        Generates a human readable description of the contact
        record.

        """
        content_type = ContentType.objects.get_for_model(self.__class__)
        contact_type = dict(CONTACT_TYPE_CHOICES)[self.contact_type]
        if contact_type == 'Email':
            contact_type = 'n email'
        else:
            contact_type = ' %s' % contact_type

        try:
            logs = ContactLogEntry.objects.filter(object_id=self.pk,
                                                  content_type=content_type)
            log = logs.order_by('-action_time')[:1][0]
        except IndexError:
            return ""

        contact_str = "A%s record for %s was %s" % \
                      (contact_type.lower(),
                       self.contact.name, ACTIVITY_TYPES[log.action_flag])

        if log.user:
            user = log.user.email
            if log.user.get_fullname:
                user = log.user.get_full_name()
            contact_str = "%s by %s" % (contact_str, user)

        return contact_str

    def get_human_readable_contact_type(self):
        contact_types = dict(CONTACT_TYPE_CHOICES)
        return contact_types[self.contact_type]

    def get_record_url(self):
        params = {
            'partner': self.partner.pk,
            'id': self.pk,
        }
        query_string = urlencode(params)
        return "%s?%s" % (reverse('record_view'), query_string)

    def shorten_date_time(self):
        return self.date_time.strftime('%b %e, %Y')

    @property
    def contactlogentry(self):
        ct = ContentType.objects.get_for_model(self.__class__)
        return ContactLogEntry.objects.filter(content_type=ct,
                                              object_id=self.pk).first()


@receiver(pre_save, sender=ContactRecord, 
          dispatch_uid='pre_save_contactrecord_signal')
def save_contactrecord(sender, instance, **kwargs):
    if not instance.approval_status:
        # if no relation exists, instance.user will raise an attribute error
        instance.approval_status = Status.objects.create(
            approved_by=instance.created_by)


MAX_ATTACHMENT_MB = 4
S3_CONNECTION = 'S3Connection:s3.amazonaws.com'


class PRMAttachment(models.Model):

    # def get_file_name(self, filename):
    #     """
    #     Ensures that a file name is unique before uploading.
    #     The PRMAttachment instance requires an extra attribute,
    #     partner (a Partner instance) to be set in order to create the
    #     file name.

    #     """
    #     filename, extension = path.splitext(filename)
    #     filename = '.'.join([sub(r'[\W]', '', filename),
    #                          sub(r'[\W]', '', extension)])

    #     # If the uploaded file only contains invalid characters the end
    #     # result will be a file named "."
    #     if not filename or filename == '.':
    #         filename = 'unnamed_file'

    #     uid = uuid4()
    #     path_addon = "mypartners/%s/%s/%s" % (self.partner.owner.pk,
    #                                           self.partner.pk, uid)
    #     name = "%s/%s" % (path_addon, filename)

    #     # Make sure that in the unlikely event that a filepath/uid/filename
    #     # combination isn't actually unique a new unique id
    #     # is generated.
    #     while default_storage.exists(name):
    #         uid = uuid4()
    #         path_addon = "mypartners/%s/%s/%s" % (self.partner.owner,
    #                                               self.partner.name, uid)
    #         name = "%s/%s" % (path_addon, filename)

    #     return name

    # attachment = models.FileField(upload_to=get_file_name, blank=True,
    #                               null=True, max_length=767)
    # contact_record = models.ForeignKey(ContactRecord, null=True,
    #                                    on_delete=models.SET_NULL)

    def save(self, *args, **kwargs):
        instance = super(PRMAttachment, self).save(*args, **kwargs)

        # Confirm that we're not trying to change public/private status of
        # actual files during local testing.
        try:
            if repr(default_storage.connection) == S3_CONNECTION:
                from boto import connect_s3, s3
                conn = connect_s3(settings.AWS_ACCESS_KEY_ID,
                                  settings.AWS_SECRET_KEY)
                bucket = conn.create_bucket(settings.AWS_STORAGE_BUCKET_NAME)
                key = s3.key.Key(bucket)
                key.key = self.attachment.name
                key.set_acl('private')
        except AttributeError:
            pass

        return instance

    def delete(self, *args, **kwargs):
        filename = self.attachment.name
        super(PRMAttachment, self).delete(*args, **kwargs)
        default_storage.delete(filename)

    @property
    def partner(self):
        return getattr(self.contact_record, 'partner', None)


class ContactLogEntry(models.Model):
    action_flag = models.PositiveSmallIntegerField('action flag')
    action_time = models.DateTimeField('action time', auto_now=True)
    change_message = models.TextField('change message', blank=True)
    # A value that can meaningfully (email, name) identify the contact.
    contact_identifier = models.CharField(max_length=255)
    content_type = models.ForeignKey(ContentType, blank=True, null=True)
    delta = models.TextField(blank=True)
    object_id = models.TextField('object id', blank=True, null=True)
    object_repr = models.CharField('object repr', max_length=200)
    partner = models.ForeignKey(Partner, null=True, on_delete=models.SET_NULL)
    user = models.ForeignKey('usermodel.User', null=True, on_delete=models.SET_NULL)
    successful = models.NullBooleanField(default=None)

    def get_edited_object(self):
        """
        Returns the edited object represented by this log entry

        """
        try:
            return self.content_type.get_object_for_this_type(pk=self.object_id)
        except self.content_type.model_class().DoesNotExist:
            return None

    def get_object_url(self):
        """
        Creates the link that leads to the view/edit view for that object.

        """
        obj = self.get_edited_object()
        if not obj or not self.partner:
            return None
        base_urls = {
            'contact': reverse('edit_contact'),
            'contact record': reverse('record_view'),
            'partner saved search': reverse('partner_edit_search'),
            'partner': reverse('partner_details'),
        }
        params = {
            'partner': self.partner.pk,
            'id': obj.pk,
            'ct': self.content_type.pk,
        }
        query_string = urlencode(params)
        return "%s?%s" % (base_urls[self.content_type.name], query_string)


class Tag(models.Model):
    name = models.CharField(max_length=255)
    hex_color = models.CharField(max_length=6, default="d4d4d4", blank=True)
    company = models.ForeignKey('seo.Company')

    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('usermodel.User', null=True, on_delete=models.SET_NULL)

    objects = SearchParameterManager()

    def __unicode__(self):
        return "%s for %s" % (self.name, self.company.name)

    def natural_key(self):
        return self.name

    class Meta:
        unique_together = ('name', 'company')
        verbose_name = "tag"


class CommonEmailDomain(models.Model):
    """
    Common email domains which should not be allowed for outreach email
    domains.
    """

    class Meta:
        ordering = ["domain"]

    domain = models.URLField(unique=True)

    def __unicode__(self):
        return self.domain


class OutreachEmailDomain(models.Model):
    """
    Email domains from which a comany will accept emails from for the purpose
    of outreach. These email addresses are for non-users.
    """

    class Meta:
        unique_together = ("company", "domain")
        ordering = ["company", "domain"]

    company = models.ForeignKey("seo.Company")
    domain = models.URLField()

    def __unicode__(self):
        return "%s for %s" % (self.domain, self.company)

    def clean_fields(self, exclude=None):
        if CommonEmailDomain.objects.filter(
                domain__iexact=self.domain).exists():
            raise ValidationError(
                "%s has been blacklisted as a common domain, please choose "
                "another." % self.domain)

    def save(self, *args, **kwargs):
        self.clean_fields()
        super(OutreachEmailDomain, self).save(*args, **kwargs)


class OutreachEmailAddress(models.Model):
    def __unicode__(self):
        return "%s for %s" % (self.email, self.company)

    company = models.ForeignKey("seo.Company")
    email = models.EmailField(
        max_length=255, verbose_name="Email", 
        help_text="Email to send outreach efforts to.")


class OutreachWorkflowState(models.Model):
    state = models.CharField(max_length=50)

    def __unicode__(self):
        return self.state


class NonUserOutreach(models.Model):
    date_added = models.DateTimeField(auto_now_add=True)
    outreach_email = models.ForeignKey("OutreachEmailAddress")
    from_email = models.EmailField(
        max_length=255, verbose_name="Email",
        help_text="Email outreach effort sent from.")
    email_body = models.TextField()
    current_workflow_state = models.ForeignKey("OutreachWorkflowState")
    partners = models.ManyToManyField("Partner")
    contacts = models.ManyToManyField("Contact")
    communication_records = models.ManyToManyField("ContactRecord")

    def __unicode__(self):
        return "Outreach email from %s sent to %s." % (
            self.from_email, self.outreach_email)
