from django.conf.urls import *

from postajob import models, views
from postajob.decorators import (message_when_site_misconfigured,
                                 error_when_site_misconfigured)
from universal.decorators import company_in_sitepackages 


urlpatterns = patterns(
    '',

    # Views for job and admin
    url(r'^order/',
        views.order_postajob,
        name="order_postajob"),
    url(r'^companyuser/',
        views.is_company_user,
        name="is_company_user"),
    url(r'list/$',
        error_when_site_misconfigured(feature='Job Listing', redirect=False)(
            views.product_listing),
        name='product_listing'),

    # Posted job management
    url(r'^all/$',
        views.jobs_overview,
        name='jobs_overview'),

    # Purchased job management
    url(r'^purchased-jobs/$',
        error_when_site_misconfigured(feature='Purchased Job Management')(
            views.purchasedproducts_overview),
        name='purchasedproducts_overview'),
    url(r'purchased-jobs/product/(?P<purchased_product>\d+)/view/(?P<pk>\d+)$',
        error_when_site_misconfigured(feature='Purchased Job Management')(
            views.view_job),
        {'admin': False},
        name='view_job'),
    url(r'^purchased-jobs/product/(?P<purchased_product>\d+)/',
        error_when_site_misconfigured(feature='Purchased Job Management')(
            views.purchasedjobs_overview),
        {'admin': False},
        name='purchasedjobs_overview'),

    # Purchased microsite management
    url(r'^admin/$',
        company_in_sitepackages(message_when_site_misconfigured(
            feature='Microsite Admin is')(
                views.purchasedmicrosite_admin_overview)),
        name='purchasedmicrosite_admin_overview'),

    # Invoices
    url(r'^admin/invoice/(?P<pk>\d+)/$',
        company_in_sitepackages(message_when_site_misconfigured(
            feature='Invoices are')(
                views.resend_invoice)),
        name='resend_invoice'),

    # Requests
    url(r'^admin/request/$',
        company_in_sitepackages(message_when_site_misconfigured(
            feature='Requests are')(
                views.admin_request)),
        name='request'),
    url(r'^admin/request/view/(?P<pk>\d+)/$',
        company_in_sitepackages(message_when_site_misconfigured(
            feature='Requests are')(
                views.view_request)),
        name='view_request'),
    url(r'^admin/request/approve/(?P<pk>\d+)/$',
        company_in_sitepackages(message_when_site_misconfigured(
            feature='Requests are')(
                views.process_admin_request)),
        {'approve': True,
         'block': False},
        name='approve_admin_request'),
    url(r'^admin/request/deny/(?P<pk>\d+)/$',
        company_in_sitepackages(message_when_site_misconfigured(
            feature='Requests are')(
                views.process_admin_request)),
        {'approve': False,
         'block': False},
        name='deny_admin_request'),
    url(r'^admin/request/block/(?P<pk>\d+)/$',
        company_in_sitepackages(message_when_site_misconfigured(
            feature='Requests are')(
                views.process_admin_request)),
        {'approve': False,
         'block': True},
        name='block_admin_request'),

    # Job
    url(r'^job/add/',
        views.JobFormView.as_view(),
        name='job_add'),
    url(r'^job/delete/(?P<pk>\d+)/',
        views.JobFormView.as_view(),
        name='job_delete'),
    url(r'^job/update/(?P<pk>\d+)/',
        views.JobFormView.as_view(),
        name='job_update'),

    # PurchasedJob
    url(r'^job/purchase/add/(?P<product>\d+)/',
        views.PurchasedJobFormView.as_view(),
        name='purchasedjob_add'),
    url(r'^job/purchase/update/(?P<pk>\d+)/',
        views.PurchasedJobFormView.as_view(),
        name='purchasedjob_update'),
    url(r'^job/purchase/delete/(?P<pk>\d+)/',
        views.PurchasedJobFormView.as_view(),
        name='purchasedjob_delete'),

    # Product management
    url(r'^admin/product/$',
        company_in_sitepackages(message_when_site_misconfigured(
            feature='Product Management is')(
                views.admin_products)),
        name='product'),
    url(r'^admin/product/add/',
        company_in_sitepackages(message_when_site_misconfigured(
            feature='Product Management is')(
                views.ProductFormView.as_view())),
        name='product_add'),
    url(r'^admin/product/delete/(?P<pk>\d+)/',
        company_in_sitepackages(message_when_site_misconfigured(
            feature='Product Management is')(
                views.ProductFormView.as_view())),
        name='product_delete'),
    url(r'^admin/product/update/(?P<pk>\d+)/',
        company_in_sitepackages(message_when_site_misconfigured(
            feature='Product Management is')(
                views.ProductFormView.as_view())),
        name='product_update'),

    # ProductGrouping
    url(r'^admin/product/group/$',
        company_in_sitepackages(message_when_site_misconfigured(
            feature='Product Groupings are')(
                views.admin_groupings)),
        name='productgrouping'),
    url(r'^admin/product/group/add/',
        company_in_sitepackages(message_when_site_misconfigured(
            feature='Product Groupings are')(
                views.ProductGroupingFormView.as_view())),
        name='productgrouping_add'),
    url(r'^admin/product/group/delete/(?P<pk>\d+)/',
        company_in_sitepackages(message_when_site_misconfigured(
            feature='Product Groupings are')(
                views.ProductGroupingFormView.as_view())),
        name='productgrouping_delete'),
    url(r'^admin/product/group/update/(?P<pk>\d+)/',
        company_in_sitepackages(message_when_site_misconfigured(
            feature='Product Groupings are')(
                views.ProductGroupingFormView.as_view())),
        name='productgrouping_update'),

    # Offline Purchases
    url(r'^admin/purchase/offline/$',
        company_in_sitepackages(message_when_site_misconfigured(
            feature='Offline Purchases are')(
                views.admin_offlinepurchase)),
        name='offlinepurchase'),
    url(r'^admin/purchase/offline/add/',
        company_in_sitepackages(message_when_site_misconfigured(
            feature='Offline Purchases are')(
                views.OfflinePurchaseFormView.as_view())),
        name='offlinepurchase_add'),
    url(r'^admin/purchase/offline/delete/(?P<pk>\d+)/',
        company_in_sitepackages(message_when_site_misconfigured(
            feature='Offline Purchases are')(
                views.OfflinePurchaseFormView.as_view())),
        name='offlinepurchase_delete'),
    url(r'^admin/purchase/offline/update/(?P<pk>\d+)/',
        company_in_sitepackages(message_when_site_misconfigured(
            feature='Offline Purchases are')(
                views.OfflinePurchaseFormView.as_view())),
        name='offlinepurchase_update'),

    url(r'^purchase/redeem/$',
        error_when_site_misconfigured(feature='Purchase Redemption')(
            views.OfflinePurchaseRedemptionFormView.as_view()),
        name='offlinepurchase_redeem'),
    url(r'^admin/purchase/offline/success/(?P<pk>\d+)/$',
        error_when_site_misconfigured(feature='Purchase Redemption')(
            company_in_sitepackages(views.view_request)),
        {'model': models.OfflinePurchase},
        name='offline_purchase_success'),

    # PurchasedProduct
    url(r'^product/purchase/add/(?P<product>\d+)/',
        views.PurchasedProductFormView.as_view(),
        name='purchasedproduct_add'),
    url(r'^product/purchase/delete/(?P<pk>\d+)/',
        views.PurchasedProductFormView.as_view(),
        name='purchasedproduct_delete'),
    url(r'^product/purchase/update/(?P<pk>\d+)/',
        views.PurchasedProductFormView.as_view(),
        name='purchasedproduct_update'),

    url(r'^admin/purchased/product$',
        company_in_sitepackages(message_when_site_misconfigured(
            feature='Purchased Products are')(
                views.admin_purchasedproduct)),
        name='purchasedproduct'),
    url(r'^admin/purchased/product/(?P<purchased_product>\d+)/view/(?P<pk>\d+)$',
        company_in_sitepackages(message_when_site_misconfigured(
            feature='Purchased Products are')(
                views.view_job)),
        {'admin': True},
        name="admin_view_job"),
    url(r'^admin/purchased/product/(?P<purchased_product>\d+)/view-invoice',
        company_in_sitepackages(message_when_site_misconfigured(
            feature='Purchased Products are')(
                views.view_invoice)),
        name="admin_view_invoice"),
    url(r'^admin/purchased/product/(?P<purchased_product>\d+)/',
        company_in_sitepackages(message_when_site_misconfigured(
            feature='Purchased Products are')(
        views.purchasedjobs_overview)),
        {'admin': True},
        name="purchasedjobs"),

    # CompanyProfile
    url(r'^admin/profile/',
        views.CompanyProfileFormView.as_view(),
        name='companyprofile_add'),
    url(r'^admin/profile/delete/(?P<pk>\d+)/',
        views.CompanyProfileFormView.as_view(),
        name='companyprofile_delete'),
    url(r'^admin/profile/update/(?P<pk>\d+)/',
        views.CompanyProfileFormView.as_view(),
        name='companyprofile_update'),

    # User management
    url(r'^admin/blocked-users/$',
        company_in_sitepackages(views.blocked_user_management),
        name='blocked_user_management'),
    url(r'^admin/blocked-users/unblock/(?P<pk>\d+)/$',
        company_in_sitepackages(views.unblock_user),
        name='unblock_user'),

    url(r'^sites/$',
        views.SitePackageFilter.as_view(),
        name='site_fsm'),
)
