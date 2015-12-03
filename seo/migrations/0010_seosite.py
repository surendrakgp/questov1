# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
        ('sites', '0001_initial'),
        ('postajob', '__first__'),
        ('seo', '0009_auto_20151019_1407'),
    ]

    operations = [
        migrations.CreateModel(
            name='SeoSite',
            fields=[
                ('site_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='sites.Site')),
                ('site_title', models.CharField(default=b'', max_length=200, verbose_name=b'Site Title', blank=True)),
                ('site_heading', models.CharField(default=b'', max_length=200, verbose_name=b'Site Heading', blank=True)),
                ('site_description', models.CharField(default=b'', max_length=200, verbose_name=b'Site Description', blank=True)),
                ('postajob_filter_type', models.CharField(default=b'this site only', max_length=255, choices=[(b'this site only', b'this site only'), (b'sites associated with the company that owns this site', b'sites associated with the company that owns this site'), (b'network sites and sites associated with the company that owns this site', b'network sites and sites associated with the company that owns this site'), (b'all sites', b'all sites'), (b'network sites only', b'network sites only'), (b'network sites and this site', b'network sites and this site')])),
                ('email_domain', models.CharField(default=b'my.jobs', max_length=255)),
                ('billboard_images', models.ManyToManyField(to='seo.BillboardImage', null=True, blank=True)),
                ('canonical_company', models.ForeignKey(related_name=b'canonical_company_for', on_delete=django.db.models.deletion.SET_NULL, blank=True, to='seo.Company', null=True)),
                ('featured_companies', models.ManyToManyField(to='seo.Company', null=True, blank=True)),
                ('group', models.ForeignKey(to='auth.Group', null=True)),
                ('site_package', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='postajob.SitePackage', null=True)),
                ('special_commitments', models.ManyToManyField(to='seo.SpecialCommitment', null=True, blank=True)),
            ],
            options={
                'verbose_name': 'Seo Site',
                'verbose_name_plural': 'Seo Sites',
            },
            bases=('sites.site',),
        ),
    ]
