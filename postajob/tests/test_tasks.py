import datetime

from myjobs.tests.setup import MyJobsBase
from mydashboard.tests.factories import CompanyFactory
from myjobs.tests.factories import UserFactory
from postajob.models import Job, JobLocation
from tasks import expire_jobs


class TaskTests(MyJobsBase):
    def setUp(self):
        super(TaskTests, self).setUp()
        self.company = CompanyFactory()
        self.user = UserFactory()
        self.job_data = {
            'title': 'title',
            'owner': self.company,
            'description': 'sadfljasdfljasdflasdfj',
            'apply_link': 'www.google.com',
            'created_by': self.user,
        }
        self.location_data = {
            'city': 'Indianapolis',
            'state': 'Indiana',
            'state_short': 'IN',
            'country': 'United States',
            'country_short': 'USA',
            'zipcode': '46268',
        }

    def test_expire_jobs(self):
        # Jobs with expiration dates in greater than or equal to today should
        # not expire.
        for x in range(0, 5):
            job = dict(self.job_data)
            job['date_new'] = datetime.datetime.now()
            job['date_updated'] = datetime.datetime.now()
            job['date_expired'] = datetime.date.today() + datetime.timedelta(days=5)
            instance = Job.objects.create(**job)
            location = JobLocation.objects.create(**self.location_data)
            instance.locations.add(location)
            instance.save()
        self.assertEqual(Job.objects.all().count(), 5)
        self.assertEqual(JobLocation.objects.all().count(), 5)
        self.assertEqual(self.ms_solr.search('*:*').hits, 5)

        for x in range(5, 10):
            job = dict(self.job_data)
            job['date_new'] = datetime.datetime.now()
            job['date_updated'] = datetime.datetime.now()
            job['date_expired'] = datetime.date.today()
            instance = Job.objects.create(**job)
            location = JobLocation.objects.create(**self.location_data)
            instance.locations.add(location)
            instance.save()
        self.assertEqual(Job.objects.all().count(), 10)
        self.assertEqual(JobLocation.objects.all().count(), 10)
        self.assertEqual(self.ms_solr.search('*:*').hits, 10)

        # Only jobs that expire before today should be expired in the next
        # expire_jobs() call.
        for x in range(10, 15):
            job = dict(self.job_data)
            job['date_new'] = datetime.datetime.now()
            job['date_updated'] = datetime.datetime.now()
            job['date_expired'] = datetime.date.today() + datetime.timedelta(days=-2)
            instance = Job.objects.create(**job)
            location = JobLocation.objects.create(**self.location_data)
            instance.locations.add(location)
            instance.save()
        self.assertEqual(Job.objects.all().count(), 15)
        self.assertEqual(self.ms_solr.search('*:*').hits, 15)

        expire_jobs()
        # The most recently made jobs should be expired and removed from solr.
        self.assertEqual(self.ms_solr.search('*:*').hits, 10)
        self.assertEqual(Job.objects.filter(is_expired=True).count(), 5)
        self.assertEqual(Job.objects.filter(is_expired=False).count(), 10)

    def test_expire_jobs_with_autorenew(self):
        # Unexpired jobs.
        for x in range(0, 5):
            job = dict(self.job_data)
            job['date_new'] = datetime.datetime.now()
            job['date_updated'] = datetime.datetime.now()
            job['date_expired'] = datetime.date.today() + datetime.timedelta(days=-5)
            instance = Job.objects.create(**job)
            location = JobLocation.objects.create(**self.location_data)
            instance.locations.add(location)
            instance.save()
        self.assertEqual(Job.objects.all().count(), 5)
        self.assertEqual(self.ms_solr.search('*:*').hits, 5)

        # Jobs that should expire.
        for x in range(5, 10):
            job = dict(self.job_data)
            job['date_new'] = datetime.datetime.now()
            job['date_updated'] = datetime.datetime.now()
            job['date_expired'] = datetime.date.today()
            instance = Job.objects.create(**job)
            location = JobLocation.objects.create(**self.location_data)
            instance.locations.add(location)
            instance.save()
        self.assertEqual(Job.objects.all().count(), 10)
        self.assertEqual(self.ms_solr.search('*:*').hits, 10)

        # Autorenew jobs.
        for x in range(10, 15):
            job = dict(self.job_data)
            job['date_new'] = datetime.datetime.now()
            job['date_updated'] = datetime.datetime.now()
            job['date_expired'] = datetime.date.today() + datetime.timedelta(days=-1)
            job['autorenew'] = True
            instance = Job.objects.create(**job)
            location = JobLocation.objects.create(**self.location_data)
            instance.locations.add(location)
            instance.save()
        self.assertEqual(Job.objects.all().count(), 15)
        self.assertEqual(self.ms_solr.search('*:*').hits, 15)

        expire_jobs()
        # 5 Jobs set to expire should have been removed from solr. The
        # un-expired jobs and autorenew jobs remain.
        self.assertEqual(self.ms_solr.search('*:*').hits, 10)

        autorenew_jobs = Job.objects.filter(autorenew=True, is_expired=False)
        new_expire_date = datetime.date.today() + datetime.timedelta(days=30)
        self.assertEqual(autorenew_jobs.count(), 5)

        # No jobs should've accidently been marked as autorenew that weren't
        # autorenew jobs.
        self.assertEqual(Job.objects.filter(is_expired=True).count(), 5)
        self.assertEqual(Job.objects.filter(is_expired=False,
                                            autorenew=False).count(), 5)

        # date_expired should've been moved up one month for expired autorenew
        # jobs.
        for job in autorenew_jobs:
            self.assertEqual(new_expire_date, job.date_expired)
