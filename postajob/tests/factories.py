import datetime
import random

import factory

from seo.tests.factories import UserFactory, CompanyFactory, CompanyUserFactory


class JobLocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'postajob.JobLocation'

    city = 'Indianapolis'
    state = 'Indiana'
    state_short = 'IN'
    country = 'United States'
    country_short = 'USA'
    zipcode = '46268'


class JobFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'postajob.Job'

    title = 'title'
    owner = factory.SubFactory(CompanyFactory)
    reqid = '1'
    description = 'sadfljasdfljasdflasdfj'
    apply_link = 'www.google.com'
    date_new = datetime.datetime.now()
    date_updated = datetime.datetime.now()
    date_expired = datetime.date.today()
    created_by = factory.SubFactory(UserFactory)


class InvoiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'postajob.Invoice'

    address_line_one = '123 Street Rd'
    address_line_two = 'Suite 321'
    card_exp_date = datetime.date.today()
    card_last_four = '1234'
    city = 'Indianapolis'
    country = 'US'
    first_name = 'John'
    last_name = 'Smith'
    owner = factory.SubFactory(CompanyFactory)
    state = 'Indiana'
    transaction = '123456'
    transaction_type = 0
    zipcode = '46268'


class SitePackageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'postajob.SitePackage'

    owner = factory.SubFactory(CompanyFactory)
    name = 'Test SitePackage'


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'postajob.Product'

    package = factory.SubFactory(SitePackageFactory)
    owner = factory.SubFactory(CompanyFactory)
    name = 'Test Product'
    # prevent duplicate transactions by not using the same cost
    cost = str(random.randint(1, 5000))
    posting_window_length = 30
    max_job_length = 30
    num_jobs_allowed = 5
    description = 'Test product description.'


class PurchasedProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'postajob.PurchasedProduct'

    owner = factory.SubFactory(CompanyFactory)
    invoice = factory.SubFactory(
        InvoiceFactory, owner=factory.SelfAttribute('..owner'))
    product = factory.SubFactory(ProductFactory)
    purchase_date = datetime.datetime.now()


class PurchasedJobFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'postajob.PurchasedJob'

    title = 'title'
    owner = factory.SubFactory(CompanyFactory)
    reqid = '1'
    description = 'sadfljasdfljasdflasdfj'
    apply_link = 'www.google.com'
    date_new = datetime.datetime.now()
    date_updated = datetime.datetime.now()
    date_expired = datetime.date.today()
    created_by = factory.SubFactory(UserFactory)
    max_expired_date  = datetime.date.today() + datetime.timedelta(days=1)
    purchased_product = factory.SubFactory(PurchasedProductFactory)


class ProductGroupingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'postajob.ProductGrouping'

    display_order = 100
    display_title = 'Test ProductGrouping'
    explanation = 'Test explanation.'
    name = 'Test ProductGrouping'
    owner = factory.SubFactory(CompanyFactory)


class OfflinePurchaseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'postajob.OfflinePurchase'

    created_by = factory.SubFactory(CompanyUserFactory)
    invoice = factory.SubFactory(InvoiceFactory)
    owner = factory.SubFactory(CompanyFactory)
    redeemed_on = None
    redeemed_by = None


class OfflineProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'postajob.OfflineProduct'

    offline_purchase = factory.SubFactory(OfflinePurchaseFactory)
    product = factory.SubFactory(ProductFactory)
    product_quantity = 1
