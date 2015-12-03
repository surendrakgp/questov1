import imp
import os
import sys

from selenium import webdriver

from django.conf import settings
from django.core.management.base import NoArgsCommand
from django.core.urlresolvers import reverse
from django.utils import unittest
from django.utils.unittest.case import TestCase, skipUnless
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait

from myjobs.models import User
from postajob.models import SitePackage, Job, Product, ProductGrouping, \
    ProductOrder, PurchasedJob
from seo.models import Company, CompanyUser, SeoSite, Configuration
from seo.tests.setup import patch_settings


class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        suite = unittest.TestLoader().loadTestsFromTestCase(JobPostingTests)
        unittest.TextTestRunner().run(suite)


def make_user(address, admin=False):
    """
    Creates a normal user or superuser using the provided address

    Inputs:
    :address: User's email address
    :admin: Boolean, is this user an admin

    Outputs:
    :user: Generated user
    """
    if admin:
        method = 'create_superuser'
    else:
        method = 'create_user'
    user = getattr(User.objects, method)(email=address, send_email=False)
    password = User.objects.make_random_password()
    if isinstance(user, tuple):
        # User.objects.create_user returns (User, created).
        user = user[0]
    # It is less of a headache to set the password now and toggle
    # password_change than it is to pass password into the user creation call,
    # determine if the password was set or if we short-circuited, and then act
    # on that determination.
    user.set_password(password)
    user.password_change = False
    user.is_active = True
    user.is_verified = True
    user.save()
    user.raw_password = password
    return user


# Django's tests work on test databases created specifically for tests.
# Selenium tests work on databases that already exist. While these could be run
# at the same time, it feels more correct to have them remain separate.
@skipUnless('test_posting' in sys.argv, 'Selenium tests are incompatible '
            'with Django tests')
class JobPostingTests(TestCase):
    OVERRIDES = {}
    CREATION_ORDER = []
    test_url = 'localhost'
    test_port = ''
    domain_override = None

    @classmethod
    def set_domain_override(cls, domain):
        cls.domain_override = domain

    @classmethod
    def setup_objects(cls):
        """
        This is a big ugly method that sets up objects needed for postajob
        testing.

        Since we're modifying an active database, we need to follow an old
        dumpster diving rule and leave it cleaner than we found it. As such,
        every addition is being added to a list so that they can be reversed.
        This is a little verbose - these additions are being appended to the
        list immediately so that we can adequately revert if something fails.
        """
        #Users:
        # These are all superusers at the moment as the admin page is being
        # used to log in. It isn't guaranteed that a given microsite has a
        # login page set up.

        # admin: Main user for testing
        cls.admin = make_user(address='paj_admin@my.jobs', admin=True)
        cls.CREATION_ORDER.append(cls.admin)
        # admin_2: Secondary company user for a different company
        cls.admin_2 = make_user(address='paj_admin_2@my.jobs', admin=True)
        cls.CREATION_ORDER.append(cls.admin_2)
        # user: User unaffiliated to any company
        cls.user = make_user(address='paj_user@my.jobs', admin=True)
        cls.CREATION_ORDER.append(cls.user)

        # Companies:
        cls.admin_company = Company.objects.create(
            name='Postajob Selenium Company',
            company_slug='postajob-selenium-company',
            member=True, product_access=True, posting_access=True)
        cls.CREATION_ORDER.append(cls.admin_company)
        cls.admin_company_2 = Company.objects.create(
            name='Postajob Selenium Company 2',
            company_slug='postajob-selenium-company-2',
            member=True, product_access=True, posting_access=True)
        cls.CREATION_ORDER.append(cls.admin_company_2)

        # Company Users:
        cls.admin_company_user = CompanyUser.objects.create(
            company=cls.admin_company, user=cls.admin)
        cls.CREATION_ORDER.append(cls.admin_company_user)
        cls.admin_company_user_2 = CompanyUser.objects.create(
            company=cls.admin_company_2, user=cls.admin_2)
        cls.CREATION_ORDER.append(cls.admin_company_user_2)

        # Seo Sites:
        cls.seo_site = SeoSite.objects.create(
            domain='selenium.jobs', name='Selenium Jobs',
            canonical_company=cls.admin_company)
        cls.CREATION_ORDER.append(cls.seo_site)
        cls.seo_site_2 = SeoSite.objects.create(
            domain='selenium2.jobs', name='Selenium Jobs',
            canonical_company=cls.admin_company_2)
        cls.CREATION_ORDER.append(cls.seo_site_2)

        # Site Packages:
        cls.site_package = SitePackage.objects.create(
            owner=cls.admin_company, name='Selenium Test Package 1')
        cls.site_package.sites.add(cls.seo_site)
        cls.CREATION_ORDER.append(cls.site_package)
        cls.site_package_2 = SitePackage.objects.create(
            owner=cls.admin_company_2, name='Selenium Test Package 2')
        cls.site_package_2.sites.add(cls.seo_site_2)
        cls.CREATION_ORDER.append(cls.site_package_2)

        # Configurations:
        cls.configuration = Configuration.objects.create()
        cls.CREATION_ORDER.append(cls.configuration)
        cls.seo_site.configurations.add(cls.configuration)

        # Products:
        cls.product = Product.objects.create(
            package=cls.site_package, owner=cls.admin_company,
            name='Selenium Test Product', cost=0)
        cls.CREATION_ORDER.append(cls.product)

        # Product Groupings:
        cls.product_grouping = ProductGrouping.objects.create(
            owner=cls.admin_company)
        cls.CREATION_ORDER.append(cls.product_grouping)

        # Product Orders:
        cls.product_order = ProductOrder.objects.create(
            product=cls.product, group=cls.product_grouping)
        cls.CREATION_ORDER.append(cls.product_order)

    @classmethod
    def remove_objects(cls):
        """
        Delete objects created in setup_objects.
        """
        for obj in cls.CREATION_ORDER[::-1]:
            obj.delete()

    @classmethod
    def login(cls, user):
        """
        Logs the provided user in using our web driver.

        Inputs:
        :user: User being logged in
        """
        cls.get('/admin/')
        cls.browser.find_element_by_id('id_username').send_keys(user.email)
        cls.browser.find_element_by_id('id_password').send_keys(
            user.raw_password)
        cls.browser.find_element_by_xpath('//input[@value="Log in"]').click()

    @classmethod
    def logout(cls):
        """
        Logs out whoever is logged in, if anyone.
        """
        cls.get('/admin/')
        try:
            element = cls.browser.find_element_by_xpath(
                '//div[@id="user-tools"]//a[2]')
        except NoSuchElementException:
            pass
        else:
            element.click()

    @classmethod
    def get(cls, path='/', domain=None):
        """
        Shortcut to cls.browser.get(...) with additional options.

        Inputs:
        :path: Path being hit
        :domain: String used for domain overrides
        """
        if path.startswith('http'):
            requested_url = path
        else:
            requested_url = 'http://{domain}{port}{path}'.format(
                domain=cls.test_url, port=cls.test_port, path=path)
        domain = domain or cls.domain_override
        if domain:
            requested_url += '?domain=%s' % domain
        cls.browser.get(requested_url)
        cls.wait_on_load()

    @classmethod
    def wait_on_load(cls):
        """
        Waits for a page to be loaded before doing the next step in a process.
        """
        WebDriverWait(cls.browser, 3).until(
            expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, 'html')))

    def make_job(self, for_admin=False):
        for field, value in self.job.items():
            # Find the correct inputs for the four items we listed
            # previously and submit their values.
            self.browser.find_element_by_id(field).send_keys(value)

        # Adding a location requires one click to finalize.
        self.browser.find_element_by_id('add-location').click()
        if for_admin:
            # Choosing the site that this job should appear on is relatively
            # easy given the low number of sites being tested. If we have more
            # sites than the default FSM cutoff, something else will be needed.
            self.browser.find_element_by_xpath(
                '//option[@value={site_pk}]'.format(
                    site_pk=self.seo_site.pk)).click()
            self.browser.find_element_by_id(
                'id_site_packages_add_link').click()

        self.browser.find_element_by_id('profile-save').click()
        self.wait_on_load()

    @classmethod
    def setUpClass(cls):
        """
        Sets up the test environment, overriding settings and modifying the db.
        """
        environment = os.environ.get('SETTINGS', '').lower()
        if environment == 'qc':
            print 'Running test_posting with QC settings'
            cls.test_url = 'qc.www.my.jobs'
            qc = imp.load_source('settings.myjobs_qc',
                                 'deploy/settings.myjobs_qc.py')
            cls.OVERRIDES = vars(qc)
        elif environment == 'staging':
            print 'Running test_posting with staging settings'
            cls.test_url = 'staging.www.my.jobs'
            staging = imp.load_source('settings.myjobs_staging',
                                      'deploy/settings.myjobs_staging.py')
            cls.OVERRIDES = vars(staging)
        else:
            production = imp.load_source('settings.myjobs_prod',
                                         'deploy/settings.myjobs_prod.py')
            assert (settings.DATABASES['default']['HOST'] !=
                    production.DATABASES['default']['HOST']), \
                'Running test_posting with production settings is unsupported'
            print 'Running test_posting with settings.py'
            # Assuming local; I have to pick a port and runserver defaults to
            # 8000, so...
            cls.test_port = ':8000'
        cls.browser = webdriver.PhantomJS()
        super(JobPostingTests, cls).setUpClass()

        with patch_settings(**cls.OVERRIDES):
            try:
                cls.setup_objects()
            except:
                # If anything happens during setup (someone cancels the
                # process, db issues, whatever), we need to roll back. Delete
                # everything we created and reraise the exception.
                cls.remove_objects()
                raise

    @classmethod
    def tearDownClass(cls):
        """
        Deletes all objects created during setup.
        """
        cls.browser.quit()
        with patch_settings(**cls.OVERRIDES):
            cls.remove_objects()
        super(JobPostingTests, cls).tearDownClass()

    def setUp(self):
        super(JobPostingTests, self).setUp()
        # TEST_OBJECTS is like CREATION_ORDER but on a test-by-test basis
        # rather than for the entire test case.
        self.TEST_OBJECTS = []

        # There are only four required text boxes we need to fill out to
        # create a job from a job form.
        self.job = {
            'id_title': 'Job Title',
            'id_description': 'Job Description',
            'id_form-__prefix__-city': 'City',
            'id_apply_link': 'https://www.google.com',
        }

        self.set_domain_override(self.seo_site.domain)

    def tearDown(self):
        self.logout()
        with patch_settings(**self.OVERRIDES):
            for obj in self.TEST_OBJECTS[::-1]:
                obj.delete()
        super(JobPostingTests, self).tearDown()

    def test_show_job_admin(self):
        """
        Ensures that the main postajob admin is functional.

        A company user for the site owner should be able to see all options.
        A company user for a third party or a non-company-user should not.

        PD-1463 Task
        - jobs admin display
        """
        with patch_settings(**self.OVERRIDES):
            for user, accessible in [(self.admin, True), (self.admin_2, False),
                                     (self.user, False)]:
                self.login(user)
                self.get(reverse('purchasedmicrosite_admin_overview'))
                for selector, expected in [
                        ('product-listing', 'Product Listing'),
                        ('our-postings', 'Posted Jobs'),
                        ('posting-admin', 'Partner Microsite')]:
                    try:
                        element = self.browser.find_element_by_id(selector)
                    except NoSuchElementException:
                        # If the user is not a company user for the owner, this
                        # is expected; if not, we should reraise and fail.
                        if accessible:
                            raise
                    else:
                        self.assertEqual(element.text, expected)
                self.logout()

    def test_post_job_as_owner(self):
        """
        Ensures that a company user of the site owner can post jobs for free
        and verify that they have been posted.

        PD-1463 Task
        - posting a job and verifying it is live (as site owner)
        - listing jobs
        """
        with patch_settings(**self.OVERRIDES):
            num_jobs = Job.objects.count()
            self.login(self.admin)
            self.get(reverse('job_add'))

            self.make_job(for_admin=True)

            self.assertEqual(Job.objects.count(), num_jobs + 1)

            # If the previous bit was successfully added to solr, the following
            # page will have a job matching its description.
            self.get(reverse('all_jobs'))
            # We could easily .click() this but that would not properly append
            # the domain override.
            job_link = self.browser.find_element_by_link_text(
                self.job['id_title']).get_attribute('href')
            job = Job.objects.get(title=self.job['id_title'],
                                  description=self.job['id_description'])
            location = job.locations.get()
            self.TEST_OBJECTS.extend([location, job])
            self.assertTrue(location.guid in job_link)
            self.get(job_link)
            element = self.browser.find_element_by_id(
                'direct_jobDescriptionText')
            self.assertEqual(element.text, job.description)

            self.logout()

            # Trying this with a normal user fails.
            self.login(self.user)
            self.get(reverse('job_add'))
            with self.assertRaises(NoSuchElementException):
                self.browser.find_element_by_id(
                    'id_site_packages_add_link')

            self.logout()

            # Trying this instead with another company user is successful.
            # Due to the way one of the decorators works, this grabs the user's
            # company. Posting will not post to the current site, but to a site
            # determined by that company. Fixing this is outside the scope of
            # writing Selenium tests.
            self.login(self.admin_2)
            self.get(reverse('job_add'))
            with self.assertRaises(NoSuchElementException):
                self.browser.find_element_by_xpath(
                    '//option[@value={site_pk}]'.format(
                        site_pk=self.seo_site.pk))
            self.browser.find_element_by_xpath(
                '//option[@value={site_pk}]'.format(
                    site_pk=self.seo_site_2.pk))

    def test_purchase_a_job(self):
        """
        Test that an unaffiliated user can purchase a product, creating a new
        company in the process.

        PD-1463 Task
        - purchasing a job, approving it, and verifying it is live
            (as site customer)
        - listing jobs
        """
        self.assertEqual(self.user.company_set.count(), 0)
        self.login(self.user)
        self.get(reverse('product_listing'))

        purchase_link = self.browser.find_element_by_link_text(
            self.product.name).get_attribute('href')
        self.get(purchase_link)
        company_info = {
            'id_company_name': 'Postajob Selenium Company 3',
            'id_address_line_one': '1234 Road',
            'id_city': 'Cityville',
            'id_zipcode': '12345'
        }
        for field, value in company_info.items():
            self.browser.find_element_by_id(field).send_keys(value)
        self.browser.find_element_by_id('profile-save').click()
        self.wait_on_load()
        self.assertEqual(self.user.company_set.count(), 1)
        created_company = self.user.company_set.get()
        self.TEST_OBJECTS.append(created_company)

        # We redirected to a new page without maintaining the domain override.
        self.get(self.browser.current_url)

        # This retrieves the purchased product detail page.
        self.get(self.browser.find_element_by_link_text(
            'View').get_attribute('href'))

        num_jobs = PurchasedJob.objects.count()

        # This retrieves the actual job form page.
        self.get(self.browser.find_element_by_link_text(
            'Post New Job').get_attribute('href'))

        self.job['id_title'] = created_company.name + ' Job'
        self.make_job()

        self.assertEqual(PurchasedJob.objects.count(), num_jobs + 1)

        # This should have generated a request object and a purchased product
        # object
        self.TEST_OBJECTS.append(self.admin_company.request_set.get())
        self.TEST_OBJECTS.append(created_company.purchasedproduct_set.get())

        self.logout()
        self.login(self.admin)

        self.get(reverse('purchasedmicrosite_admin_overview'))

        requests_link = self.browser.find_element_by_link_text(
            'Manage Requests').get_attribute('href')
        self.get(requests_link)

        view_request = self.browser.find_element_by_link_text(
            'View').get_attribute('href')
        self.get(view_request)

        request = self.admin_company.request_set.get()

        # The approve button submits a form whose action does not include
        # a domain override. Add one. :(
        request_approve = reverse('approve_admin_request',
                                  kwargs={'pk': request.pk})
        self.browser.execute_script(
            '$("form[action=\'%s\']").attr("action", "%s");' % (
                request_approve,
                request_approve + '?domain=' + self.seo_site.domain))

        # Click the approve button
        self.browser.find_element_by_xpath(
            '//button[contains(text(), "Approve This Job")]').click()
        self.wait_on_load()

        # Once we've finished processing the approval, check for the job on
        # our list of jobs and ensure its data is correct.
        self.get(reverse('all_jobs'))

        job = PurchasedJob.objects.get(title=self.job['id_title'],
                                       description=self.job['id_description'])
        location = job.locations.get()
        job_link = self.browser.find_element_by_link_text(
            self.job['id_title']).get_attribute('href')
        self.TEST_OBJECTS.extend([location, job])
        self.assertTrue(location.guid in job_link)
        self.get(job_link)
        element = self.browser.find_element_by_id(
            'direct_jobDescriptionText')
        self.assertEqual(element.text, job.description)
