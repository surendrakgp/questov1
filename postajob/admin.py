from django.contrib import admin

from postajob.forms import (JobForm, JobLocationForm, ProductForm, ProductGroupingForm,
                            PurchasedProductForm, PurchasedJobAdminForm,
                            SitePackageForm)
from postajob.models import (Job, JobLocation, Product, ProductGrouping, PurchasedProduct,
                             PurchasedJob, SitePackage)


class ModelAdminWithRequest(admin.ModelAdmin):
    def get_form(self, request, obj=None, **kwargs):
        """
        Override get_form() to allow the request information to be
        passed along to the JobForm.

        """
        ModelForm = super(ModelAdminWithRequest, self).get_form(request, obj,
                                                                **kwargs)

        class ModelFormMetaClass(ModelForm):
            def __new__(cls, *args, **kwargs):
                kwargs['request'] = request
                return ModelForm(*args, **kwargs)
        return ModelFormMetaClass


class JobLocationsInline(admin.TabularInline):
    model = Job.locations.through
    max_num = 1


class JobLocationAdmin(admin.ModelAdmin):
    form = JobLocationForm
    inlines = (JobLocationsInline, )


class JobAdmin(ModelAdminWithRequest):
    form = JobForm
    list_display = ('__unicode__', )
    search_fields = ('title', 'owner', 'site_packages__sites__domain', )

    fieldsets = (
        ('Job Information', {
            'fields': (('title', ), 'reqid', 'description',
                       ('date_expired', 'is_expired', 'autorenew', )),
        }),
        ('Application Instructions', {
            'fields': ('apply_type', 'apply_link', 'apply_email',
                       'apply_info', ),
        }),
        ('Site Information', {
            'fields': ('owner', 'post_to', 'site_packages', ),
        }),
    )

    def queryset(self, request):
        """
        Prevent users from seeing jobs that don't belong to their company
        in the admin.

        """
        jobs = super(JobAdmin, self).queryset(request)
        if not request.user.is_superuser:
            jobs = jobs.filter(owner__admins=request.user)
        return jobs


class PurchasedJobAdmin(ModelAdminWithRequest):
    form = PurchasedJobAdminForm
    list_display = ('__unicode__', )
    search_fields = ('title', 'owner', )

    fieldsets = (
        ('Job Information', {
            'fields': (('title', 'is_approved', ), 'reqid', 'description',
                       ('date_expired', 'is_expired', 'autorenew', )),
        }),
        ('Application Instructions', {
            'fields': ('apply_type', 'apply_link', 'apply_email',
                       'apply_info', ),
        }),
        ('Site Information', {
            'fields': ('owner', 'purchased_product', ),
        }),
    )

    def delete_model(self, request, obj):
        # Django admin bulk delete doesn't trigger a post_delete signal. This
        # ensures that the remove_from_solr() usually handled by a delete
        # signal is called in those cases.
        obj.remove_from_solr()
        obj.delete()

    def queryset(self, request):
        """
        Prevent users from seeing jobs that don't belong to their company
        in the admin.

        """
        jobs = super(PurchasedJobAdmin, self).queryset(request)
        if not request.user.is_superuser:
            jobs = jobs.filter(owner__admins=request.user)
        return jobs


class SitePackageAdmin(ModelAdminWithRequest):
    form = SitePackageForm
    list_display = ('id', 'name', )

    def queryset(self, request):
        """
        Make SeoSite-specific packages unavailable in the admin and prevent
        non-superusers from seeing packages.

        """
        packages = SitePackage.objects.user_available()
        if not request.user.is_superuser:
            packages = packages.filter(owner__admins=request.user)
        return packages


class ProductFormAdmin(ModelAdminWithRequest):
    actions = None
    form = ProductForm
    list_display = ('owner', 'package', )

    fieldsets = (
        ('', {
            'fields': ('name', 'owner', 'package')
        }),
        ('Package Details', {
            'fields': ('cost', 'posting_window_length',
                       'max_job_length', 'job_limit', 'num_jobs_allowed',
                       'requires_approval', )
        }),
    )

    def queryset(self, request):
        products = Product.objects.all()
        if not request.user.is_superuser:
            products = products.filter(owner__admins=request.user)
        return products

    def has_delete_permission(self, request, obj=None):
        return False


class ProductGroupingFormAdmin(ModelAdminWithRequest):
    form = ProductGroupingForm
    list_display = ('owner', 'display_order', 'name', )

    def queryset(self, request):
        groups = ProductGrouping.objects.all()
        if not request.user.is_superuser:
            groups = groups.filter(owner__admins=request.user)
        return groups


class PurchasedProductFormAdmin(ModelAdminWithRequest):
    actions = None
    form = PurchasedProductForm
    list_display = ('product', 'owner',
                    'paid', 'expiration_date', 'num_jobs_allowed',
                    'jobs_remaining', )

    def __init__(self, *args, **kwargs):
        super(PurchasedProductFormAdmin, self).__init__(*args, **kwargs)
        # Remove edit links, since you can't really edit a purchase.
        self.list_display_links = (None, )

    def has_add_permission(self, request):
        return False


admin.site.register(Job, JobAdmin)
admin.site.register(PurchasedJob, PurchasedJobAdmin)
admin.site.register(SitePackage, SitePackageAdmin)
admin.site.register(Product, ProductFormAdmin)
admin.site.register(ProductGrouping, ProductGroupingFormAdmin)
admin.site.register(PurchasedProduct, PurchasedProductFormAdmin)
admin.site.register(JobLocation, JobLocationAdmin)