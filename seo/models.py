import operator
# from DNS import DNSError
from boto.route53.exception import DNSServerError
# from slugify import slugify
import Queue

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes import generic
from django.contrib.flatpages.models import FlatPage
from django.contrib.sites.models import Site
from django.contrib.syndication.views import Feed
from django.contrib import messages
from django.core.cache import cache
from django.core import mail
from django.core.validators import MaxValueValidator, ValidationError
from django.db import models
from django.db.models.query import QuerySet
from django.db.models.signals import (post_delete, pre_delete, post_save,
                                      pre_save)
from django.db.models.fields.related import ForeignKey
from django.dispatch import Signal, receiver
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

# from haystack.inputs import Raw
# from haystack.query import SQ

# from saved_search.models import BaseSavedSearch, SOLR_ESCAPE_CHARS
# from taggit.managers import TaggableManager

# from moc_coding import models as moc_models
from registrations.models import Invitation
# from social_links import models as social_models
# from seo.route53 import can_send_email, make_mx_record
# from seo.search_backend import DESearchQuerySet
from usermodel.models import User
from mypartners.models import Tag
# from universal.accessibility import DOCTYPE_CHOICES, LANGUAGE_CODES_CHOICES
from universal.helpers import get_domain, get_object_or_none

class JobsByBuidManager(models.Manager):
    def get_queryset(self):
        queryset = super(JobsByBuidManager, self).get_query_set()
        if settings.SITE_BUIDS:
            return queryset.filter(buid__in=settings.SITE_BUIDS)
        else:
            return queryset


class ConfigBySiteManager(models.Manager):
    def get_queryset(self):
        return super(ConfigBySiteManager, self).get_queryset().filter(
            seosite__id=settings.SITE_ID)


# class GoogleAnalyticsBySiteManager(models.Manager):
#     def get_queryset(self):
#         return super(GoogleAnalyticsBySiteManager, self).get_queryset().filter(
#             seosite__id=settings.SITE_ID)


class jobListing (models.Model):
    def __unicode__(self):
        return self.title

    class Meta:
        verbose_name = 'Job Listing'
        verbose_name_plural = 'Job Listings'

    city = models.CharField(max_length=200, blank=True, null=True)
    citySlug = models.SlugField(blank=True, null=True)
    country = models.CharField(max_length=200, blank=True, null=True)
    countrySlug = models.SlugField(blank=True, null=True)
    country_short = models.CharField(max_length=3, blank=True, null=True,
                                     db_index=True)
    date_new = models.DateTimeField('date new')
    date_updated = models.DateTimeField('date updated')
    description = models.TextField()
    hitkey = models.CharField(max_length=50)
    link = models.URLField(max_length=200)
    location = models.CharField(max_length=200, blank=True, null=True)
    reqid = models.CharField(max_length=50, blank=True, null=True)
    state = models.CharField(max_length=200, blank=True, null=True)
    stateSlug = models.SlugField(blank=True, null=True)
    state_short = models.CharField(max_length=3, blank=True, null=True)
    title = models.CharField(max_length=200)
    titleSlug = models.SlugField(max_length=200, blank=True, null=True,
                                 db_index=True)
    uid = models.IntegerField(db_index=True, unique=True)
    zipcode = models.CharField(max_length=15, null=True, blank=True)

    objects = models.Manager()
    this_site = JobsByBuidManager()

    def return_id(self):
        return self.id

    def save(self):
        self.titleSlug = slugify(self.title)
        self.countrySlug = slugify(self.country)
        self.stateSlug = slugify(self.state)
        self.citySlug = slugify(self.city)

        if self.city and self.state_short:
            self.location = self.city + ', ' + self.state_short
        elif self.city and self.country_short:
            self.location = self.city + ', ' + self.country_short
        elif self.state and self.country_short:
            self.location = self.state + ', ' + self.country_short
        elif self.country:
            self.location = 'Virtual, ' + self.country_short
        else:
            self.location = 'Global'

        super(jobListing, self).save()

class Company(models.Model):
    """
    This model defines companies that come from various job sources (currently
    business units).

    """
    def __unicode__(self):
        return self.name

    natural_key = __unicode__

    class Meta:
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'
        ordering = ['name']
        unique_together = ('name', 'user_created')

    def save(self, *args, **kwargs):
        exists = str(self.pk).isdigit()

        self.company_slug = slugify(self.name)
        super(Company, self).save(*args, **kwargs)

        if not exists:
            default_tags = [
                {"name": "Veteran", "hex_color": "5EB94E"},
                {"name": "Female", "hex_color": "4BB1CF"},
                {"name": "Minority", "hex_color": "FAA732"},
                {"name": "Disability", "hex_color": "808A9A"},
                {"name": "Disabled Veteran", "hex_color": "659274"}
            ]
            for tag in default_tags:
                Tag.objects.get_or_create(company=self, **tag)

    def associated_jobs(self):
        b_units = self.job_source_ids.all()
        job_count = 0
        for unit in b_units:
            job_count += unit.associated_jobs
        return job_count

    def featured_on(self):
        return ", ".join(self.seosite_set.all().values_list("domain",
                                                            flat=True))

    @property
    def company_user_count(self):
        """
        Counts how many users are mapped to this company. This is useful for
        determining which company to map companyusers to when two company
        instances have very similar names.

        It is treated as a property of the model.

        """
        return self.companyuser_set.count()

    # admins = models.ManyToManyField(User, through='CompanyUser')
    name = models.CharField('Name', max_length=200)
    company_slug = models.SlugField('Company Slug', max_length=200, null=True,
                                    blank=True)
    # job_source_ids = models.ManyToManyField('BusinessUnit')
    logo_url = models.URLField('Logo URL', max_length=200, null=True,
                               blank=True, help_text="The url for the 100x50 "
                               "logo image for this company.")
    linkedin_id = models.CharField('LinkedIn Company ID',
                                   max_length=20, null=True, blank=True,
                                   help_text="The LinkedIn issued company "
                                   "ID for this company.")
    og_img = models.URLField('Open Graph Image URL', max_length=200, null=True,
                             blank=True, help_text="The url for the large "
                             "format logo for use when sharing jobs on "
                             "LinkedIn, and other social platforms that support"
                             " OpenGraph.")
    canonical_microsite = models.URLField('Canonical Microsite URL',
                                          max_length=200, null=True, blank=True,
                                          help_text="The primary "
                                          "directemployers microsite for this "
                                          "company.")
    member = models.BooleanField('DirectEmployers Association Member',
                                 default=False)
    # social_links = generic.GenericRelation(social_models.SocialLink,
    #                                        object_id_field='id',
    #                                        content_type_field='content_type')
    digital_strategies_customer = models.BooleanField(
        'Digital Strategies Customer', default=False)
    enhanced = models.BooleanField('Enhanced', default=False)
    # site_package = models.ForeignKey('postajob.SitePackage', null=True,
    #                                  on_delete=models.SET_NULL)

    # prm_saved_search_sites = models.ManyToManyField('SeoSite', null=True,
    #                                                 blank=True)

    # Permissions
    prm_access = models.BooleanField(default=False)
    product_access = models.BooleanField(default=False)
    posting_access = models.BooleanField(default=False)
    user_created = models.BooleanField(default=False)

    def slugified_name(self):
        return slugify(self.name)

    # def get_seo_sites(self):
    #     """
    #     Retrieves a given company's microsites

    #     Inputs:
    #     :company: Company whose microsites are being retrieved

    #     Outputs:
    #     :microsites: List of microsites
    #     """
    #     buids = self.job_source_ids.all()

    #     microsites = SeoSite.objects.filter(models.Q(business_units__in=buids)
    #                                         | models.Q(canonical_company=self))
    #     return microsites

    def user_has_access(self, user):
        """
        In order for a user to have access they must be a CompanyUser
        for the Company.
        """
        return user in self.admins.all()

    @property
    def has_packages(self):
        return self.sitepackage_set.filter(
            sites__in=settings.SITE.postajob_site_list()).exists()


# class FeaturedCompany(models.Model):
#     """
#     Featured company option for a given multi-company SeoSite.
#     """
#     seosite = models.ForeignKey('SeoSite')
#     company = models.ForeignKey('Company')
#     is_featured = models.BooleanField('Featured Company?', default=False)


class SpecialCommitment(models.Model):
    """
    Special Commits are used on a site by site basis to place Schema.org
    tags on the site. This flags the site as containing jobs for a distinct
    set of job seekers.
    """
    name = models.CharField(max_length=200)
    commit = models.CharField(
        'Schema.org Commit Code',
        help_text="VeteranCommit, SummerCommit, etc...",
        max_length=200)

    def __unicode__(self):
        return self.name

    def committed_sites(self):
        return ", ".join(self.seosite_set.all().values_list("domain",
                                                            flat=True))

    class Meta:
        verbose_name = "Special Commitment"
        verbose_name_plural = "Special Commitments"


class CompanyUser(models.Model):
    GROUP_NAME = 'Employer'
    ADMIN_GROUP_NAME = 'Partner Microsite Admin'

    user = models.ForeignKey(User)
    company = models.ForeignKey(Company)
    date_added = models.DateTimeField(auto_now=True)
    group = models.ManyToManyField('auth.Group', blank=True)

    def __unicode__(self):
        return 'Admin %s for %s' % (self.user.email, self.company.name)

    def save(self, *args, **kwargs):
        """
        Adds the user to the Employer group if it wasn't already a member.

        If the user is already a member of the Employer group, the Group app
        is smart enough to not add it a second time.
        """

        using = kwargs.get('using', 'default')

        inviting_user = kwargs.pop('inviting_user', None)
        group = Group.objects.using(using).get(name=self.GROUP_NAME)
        self.user.groups.add(group)

        # There are some cases where a CompanyUser may be adding themselves
        # and not being invited, so only create an invitation if we can
        # determine who is inviting them.
        if not self.pk and inviting_user:
            Invitation(invitee=self.user, inviting_company=self.company,
                       added_permission=group,
                       inviting_user=inviting_user).save(using=using)

        return super(CompanyUser, self).save(*args, **kwargs)

    class Meta:
        unique_together = ('user', 'company')
        db_table = 'mydashboard_companyuser'

    def make_purchased_microsite_admin(self):
        group, _ = Group.objects.get_or_create(name=self.ADMIN_GROUP_NAME)
        self.group.add(group)
        self.save()


class BillboardImage(models.Model):
    def __unicode__(self):
        return "%s: %s" % (self.title, str(self.id))

    title = models.CharField('Title', max_length=200)
    group = models.ForeignKey('auth.group', null=True)
    image_url = models.URLField('Image URL', max_length=200)
    copyright_info = models.CharField('Copyright Info', max_length=200)
    source_url = models.URLField('Source URL', max_length=200)
    logo_url = models.URLField('Logo Image URL',
                               max_length=200, null=True, blank=True)
    sponsor_url = models.URLField('Logo Sponsor URL',
                                  max_length=200, null=True, blank=True)

    class Meta:
        verbose_name = 'Billboard Image'
        verbose_name_plural = 'Billboard Images'

    def on_sites(self):
        return ", ".join(self.seosite_set.all().values_list("domain",
                                                            flat=True))

    def number_of_hotspots(self):
        return self.billboardhotspot_set.all().count()

    def has_hotspots(self):
        # returns True if the the billboard has hotspots.
        return self.number_of_hotspots() > 0
    has_hotspots.boolean = True


class BillboardHotspot(models.Model):
    billboard_image = models.ForeignKey(BillboardImage)
    title = models.CharField('Title', max_length=50,
                             help_text="Max 50 characters")
    text = models.CharField('Text', max_length=140,
                            help_text="Max 140 characters.  "
                                      "Use HTML markup for line breaks "
                                      "and formatting.")
    url = models.URLField('URL', null=True, blank=True)
    display_url = models.TextField('Display URL', null=True, blank=True)
    offset_x = models.IntegerField('Offset X')
    offset_y = models.IntegerField('Offset Y')
    primary_color = models.CharField('Primary Color', max_length=6,
                                     default='5A6D81')
    font_color = models.CharField('Font Color', max_length=6, default='FFFFFF')
    border_color = models.CharField('Border Color', max_length=6,
                                    default='FFFFFF')

    class Meta:
        verbose_name = 'Billboard Hotspot'


class SeoSite(Site):
    class Meta:
        verbose_name = 'Seo Site'
        verbose_name_plural = 'Seo Sites'

    def associated_companies(self):
        buids = self.business_units.all()
        return Company.objects.filter(job_source_ids__id__in=buids)

    def network_sites(self):
        return SeoSite.objects.filter(site_tags__site_tag='network')

    def network_sites_and_this_site(self):
        query = models.Q(site_tags__site_tag='network') | models.Q(id=self.id)
        return SeoSite.objects.filter(query)

    def this_site_only(self):
        # This should return self, but I really want to stay consistent and
        # return a QuerySet so that all the functions can be used
        # identically without knowing the value of postajob_filter_type.
        return SeoSite.objects.filter(id=self.id)

    def company_sites(self):
        companies = self.associated_companies()
        company_buids = companies.values_list('job_source_ids', flat=True)

        sites = SeoSite.objects.filter(business_units__id__in=company_buids)
        return sites.exclude(site_tags__site_tag='network')

    def network_and_company_sites(self):
        companies = self.associated_companies()
        company_buids = companies.values_list('job_source_ids', flat=True)

        query = [models.Q(business_units__id__in=company_buids),
                 models.Q(site_tags__site_tag='network')]

        return SeoSite.objects.filter(reduce(operator.or_, query))

    def all_sites(self):
        return SeoSite.objects.all()

    postajob_filter_options_dict = {
        'network sites only': network_sites,
        'network sites and this site': network_sites_and_this_site,
        'this site only': this_site_only,
        'network sites and sites associated '
        'with the company that owns this site': network_and_company_sites,
        'sites associated with the company that owns this site': company_sites,
        'all sites': all_sites,
    }
    postajob_filter_options = tuple([(k, k) for k in
                                     postajob_filter_options_dict.keys()])

    group = models.ForeignKey('auth.Group', null=True)
    # facets = models.ManyToManyField('CustomFacet', null=True, blank=True,
    #                                 through='SeoSiteFacet')
    # configurations = models.ManyToManyField('Configuration', blank=True)
    # google_analytics = models.ManyToManyField('GoogleAnalytics', null=True,
    #                                           blank=True)
    # business_units = models.ManyToManyField('BusinessUnit', null=True,
    #                                         blank=True)
    featured_companies = models.ManyToManyField('Company', null=True,
                                                blank=True)
    # microsite_carousel = models.ForeignKey('social_links.MicrositeCarousel',
    #                                        null=True, blank=True,
    #                                       on_delete=models.SET_NULL)
    billboard_images = models.ManyToManyField('BillboardImage', blank=True,
                                              null=True)
    site_title = models.CharField('Site Title', max_length=200, blank=True,
                                  default='')
    site_heading = models.CharField('Site Heading', max_length=200, blank=True,
                                    default='')
    site_description = models.CharField('Site Description', max_length=200,
                                        blank=True, default='')
    # google_analytics_campaigns = models.ForeignKey('GoogleAnalyticsCampaign',
    #                                                null=True, blank=True)
    # view_sources = models.ForeignKey('ViewSource', null=True, blank=True)
    # ats_source_codes = models.ManyToManyField('ATSSourceCode', null=True,
    #                                           blank=True)
    special_commitments = models.ManyToManyField('SpecialCommitment',
                                                 blank=True, null=True)
    # site_tags = models.ManyToManyField('SiteTag', blank=True, null=True)

    # The "designated" site package specific to this seosite.
    # This site should be the only site attached to site_package.
    site_package = models.ForeignKey('postajob.SitePackage', null=True,
                                     blank=True, on_delete=models.SET_NULL)

    postajob_filter_type = models.CharField(max_length=255,
                                            choices=postajob_filter_options,
                                            default='this site only')
    canonical_company = models.ForeignKey('Company', blank=True, null=True,
                                          on_delete=models.SET_NULL,
                                          related_name='canonical_company_for')
    
    # parent_site = NonChainedForeignKey('self', blank=True, null=True,
    #                                  on_delete=models.SET_NULL,
    #                                  related_name='child_sites')                                      
                                        
    email_domain = models.CharField(max_length=255, default='my.jobs')

    def clean_domain(self):
        """
        Ensures that an MX record exists for a given domain, if possible.
        This allows the domain as an option for email_domain.
        """
        if not hasattr(mail, 'outbox'):
            # Don't try creating MX records when running tests.
            try:
                can_send = can_send_email(self.domain)
                if can_send is not None and not can_send:
                    make_mx_record(self.domain)
            except (DNSError, DNSServerError):
                # This will create some false negatives but there's not much
                # to be done about that aside from multiple retries.
                pass
        return self.domain

    def clean_email_domain(self):
        # TODO: Finish after MX Records are sorted out
        # Determine if the company actually has permission to use the domain.
        domains = self.canonical_company.get_seo_sites().values_list('domain',
                                                                     flat=True)
        domains = [get_domain(domain) for domain in domains]
        domains.append('my.jobs')
        if self.email_domain not in domains:
            raise ValidationError('You can only send emails from a domain '
                                  'that is associated with your company.')

        # Ensure that we have an MX record for the domain.
        if not can_send_email(self.email_domain):
            raise ValidationError('You do not currently have the ability '
                                  'to send emails from this domain.')
        return self.email_domain

    def postajob_site_list(self):
        filter_function = self.postajob_filter_options_dict.get(
            self.postajob_filter_type, SeoSite.this_site_only)
        return filter_function(self)

    # @staticmethod
    # def clear_caches(sites):
    #     # Increment Configuration revision attributes, which is used
    #     # when calculating a custom_cache_pages cache key prefix.
    #     # This will effectively expire the page cache for custom_cache_page
    #     # views_
    #     configs = Configuration.objects.filter(seosite__in=sites)
    #     # https://docs.djangoproject.com/en/dev/topics/db/queries/#query-expressions
    #     configs.update(revision=models.F('revision') + 1)
    #     Configuration.clear_caches(configs)
    #     # Delete domain-based cache entries that don't use the
    #     # custom_cache_page prefix
    #     site_cache_keys = ['%s:SeoSite' % site.domain for site in sites]
    #     buid_cache_keys = ['%s:buids' % key for key in site_cache_keys]
    #     social_cache_keys = ['%s:social_links' % site.domain for site in sites]
    #     cache.delete_many(site_cache_keys + buid_cache_keys + social_cache_keys)

    def email_domain_choices(self,):
        from postajob.models import CompanyProfile
        profile = get_object_or_none(CompanyProfile,
                                     company=self.canonical_company)
        email_domain_field = SeoSite._meta.get_field('email_domain')
        choices = [
            (email_domain_field.get_default(), email_domain_field.get_default()),
            (self.domain, self.domain),
        ]
        if profile and profile.outgoing_email_domain:
            choices.append((profile.outgoing_email_domain,
                            profile.outgoing_email_domain))
        return choices    

    def save(self, *args, **kwargs):
        #always call clean if the parent_site entry exists to prevent invalid
        #relationships
        if self.parent_site: self.clean_fields()
        super(SeoSite, self).save(*args, **kwargs)
        self.clear_caches([self])
    
    def user_has_access(self, user):
        """
        In order for a user to have access they must be a CompanyUser
        for the Company that owns the SeoSite.
        """
        site_buids = self.business_units.all()
        companies = Company.objects.filter(job_source_ids__in=site_buids)
        user_companies = user.get_companies()
        for company in companies:
            if company not in user_companies:
                return False
        return True

    def get_companies(self):
        site_buids = self.business_units.all()
        return Company.objects.filter(job_source_ids__in=site_buids).distinct()































class Country(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    abbrev = models.CharField(max_length=255, blank=True, null=True,
                              db_index=True)
    abbrev_short = models.CharField(max_length=255, blank=True, null=True,
                                    db_index=True)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = 'Country'
        verbose_name_plural = 'Countries'


class State(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    nation = models.ForeignKey(Country)

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together = ('name', 'nation')
        verbose_name = 'State'
        verbose_name_plural = 'States'


class City(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    nation = models.ForeignKey(Country)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = 'City'
        verbose_name_plural = 'Cities'


class CustomPage(FlatPage):
    group = models.ForeignKey(Group, blank=True, null=True)
    meta = models.TextField(blank=True)
    meta_description = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Custom Page'
        verbose_name_plural = 'Custom Pages'