from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import models
from django.db.models.query import QuerySet
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _


CHOICES = ['sourcecodetag', 'amptoamp', 'cframe', 'anchorredirectissue',
           'urlswap', 'replacethenadd', 'replacethenaddpre',
           'sourceurlwrapappend', 'sourcecodeinsertion',
           'sourceurlwrapunencoded', 'sourceurlwrapunencodedappend',
           'switchlastinstance', 'switchlastthenadd', 'sourcecodeswitch',
           'doubleclickunwind', 'fixurl']


CHOICE_LIST = tuple((choice, choice) for choice in CHOICES)


class DestinationManipulation(models.Model):
    """
    Represents the original DestinationManipulation table
    """
    action_type = models.IntegerField(help_text=_('Always 1 or 2'))
    buid = models.IntegerField(help_text=_('Business unit ID that owns '
                                           'this manipulation'))
    view_source = models.IntegerField(help_text=_('View source ID for a'
                                                  'particular manipulation'))
    action = models.CharField(max_length=255, blank=True, null=True,
                              choices=CHOICE_LIST, default=CHOICES[0],
                              help_text=_('String describing what type of '
                                          'manipulation is to occur'))
    value_1 = models.TextField(blank=True)
    value_2 = models.TextField(blank=True)

    class Meta:
        unique_together = ('action_type', 'buid', 'view_source')

    def __unicode__(self):
        return u'buid: %s, action: %s-%s, view source %s' % (
            self.buid, self.action_type, self.action, self.view_source)

    def get_view_source_name(self):
        vs = None
        try:
            vs = ViewSource.objects.get(view_source_id=self.view_source)
        except ViewSource.DoesNotExist:
            pass

        if vs:
            tag = '<a href="/admin/redirect/viewsource/%s">' % vs.pk
            tag += '%s (%s)</a>' % (vs.name, vs.view_source_id)
        else:
            tag = str(self.view_source)

        tag += '<br><span class="float-right">Excluded <img src="/static/admin/img/icon-%s.gif" alt=%s></span>'
        if self.view_source in settings.EXCLUDED_VIEW_SOURCES:
            tag %= ('yes', 'True')
        else:
            tag %= ('no', 'False')
        return tag

    get_view_source_name.short_description = 'View source'
    get_view_source_name.allow_tags = True
    get_view_source_name.admin_order_field = 'view_source'


class RedirectMixin(object):
    def get_any(self, *args, **kwargs):
        """
        Gets a redirect object (with matching args and kwargs)
        from the first table with a match.

        """
        subclasses = BaseRedirect.__subclasses__()
        # We always want to check the Redirect table first, so make
        # sure it's first in the list.
        subclasses.insert(0, subclasses.pop(subclasses.index(Redirect)))
        for model in subclasses:
            try:
                return model.objects.get(*args, **kwargs)
            except model.DoesNotExist:
                pass
            except model.MultipleObjectsReturned:
                raise MultipleObjectsReturned
        raise ObjectDoesNotExist


class RedirectQuerySet(QuerySet, RedirectMixin):
    pass


class RedirectManager(models.Manager, RedirectMixin):
    def get_query_set(self):
        return RedirectQuerySet(self.model, using=self._db)


class BaseRedirect(models.Model):
    """
    Contains most of the information required to determine how a url
    is to be transformed
    """
    guid = models.CharField(max_length=42, primary_key=True,
                            help_text=_('42-character hex string'),
                            db_index=True)
    buid = models.IntegerField(default=0,
                               help_text=_('Business unit ID for a given '
                                           'job provider'))
    uid = models.IntegerField(unique=True, blank=True, null=True,
                              help_text=_("Unique id on partner's ATS or "
                                          "other job repository"))
    url = models.TextField(help_text=_('URL being manipulated'))
    new_date = models.DateTimeField(help_text=_('Date that this job was '
                                                'added'))
    expired_date = models.DateTimeField(blank=True, null=True,
                                        help_text=_('Date that this job was '
                                                    'marked as expired'),
                                        db_index=True)
    job_location = models.CharField(max_length=255, blank=True)
    job_title = models.CharField(max_length=255, blank=True)
    company_name = models.TextField(blank=True)

    objects = RedirectManager()

    class Meta:
        abstract = True

    def __unicode__(self):
        return u'%s for guid %s' % (self.url, self.guid)

    def make_link(self):
        """Generates the redirected link for a redirect object."""
        # Handle the fact that guid is has leading/trailing braces and dashes.
        # '{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}'
        return "http://my.jobs/%s" % self.guid[1:-1].replace('-', '') + '10'


class Redirect(BaseRedirect):
    pass


class RedirectArchive(BaseRedirect):
    pass


class ATSSourceCode(models.Model):
    """
    Represents one entry in a query string of the form
    ?parameter_name=parameter_value
    """
    buid = models.IntegerField(default=0)
    view_source = models.ForeignKey('ViewSource', blank=False, null=True)
    ats_name = models.CharField(max_length=255)
    parameter_name = models.CharField(max_length=255)
    parameter_value = models.CharField(max_length=255)

    class Meta:
        unique_together = ('ats_name', 'parameter_name', 'parameter_value',
                           'buid', 'view_source')

    def __unicode__(self):
        return u'buid %d, view source %d' % \
            (self.buid, self.view_source_id)


# class CanonicalMicrosite(models.Model):
#     buid = models.IntegerField(primary_key=True, default=0)
#     canonical_microsite_url = models.URLField()

#     def __unicode__(self):
#         return u'%s for buid %d' % \
#             (self.canonical_microsite_url, self.buid)


class RedirectAction(models.Model):
    """
    Determines what transformation(s) should take place based on the provided
    parameters
    """

    # Too manual? To add another action, add it to this list and
    # increment the value in the call to range, then add it to the
    # ACTION_CHOICES tuple
    (SOURCECODETAG_ACTION, AMPTOAMP_ACTION, CFRAME_ACTION,
        ANCHORREDIRECTISSUE_ACTION, URLSWAP_ACTION, REPLACETHENADD_ACTION,
        REPLACETHENADDPRE_ACTION, SOURCEURLWRAPAPPEND_ACTION,
        SOURCECODEINSERTION_ACTION, SOURCEURLWRAPUNENCODED_ACTION,
        SOURCEURLWRAPUNENCODEDAPPEND_ACTION, SWITCHLASTINSTANCE_ACTION,
        SWITCHLASTTHENADD_ACTION, SOURCECODESWITCH_ACTION,
        DOUBLECLICKUNWIND_ACTION, FIXURL_ACTION,) = range(16)

    ACTION_CHOICES = (
        (SOURCECODETAG_ACTION, 'sourcecodetag'),
        (AMPTOAMP_ACTION, 'amptoamp'),
        (CFRAME_ACTION, 'cframe'),
        (ANCHORREDIRECTISSUE_ACTION, 'anchorredirectissue'),
        (URLSWAP_ACTION, 'urlswap'),
        (REPLACETHENADD_ACTION, 'replacethenadd'),
        (REPLACETHENADDPRE_ACTION, 'replacethenaddpre'),
        (SOURCEURLWRAPAPPEND_ACTION, 'sourceurlwrapappend'),
        (SOURCECODEINSERTION_ACTION, 'sourcecodeinsertion'),
        (SOURCEURLWRAPUNENCODED_ACTION, 'sourceurlwrapunencoded'),
        (SOURCEURLWRAPUNENCODEDAPPEND_ACTION, 'sourceurlwrapunencodedappend'),
        (SWITCHLASTINSTANCE_ACTION, 'switchlastinstance'),
        (SWITCHLASTTHENADD_ACTION, 'switchlastthenadd'),
        (SOURCECODESWITCH_ACTION, 'sourcecodeswitch'),
        (DOUBLECLICKUNWIND_ACTION, 'doubleclickunwind'),
        (FIXURL_ACTION, 'fixurl'),
    )

    buid = models.IntegerField(default=0)
    view_source = models.ForeignKey('ViewSource')
    action = models.IntegerField(choices=ACTION_CHOICES,
                                 default=SOURCECODETAG_ACTION)

    class Meta:
        unique_together = ('buid', 'view_source', 'action')
        index_together = [['buid', 'view_source']]

    def __unicode__(self):
        return '%s for buid %d, view source %d' % \
            (self.action, self.buid, self.view_source_id)

    def get_method_name(self):
        return self.ACTION_CHOICES[self.action][1]


class ViewSource(models.Model):
    view_source_id = models.IntegerField(primary_key=True, blank=True,
                                         default=None)
    name = models.CharField(max_length=255, blank=True)
    friendly_name = models.CharField(max_length=255, blank=True)
    microsite = models.BooleanField(help_text=_(
        'Defunct; Use CanonicalMicrosite'),
        default=False)
    include_ga_params = models.BooleanField(
        help_text=_('Enables addition of Google Analytics parameters'),
        default=False)
    view_source_type = models.IntegerField(default=0)

    class Meta:
        get_latest_by = 'view_source_id'

    def __unicode__(self):
        return u'%s (%d)' % (self.name, self.view_source_id)

    def save(self, *args, **kwargs):
        if not self.view_source_id:
            # if view_source_id was not provided, set it to the next
            # available value
            try:
                latest = ViewSource.objects.values_list('view_source_id',
                                                        flat=True).latest()
                self.view_source_id = latest + 1
            except ViewSource.DoesNotExist:
                self.view_source_id = 0
        super(ViewSource, self).save(*args, **kwargs)

    def is_excluded(self):
        tag = '<img src="/static/admin/img/icon-%s.gif" alt=%s>'
        if self.view_source_id in settings.EXCLUDED_VIEW_SOURCES:
            tag %= ('yes', 'True')
        else:
            tag %= ('no', 'False')
        return tag
    is_excluded.short_description = 'excluded'
    is_excluded.allow_tags = True


class ViewSourceGroup(models.Model):
    name = models.CharField(_('Name of this view source group'),
                            blank=False, null=False, max_length=100)
    view_source = models.ManyToManyField('ViewSource')


class ExcludedViewSource(models.Model):
    """
    Each instance represents a particular view source that does not redirect
    to a microsite
    """
    view_source = models.IntegerField(primary_key=True,
                                      help_text=_('This view source will not '
                                                  'redirect to a microsite'))

    def get_vs_cell(self):
        """
        The Django admin is heavily table based. Construct the tags that will
        go into this excluded view source's cell.
        """
        try:
            vs = ViewSource.objects.get(view_source_id=self.view_source)
        except ViewSource.DoesNotExist:
            vs = None

        tag = '<a href="/admin/redirect/excludedviewsource/%s">' % \
              self.view_source

        if vs:
            tag += '%s</a>' % (str(vs),)
        else:
            tag += '%s</a>' % self.view_source
        return tag
    get_vs_cell.short_description = 'view source'
    get_vs_cell.allow_tags = True


def clear_vs_cache(sender, instance, created, **kwargs):
    cache_key = settings.EXCLUDED_VIEW_SOURCE_CACHE_KEY
    cache.delete(cache_key)


# Clears excluded view source cache when an instance is saved
post_save.connect(clear_vs_cache, sender=ExcludedViewSource,
                  dispatch_uid="clear_vs_cache")


class CustomExcludedViewSource(models.Model):
    """
    Some companies want a given view source to not redirect to their microsite
    but that should not be the case for everyone. This is a company-specific
    exclusion.
    """
    buid = models.IntegerField(blank=False,
                               help_text=_('Business unit id that wants '
                                           'a custom exclusion'))
    view_source = models.IntegerField(blank=False,
                                      help_text=_('View source that should '
                                                  'be excluded'))

    class Meta:
        unique_together = (('buid', 'view_source'),)
        index_together = [['buid', 'view_source']]

    def get_vs_name(self):
        try:
            vs = ViewSource.objects.get(view_source_id=self.view_source)
            tag = str(vs)
        except ViewSource.DoesNotExist:
            tag = str(self.view_source)
        return tag
    get_vs_name.short_description = 'view source'


def clear_custom_vs_cache(sender, instance, created, **kwargs):
    cache_key = settings.CUSTOM_EXCLUSION_CACHE_KEY
    cache.delete(cache_key)


# Clears excluded view source cache when an instance is saved
post_save.connect(clear_custom_vs_cache, sender=CustomExcludedViewSource,
                  dispatch_uid="clear_custom_vs_cache")


class CompanyEmail(models.Model):
    buid = models.IntegerField(primary_key=True)
    email = models.EmailField()

    def __unicode__(self):
        return '%s: %s' % (self.email, self.buid)


class EmailRedirectLog(models.Model):
    from_addr = models.EmailField()
    to_guid = models.CharField(max_length=38)
    buid = models.IntegerField()
    to_addr = models.EmailField()
    sent = models.DateTimeField(auto_now_add=True)
