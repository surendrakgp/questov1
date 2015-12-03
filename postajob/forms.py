from authorize import AuthorizeInvalidError, AuthorizeResponseError
from datetime import date, datetime, timedelta
# from fsm.widget import FSM

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.validators import validate_email, URLValidator
from django.core.urlresolvers import reverse_lazy
from django import forms
from django.forms import (CharField, CheckboxSelectMultiple,
                          HiddenInput, IntegerField, ModelMultipleChoiceField,
                          RadioSelect, Select, TextInput, ChoiceField)
from django.forms.models import modelformset_factory, BaseModelFormSet

from seo.models import Company, CompanyUser, SeoSite
from mypartners.widgets import SplitDateDropDownField
from postajob.fields import NoValidationChoiceField, SelectWithOptionClasses
from postajob.models import (CompanyProfile, Invoice, Job, OfflinePurchase,
                             OfflineProduct, Package, Product, ProductGrouping,
                             ProductOrder, PurchasedProduct, PurchasedJob,
                             SitePackage, JobLocation)
from postajob.payment import authorize_card, get_card, settle_transaction
from postajob.widgets import ExpField
from universal.forms import RequestForm
from universal.helpers import get_object_or_none, get_company


def is_superuser_in_admin(request):
    return request.path.startswith('/admin') and request.user.is_superuser


class BaseJobForm(RequestForm):
    class Meta:
        exclude = ('is_syndicated', 'created_by', )

    class Media:
        css = {
            'all': ('postajob.159-9.css', )
        }
        js = ('postajob.160-13.js', )

    apply_choices = [('link', "Link"), ('email', 'Email'),
                     ('instructions', 'Instructions')]
    apply_type = CharField(label='Application Method',
                           widget=RadioSelect(choices=apply_choices),
                           help_text=Job.help_text['apply_type'])

    apply_email = CharField(required=False, max_length=255,
                            label='Apply Email',
                            help_text=Job.help_text['apply_email'],
                            widget=TextInput(attrs={'size': 50}))
    apply_link = CharField(required=False, max_length=255,
                           label='Apply Link',
                           help_text=Job.help_text['apply_link'],
                           widget=TextInput(attrs={'rows': 1, 'size': 50}))
    date_expired = IntegerField(label='Expires In',
                                help_text="The length of time before the job "
                                          "expires.",
                                widget=Select(
                                    choices=Product.max_job_length_choices))

    def __init__(self, *args, **kwargs):
        super(BaseJobForm, self).__init__(*args, **kwargs)

        # Set the starting apply option.
        if self.instance and self.instance.apply_info:
            self.initial['apply_type'] = 'instructions'
        else:
            # convert apply_link to email
            if self.instance.apply_link.startswith("mailto:"):
                self.initial['apply_email'] = self.instance.apply_link.split(
                    'mailto:')[1]
                self.initial['apply_type'] = 'email'
            else:
                # This works because apply_email is actually a link
                # that uses mailto:
                self.initial['apply_type'] = 'link'

        if not is_superuser_in_admin(self.request):
            # Remove the option to set the company.
            self.fields['owner'].widget = HiddenInput()
            self.initial['owner'] = self.company

    def clean_apply_link(self):
        """
        If the apply_link is a url and not a mailto, format the link
        appropriately and confirm it really is a url.

        """
        apply_link = self.cleaned_data.get('apply_link')
        if apply_link and apply_link.startswith('mailto:'):
            return apply_link
        if apply_link and not (apply_link.startswith('http://') or
                               apply_link.startswith('https://')):
            apply_link = 'http://{link}'.format(link=apply_link)
        if apply_link:
            URLValidator(apply_link)
        return apply_link


    def clean(self):
        apply_info = self.cleaned_data.get('apply_info')
        apply_link = self.cleaned_data.get('apply_link')
        apply_email = self.cleaned_data.get('apply_email')

        # Require one set of apply instructions.
        if not any([apply_info, apply_link, apply_email]):
            msg = 'You must supply some type of appliction information.'
            self._errors['apply_type'] = self.error_class([msg])
            raise ValidationError(msg)
        # Allow only one set of apply instructions.
        if sum([1 for x in [apply_info, apply_link, apply_email] if x]) > 1:
            msg = 'You can only supply one application method.'
            self._errors['apply_type'] = self.error_class([msg])
            raise ValidationError(msg)

        if apply_email:
            # validate_email() raises its own ValidationError.
            validate_email(apply_email)
            # If the apply instructions are an email, it needs to be
            # reformatted as a mailto and saved as the link.
            apply_email = 'mailto:{link}'.format(link=apply_email)
            self.cleaned_data['apply_link'] = apply_email
        return self.cleaned_data

    def save(self, commit=True):
        self.instance.created_by = self.request.user
        return super(BaseJobForm, self).save(commit)


class JobLocationForm(forms.ModelForm):
    state = NoValidationChoiceField(choices=JobLocation.state_choices,
                                    widget=SelectWithOptionClasses())
    country = ChoiceField(choices=JobLocation.country_choices,
                          initial='United States')
    region = CharField(max_length=255, required=False)

    class Meta:
        fields = ('city', 'state', 'region', 'country', 'zipcode')
        excluded = ('guid', 'state_short', 'country_short')
        model = JobLocation

    def clean(self):
        cleaned_data = self.cleaned_data
        if (cleaned_data.get('country') not in ["United States", "Canada"]
                and not self.instance.pk):
            region = cleaned_data.get('region')
            if region:
                cleaned_data['state'] = region
            else:
                raise ValidationError('State or region is required.')
        return cleaned_data


class BaseJobLocationFormSet(BaseModelFormSet):
    def clean(self):
        if any(self.errors):
            return

        has_locations = (all(form.has_changed for form in self.forms) and
                         all(not data['DELETE'] for data in self.cleaned_data))

        if not self.forms or not has_locations:
            raise ValidationError("Job postings must have at least one "
                                  "location")

    def save(self, commit=True, delete=None):
        """
        Overrides BaseModelFormSet.save to add an additional parameter for which
        forms are to be deleted

        Inputs:
        :commit: Commit changes to database
        :delete: Form indices to be deleted; Defaults to None

        Outputs:
        :saved: List of saved items
        """
        # This represents new locations that were removed before saving,
        # meaning they didn't have ids when the page was loaded.
        # We can fake deleting these by just not saving them.
        delete = delete or []
        saved = []

        # Filter out blank strings from the list of ids to be deleted
        deleted_ids = filter(lambda x: bool(x),
                             [deleted['id'].value()
                              for deleted in self.deleted_forms])
        for index, form in enumerate(self.forms):
            id_ = form['id'].value()
            if id_ in deleted_ids or index in delete:
                if id_ and commit:
                    JobLocation.objects.get(pk=id_).delete()
            else:
                saved.append(form.save(commit))
        return saved


JobLocationFormSet = modelformset_factory(JobLocation, form=JobLocationForm,
                                          formset=BaseJobLocationFormSet,
                                          extra=0, can_delete=True)


class JobForm(BaseJobForm):
    class Meta:
        fields = ('title', 'reqid', 'description',
                  'date_expired', 'is_expired', 'autorenew', 'apply_type',
                  'apply_link', 'apply_email', 'apply_info', 'owner',
                  'post_to', 'site_packages')
        model = Job

    post_to_choices = [('network', 'The entire My.jobs network'),
                       ('site', 'A specific site you own'), ]
    post_to = CharField(label='Post to', help_text=Job.help_text['post_to'],
                        widget=RadioSelect(attrs={'id': 'post-to-selector'},
                                           choices=post_to_choices),
                        initial='site')

    def __init__(self, *args, **kwargs):
        super(JobForm, self).__init__(*args, **kwargs)
        if is_superuser_in_admin(self.request):
            sites = SeoSite.objects.all()
        else:
            sites = self.company.get_seo_sites()

        site_packages_widget = FSM('Sites', reverse_lazy('site_fsm'), async=True)
        # For a single job posting by a member company to a microsite
        # we consider each site an individual site package but the
        # site_package for a site is only created when it's first used,
        # so we use SeoSite as the queryset here instead of SitePackage.
        self.fields['site_packages'] = ModelMultipleChoiceField(
            queryset=sites, help_text='', label='Site', required=False,
            widget=site_packages_widget)

        if self.instance.pk and self.instance.site_packages:
            packages = self.instance.site_packages.all()
            # If the only site package is the company package, then the
            # current job must be posted to all company and network sites.
            if (packages.count() == 1 and
                    packages[0] == self.instance.owner.site_package):
                self.initial['post_to'] = 'network'

            # Since we're not using actual site_packages for the site_packages,
            # the initial data also needs to be manually set.
            initial = [site.pk for site in self.instance.on_sites()]
            self.initial['site_packages'] = {site: 'selected'
                                             for site in initial}

        # Set the starting date expired option
        if self.instance and self.instance.date_expired:
            date_new = getattr(
                self.instance, 'date_new', datetime.now()).date()
            days = (self.instance.date_expired - date_new).days
            self.initial['date_expired'] = days
        else:
            # Select the longest duration
            self.initial['date_expired'] = self.fields[
                'date_expired'].widget.choices[-1][0]

    def clean_date_expired(self):
        date_new = self.instance.date_new or datetime.now()

        date_expired = self.cleaned_data['date_expired']
        return date_new + timedelta(date_expired)

    def clean_site_packages(self):
        """
        Convert from SeoSite or network sites to a SitePackage.

        """
        if self.cleaned_data.get('post_to') == 'network':
            company = self.cleaned_data.get('owner', self.company)
            if not hasattr(company, 'site_package') or not company.site_package:
                package = SitePackage()
                package.make_unique_for_company(company)
            site_packages = [company.site_package]
        else:
            sites = self.cleaned_data.get('site_packages')
            site_packages = []
            for site in sites:
                if not hasattr(site, 'site_package') or not site.site_package:
                    # If a site doesn't already have a site_package specific
                    # to it create one.
                    package = SitePackage(name=site.domain)
                    package.make_unique_for_site(site)
                site_packages.append(site.site_package)

        return site_packages

    def get_field_sets(self):
        field_sets = [
            [self['title'], self['description'], self['reqid']],
            [self['apply_type'], self['apply_link'], self['apply_email'],
             self['apply_info']],
            [self['date_expired'], self['is_expired']],
            [self['post_to'], self['site_packages']]
        ]
        return field_sets

    def save(self, commit=True):
        sites = self.cleaned_data['site_packages']
        job = super(JobForm, self).save(commit)
        # The pk must exist before the manytomany relationship can be created.
        if not hasattr(job, 'pk') or not job.pk:
            job.save()
        [job.site_packages.add(s) for s in sites]
        # Add to solr now that we know we have the correct sites.
        job.add_to_solr()
        return job


class PurchasedJobBaseForm(JobForm):
    class Meta:
        fields = ('title', 'reqid', 'description', 'date_expired',
                  'is_expired', 'autorenew', 'apply_type', 'apply_link',
                  'apply_email', 'apply_info', 'owner', 'post_to')
        model = PurchasedJob
        purchased_product = None

    def clean_date_expired(self):
        try:
            date_new = self.instance.job_ptr.date_new
        except Job.DoesNotExist:
            # We are adding a job, not editing one
            date_new = datetime.now()

        date_expired = self.cleaned_data['date_expired']
        return date_new + timedelta(date_expired)

    def clean(self):
        date_expired = self.cleaned_data.get('date_expired').date()
        is_expired = self.cleaned_data.get('is_expired')

        if not hasattr(self, 'purchased_product'):
            self.purchased_product = self.cleaned_data.get('purchased_product')

        if (hasattr(self.instance, 'max_expired_date') and
                self.instance.max_expired_date):
            max_expired_date = self.instance.max_expired_date
        else:
            max_job_length = self.purchased_product.max_job_length
            max_expired_date = (date.today() + timedelta(max_job_length))

        # Honestly just backup, because this can't really happen.
        if not is_expired and date.today() >= max_expired_date:
            msg = 'This job has expired and can no longer be relisted.'
            self._errors['is_expired'] = self.error_class([msg])
            raise ValidationError(msg)

        if date_expired > max_expired_date:
            msg = 'The job must expire before %s.' % max_expired_date
            self._errors['date_expired'] = self.error_class([msg])
            raise ValidationError(msg)

        return super(PurchasedJobBaseForm, self).clean()

    def save(self, commit=True):
        job = super(PurchasedJobBaseForm, self).save(commit)
        job.add_to_solr()
        return job


class PurchasedJobForm(PurchasedJobBaseForm):
    def __init__(self, *args, **kwargs):
        self.purchased_product = kwargs.pop('product', None)
        super(PurchasedJobForm, self).__init__(*args, **kwargs)
        self.fields.pop('post_to', None)
        self.initial['site_packages'] = self.fields['site_packages'].queryset

        # Restrict choices for date expiration to those determined by the
        # product
        max_job_length = self.purchased_product.max_job_length
        job_length_index = [
            choice[0] for choice in 
            self.fields['date_expired'].widget.choices].index(max_job_length)

        self.fields['date_expired'].widget.choices = self.fields[
            'date_expired'].widget.choices[:job_length_index+1]

        # Set the starting date expired option
        if self.instance and self.instance.date_expired:
            date_new = getattr(
                self.instance, 'date_new', datetime.now()).date()
            days = (self.instance.date_expired - date_new).days
            self.initial['date_expired'] = days
        else:
            # Select the longest duration
            self.initial['date_expired'] = self.fields[
                'date_expired'].widget.choices[-1][0]

    def get_field_sets(self):
        field_sets = [
            [self['title'], self['description'], self['reqid']],
            [self['apply_type'], self['apply_link'], self['apply_email'],
             self['apply_info']],
            [self['date_expired'], self['is_expired']],
        ]
        return field_sets

    def save(self, commit=True):
        # Every time a prooduct is edited it needs to go back through the
        # approval process.
        self.instance.is_approved = False

        self.instance.purchased_product = self.purchased_product
        return super(PurchasedJobForm, self).save(commit)


class PurchasedJobAdminForm(PurchasedJobBaseForm):
    class Meta:
        model = PurchasedJobBaseForm.Meta.model
        extra_fields = ['is_approved', 'purchased_product', ]
        fields = tuple(list(PurchasedJobBaseForm.Meta.fields) + extra_fields)


class SitePackageForm(RequestForm):
    class Meta:
        model = SitePackage
        fields = ('name', 'sites', 'owner', )

    sites_widget = admin.widgets.FilteredSelectMultiple('Sites', False)
    sites = ModelMultipleChoiceField(SeoSite.objects.all(),
                                     label="On Sites",
                                     required=False,
                                     widget=sites_widget)

    def __init__(self, *args, **kwargs):
        super(SitePackageForm, self).__init__(*args, **kwargs)
        if not is_superuser_in_admin(self.request):
            # Limit a user's access to only sites they own.
            self.fields['sites'].queryset = self.request.user.get_sites()

            # Limit a user to only companies they have access to.
            self.fields['owner'].queryset = self.request.user.get_companies()


class ProductForm(RequestForm):
    class Meta:
        model = Product
        fields = ('name', 'package', 'owner', 'cost',
                  'posting_window_length', 'max_job_length',
                  'job_limit', 'num_jobs_allowed', 'requires_approval',
                  'is_displayed', )

    class Media:
        css = {
            'all': ('postajob.159-9.css', )
        }
        js = ('postajob.160-13.js', )

    job_limit_choices = [('unlimited', "Unlimited"),
                         ('specific', 'A Specific Number'), ]
    job_limit = CharField(
        label='Job Limit', widget=RadioSelect(choices=job_limit_choices),
        help_text=Product.help_text['num_jobs_allowed'], initial='unlimited'
    )

    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        if not is_superuser_in_admin(self.request):
            # Update querysets based on what the user should have
            # access to.
            self.fields['owner'].widget = HiddenInput()
            self.initial['owner'] = self.company

            packages = Package.objects.user_available()
            packages = packages.filter_company([self.company])
            self.fields['package'].queryset = packages
            # remove "------" option from select box
            self.fields['package'].empty_label = None

        if self.instance.pk and self.instance.num_jobs_allowed != 0:
            self.initial['job_limit'] = 'specific'

        profile = get_object_or_none(CompanyProfile, company=self.company)
        if (not profile or not
                (profile.authorize_net_login and
                 profile.authorize_net_transaction_key)):
            if is_superuser_in_admin(self.request):
                # Superusers should know better than to break things
                self.fields["cost"].help_text = ("This member needs to "
                                                 "have added Authorize.net "
                                                 "account information "
                                                 "before we can safely "
                                                 "charge for posting. If "
                                                 "that hasn't been added, "
                                                 "bad things may happen.")
            else:
                self.fields['cost'].help_text = ('You cannot charge for '
                                                 'jobs until you '
                                                 '<a href=%s>add your '
                                                 'Authorize.net account '
                                                 'information</a>.' %
                                                 reverse_lazy('companyprofile_add'))
                self.initial['cost'] = 0
                self.fields['cost'].widget.attrs['readonly'] = True
                setattr(self, 'no_payment_info', True)

    def clean_cost(self):
        cost = self.cleaned_data.get('cost')
        profile = get_object_or_none(CompanyProfile,
                                     company=self.cleaned_data.get('owner'))

        # cost comes through as a Decimal, which has a handy is_zero method;
        # cost is required, so we don't have to worry about None
        if not cost.is_zero() and (not profile or
                                   not (profile.authorize_net_login and
                                        profile.authorize_net_transaction_key)):
            raise ValidationError('This company does not have Authorize.net '
                                  'credentials defined - product must be free')
        return cost

    def clean(self):
        data = self.cleaned_data

        num_jobs_selector = data.get('job_limit')
        if num_jobs_selector == 'unlimited':
            self.cleaned_data['num_jobs_allowed'] = 0

        if hasattr(self, 'no_payment_info') and not data['requires_approval']:
            msg = 'Free jobs require approval.'
            self._errors['requires_approval'] = self.error_class([msg])
            raise ValidationError(msg)

        return self.cleaned_data


class ProductGroupingForm(RequestForm):
    class Meta:
        model = ProductGrouping
        exclude = ('display_order', )
        fields = ('products', 'display_title', 'explanation',
                  'name', 'owner', 'is_displayed', )

    class Media:
        css = {
            'all': ('postajob.159-9.css', )
        }

    products_widget = CheckboxSelectMultiple()
    products = ModelMultipleChoiceField(Product.objects.all(),
                                        widget=products_widget)

    def __init__(self, *args, **kwargs):
        super(ProductGroupingForm, self).__init__(*args, **kwargs)

        if not is_superuser_in_admin(self.request):
            kwargs = {'owner': self.company}
            self.fields['products'].queryset = \
                self.fields['products'].queryset.filter(**kwargs)

            self.initial['owner'] = self.company
            self.fields['owner'].widget = HiddenInput()

    def save(self, commit=True):
        products = self.cleaned_data.pop('products')
        instance = super(ProductGroupingForm, self).save(commit)
        if not instance.pk:
            instance.save()

        delete_orders = ProductOrder.objects.filter(group=instance)
        delete_orders = delete_orders.exclude(product__in=products)
        for product in products:
            ordered_product, _ = ProductOrder.objects.get_or_create(
                product=product, group=instance)
            ordered_product.display_order = 0
            ordered_product.save()
        delete_orders.delete()
        return instance


def make_company_from_form(form_instance):
    """
    Makes a Company, CompanyUser, and CompanyProfile from a form instance.
    Form instance must have a new company_name in form_instance.cleaned_data.
    """

    cleaned_data = form_instance.cleaned_data
    company_name = cleaned_data.get('company_name')
    form_instance.company = Company.objects.create(name=company_name,
                                                   user_created=True)
    cu = CompanyUser.objects.create(user=form_instance.request.user,
                                    company=form_instance.company)
    profile = CompanyProfile.objects.create(
        company=form_instance.company,
        address_line_one=cleaned_data.get('address_line_one'),
        address_line_two=cleaned_data.get('address_line_two'),
        city=cleaned_data.get('city'),
        country=cleaned_data.get('country'),
        state=cleaned_data.get('state'),
        zipcode=cleaned_data.get('zipcode'),
    )
    profile.save()
    cu.make_purchased_microsite_admin()


class PurchasedProductNoPurchaseForm(RequestForm):
    class Meta:
        model = PurchasedProduct
        fields = ('address_line_one', 'address_line_two', 'city', 'state',
                  'region', 'country', 'zipcode')

    class Media:
        css = {
            'all': ('postajob.159-9.css', )
        }
        js = (
            'postajob.160-13.js',
        )

    address_line_one = CharField(label='Address Line One')
    address_line_two = CharField(label='Address Line Two',
                                 required=False)
    state = NoValidationChoiceField(choices=JobLocation.state_choices,
                                    widget=SelectWithOptionClasses(),
                                    label='State',
                                    required=False)
    region = CharField(max_length=255, label='Region', required=False)
    country = ChoiceField(choices=JobLocation.country_choices,
                          initial='United States', label='Country',
                          required=False)
    city = CharField(label='City')
    zipcode = CharField(label='Zip Code')

    def __init__(self, *args, **kwargs):
        self.product = kwargs.pop('product', None)
        super(PurchasedProductNoPurchaseForm, self).__init__(*args, **kwargs)
        if not self.company:
            self.fields['company_name'] = CharField(label='Company Name')
            self.fields.keyOrder.insert(0, self.fields.keyOrder.pop())

    def clean(self):
        cleaned_data = self.cleaned_data
        if (cleaned_data.get('country') not in ["United States", "Canada"]
                and not self.instance.pk):
            region = cleaned_data.get('region')
            if region:
                cleaned_data['state'] = region
            else:
                raise ValidationError('State or region is required.')

        if not self.company:
            company_name = cleaned_data.get('company_name')
            msg = clean_company_name(company_name, None)
            if msg:
                self._errors['company_name'] = self.error_class([msg])
                raise ValidationError(msg)

        return self.cleaned_data

    def save(self, commit=True):
        if not self.company:
            make_company_from_form(self)

        invoice = Invoice.objects.create(
            address_line_one=self.cleaned_data.get('address_line_one'),
            address_line_two=self.cleaned_data.get('address_line_two'),
            card_exp_date=date.today(),
            card_last_four='FREE',
            city=self.cleaned_data.get('city'),
            country=self.cleaned_data.get('country'),
            first_name=self.request.user.first_name,
            last_name=self.request.user.last_name,
            owner=self.product.owner,
            state=self.cleaned_data.get('state'),
            transaction_type=Invoice.FREE,
            zipcode=self.cleaned_data.get('zipcode'),
        )
        self.instance.invoice = invoice
        self.instance.product = self.product
        self.instance.owner = self.company
        self.instance.paid = True

        super(PurchasedProductNoPurchaseForm, self).save(commit)

        invoice.save()
        invoice.send_invoice_email(other_recipients=[self.request.user.email])


class PurchasedProductForm(RequestForm):
    class Meta:
        model = PurchasedProduct
        fields = ('card_number', 'cvv', 'exp_date', 'first_name', 'last_name',
                  'address_line_one', 'address_line_two', 'city', 'state',
                  'region', 'country', 'zipcode')

    class Media:
        css = {
            'all': ('postajob.159-9.css', )
        }
        js = (
            'postajob.160-13.js',
        )

    card_number = CharField(label='Credit Card Number')
    cvv = IntegerField(label='CVV')
    exp_date = ExpField(label='Expiration Date')

    first_name = CharField(label='First Name on Card')
    last_name = CharField(label='Last Name on Card')
    address_line_one = CharField(label='Billing Address Line One')
    address_line_two = CharField(label='Billing Address Line Two',
                                 required=False)
    state = NoValidationChoiceField(choices=JobLocation.state_choices,
                                    widget=SelectWithOptionClasses(),
                                    label='Billing State')
    region = CharField(max_length=255, required=False,
                       label='Billing Region')
    country = ChoiceField(choices=JobLocation.country_choices,
                          initial='United States',
                          label='Billing Country')
    city = CharField(label='Billing City')
    zipcode = CharField(label='Billing Zip Code')

    def __init__(self, *args, **kwargs):
        self.product = kwargs.pop('product', None)
        super(PurchasedProductForm, self).__init__(*args, **kwargs)
        if not self.company:
            self.fields['company_name'] = CharField(label='Company Name')
            self.fields.keyOrder.insert(0, self.fields.keyOrder.pop())

    def clean(self):
        cleaned_data = self.cleaned_data
        if (cleaned_data.get('country') not in ["United States", "Canada"]
                and not self.instance.pk):
            region = cleaned_data.get('region')
            if region:
                cleaned_data['state'] = region
            else:
                raise ValidationError('State or region is required.')

        if not self.company:
            company_name = self.cleaned_data.get('company_name')
            msg = clean_company_name(company_name, None)
            if msg:
                self._errors['company_name'] = self.error_class([msg])
                raise ValidationError(msg)

        exp_date = self.cleaned_data.get('exp_date')
        try:
            month = exp_date.month
            year = exp_date.year
        except AttributeError:
            msg = 'Invalid CC Expiration Date.'
            self._errors['exp_Date'] = self.error_class([msg])
            raise ValidationError(msg)
        address = "%s %s" % (self.cleaned_data.get('address_line_one', ''),
                             self.cleaned_data.get('address_line_two', ''))
        try:
            card = get_card(self.cleaned_data.get('card_number'),
                            self.cleaned_data.get('cvv'), month, year,
                            self.cleaned_data.get('first_name'),
                            self.cleaned_data.get('last_name'),
                            address, self.cleaned_data.get('city'),
                            self.cleaned_data.get('state'),
                            self.cleaned_data.get('zip_code'),
                            self.product.owner.companyprofile.authorize_net_login,
                            self.product.owner.companyprofile.authorize_net_transaction_key,
                            self.cleaned_data.get('country'))
        except AuthorizeInvalidError, e:
            self._errors['card_number'] = self.error_class([e.message])
            raise ValidationError(e.message)

        try:
            self.transaction = authorize_card(self.product.cost, card)
        except AuthorizeResponseError, e:
            msg = e.full_response['response_reason_text']
            self._errors['card_number'] = self.error_class([msg])
            raise ValidationError(msg)

        return self.cleaned_data

    def save(self, commit=True):
        if not self.company:
            make_company_from_form(self)

        invoice = Invoice.objects.create(
            address_line_one=self.cleaned_data.get('address_line_one'),
            address_line_two=self.cleaned_data.get('address_line_two'),
            card_exp_date=self.cleaned_data.get('exp_date'),
            card_last_four=self.cleaned_data.get('card_number')[-4:],
            city=self.cleaned_data.get('city'),
            country=self.cleaned_data.get('country'),
            first_name=self.cleaned_data.get('first_name'),
            last_name=self.cleaned_data.get('last_name'),
            owner=self.product.owner,
            state=self.cleaned_data.get('state'),
            transaction_type=Invoice.AUTHORIZE_NET,
            transaction=self.transaction.uid,
            zipcode=self.cleaned_data.get('zipcode'),
        )
        self.instance.invoice = invoice
        self.instance.product = self.product
        self.instance.owner = self.company

        super(PurchasedProductForm, self).save(commit)
        try:
            settled_transaction = settle_transaction(self.transaction)
            invoice.transaction = settled_transaction.uid
            self.instance.paid = True
            self.instance.save()
            invoice.save()
        except AuthorizeResponseError:
            pass
        else:
            invoice.send_invoice_email(
                other_recipients=[self.request.user.email])


class OfflinePurchaseForm(RequestForm):
    """
    This is barely a traditional ModelForm (and would probably be better off
    as just a regular form), but is going to be treated as a ModelForm
    so the same form can override the OfflinePurchase admin
    as well.

    """
    class Meta:
        model = OfflinePurchase
        exclude = ('created_by', 'created_on', 'redeemed_by', 'redeemed_on',
                   'redemption_uid', 'products', 'invoice', 'owner', )

    class Media:
        css = {
            'all': ('postajob.159-9.css', )
        }
        js = ('postajob.160-13.js', )

    def __init__(self, *args, **kwargs):
        super(OfflinePurchaseForm, self).__init__(*args, **kwargs)

        self.products = Product.objects.filter(owner=self.company)

        # Create the Product list.
        for product in self.products:
            label = '{name}'.format(name=product.name)
            self.fields[str(product.pk)] = IntegerField(label=label, initial=0,
                                                        min_value=0)

    def save(self, commit=True):
        self.instance.owner = self.company
        self.instance.created_by = CompanyUser.objects.get(
            company=self.company, user=self.request.user)

        instance = super(OfflinePurchaseForm, self).save(commit)

        for product in self.products:
            product_quantity = self.cleaned_data.get(str(product.pk))
            if product_quantity:
                OfflineProduct.objects.create(
                    product=product, offline_purchase=instance,
                    product_quantity=product_quantity
                )
        instance.save()

        company = get_object_or_none(
            Company, pk=self.cleaned_data.get('purchasing_company'))
        if company:
            instance.redeemed_on = date.today()
            instance.create_purchased_products(company)
            instance.save()

        return instance


class OfflinePurchaseRedemptionForm(RequestForm):
    """
    This is barely a traditional ModelForm (and would probably be better off
    as just a regular form), but is going to be treated as a ModelForm
    so the same form can override the OfflinePurchase admin
    as well.

    """
    class Meta:
        model = OfflinePurchase
        exclude = ('created_by', 'created_on', 'redeemed_by', 'redeemed_on',
                   'redemption_uid', 'products', 'invoice', 'owner', )

    redemption_id = CharField(label='Redemption ID')

    def __init__(self, *args, **kwargs):
        super(OfflinePurchaseRedemptionForm, self).__init__(*args, **kwargs)
        if not self.company:
            self.fields['company_name'] = CharField(label='Company Name')
            self.fields['address_line_one'] = CharField(label='Address Line One')
            self.fields['address_line_two'] = CharField(label='Address Line Two',
                                                        required=False)
            self.fields['city'] = CharField(label='City')
            self.fields['state'] = CharField(label='State')
            self.fields['country'] = CharField(label='Country')
            self.fields['zipcode'] = CharField(label='Zip Code')

    def clean_company_name(self):
        company_name = self.cleaned_data.get('company_name')
        msg = clean_company_name(company_name, None)
        if msg:
            self._errors['company_name'] = self.error_class([msg])
            raise ValidationError(msg)
        return company_name

    def clean_redemption_id(self):
        redemption_id = self.cleaned_data.get('redemption_id')
        offline_purchase = get_object_or_none(OfflinePurchase,
                                              redemption_uid=redemption_id,
                                              redeemed_by=None,
                                              redeemed_on=None)
        if not offline_purchase:
            raise ValidationError('The redemption id you entered is invalid.')

        return offline_purchase

    def save(self, commit=True):
        if not self.company:
            make_company_from_form(self)
        self.instance = self.cleaned_data.get('redemption_id')

        invoice_kwargs = {
            'first_name': self.request.user.first_name,
            'last_name': self.request.user.last_name,
            'owner': self.company,
            'transaction_type': Invoice.OFFLINE_PURCHASE,
            'transaction': self.instance.redemption_uid,
        }
        if hasattr(self.company, 'companyprofile'):
            profile = self.company.companyprofile
            invoice_kwargs['address_line_one'] = profile.address_line_one
            invoice_kwargs['address_line_two'] = profile.address_line_two
            invoice_kwargs['city'] = profile.city
            invoice_kwargs['state'] = profile.state
            invoice_kwargs['country'] = profile.country
            invoice_kwargs['zipcode'] = profile.zipcode
        invoice = Invoice.objects.create(**invoice_kwargs)

        self.instance.invoice = invoice
        self.instance.redeemed_by = CompanyUser.objects.get(
            user=self.request.user, company=self.company)
        self.instance.redeemed_on = date.today()
        instance = super(OfflinePurchaseRedemptionForm, self).save(commit)
        instance.create_purchased_products(self.company)
        return instance


class CompanyProfileForm(RequestForm):
    state = NoValidationChoiceField(choices=JobLocation.state_choices,
                                    widget=SelectWithOptionClasses(),
                                    required=False)
    region = CharField(max_length=255, required=False)
    country = ChoiceField(choices=JobLocation.country_choices,
                          initial='United States',
                          required=False)

    class Meta:
        model = CompanyProfile
        exclude = ('company', 'blocked_users', 'customer_of')

    class Media:
        css = {
            'all': ('postajob.159-9.css', )
        }
        js = ('postajob.160-13.js', )

    def __init__(self, *args, **kwargs):
        super(CompanyProfileForm, self).__init__(*args, **kwargs)
        if not self.instance.company.product_access:
            self.fields.pop('authorize_net_login', None)
            self.fields.pop('authorize_net_transaction_key', None)

        self.fields['company_name'] = CharField(
            initial=self.instance.company.name, label='Company Name')
        self.fields.keyOrder.insert(0, self.fields.keyOrder.pop())

        # companies pulled from content acquisition should be read-only
        if not self.instance.company.user_created:
            self.fields['company_name'].widget.attrs['readonly'] = True
            self.fields['description'].widget.attrs['readonly'] = True

    def clean(self):
        cleaned_data = self.cleaned_data
        if (cleaned_data.get('country') not in ["United States", "Canada"]
                and not self.instance.pk):
            region = cleaned_data.get('region')
            if region:
                cleaned_data['state'] = region

        if self.instance.company.user_created:
            company_name = cleaned_data.get('company_name')
            msg = clean_company_name(company_name, self.instance.company)
            if msg:
                self._errors['company_name'] = self.error_class([msg])
                raise ValidationError(msg)
        return cleaned_data

    def save(self, commit=True):
        self.instance.company = self.company
        if self.instance.company.user_created:
            company_name = self.cleaned_data.get('company_name')
            self.instance.company.name = company_name
            self.instance.company.save()

        super(CompanyProfileForm, self).save(commit)


def clean_company_name(company_name, current_company):
    company_query = Company.objects.filter(name=company_name)
    if current_company:
        company_query = company_query.exclude(pk=current_company.pk)
    if company_query.exists():
        return "A company with that name already exists."
    return None
