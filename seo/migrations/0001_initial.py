# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200, verbose_name=b'Name')),
                ('company_slug', models.SlugField(max_length=200, null=True, verbose_name=b'Company Slug', blank=True)),
                ('logo_url', models.URLField(help_text=b'The url for the 100x50 logo image for this company.', null=True, verbose_name=b'Logo URL', blank=True)),
                ('linkedin_id', models.CharField(help_text=b'The LinkedIn issued company ID for this company.', max_length=20, null=True, verbose_name=b'LinkedIn Company ID', blank=True)),
                ('og_img', models.URLField(help_text=b'The url for the large format logo for use when sharing jobs on LinkedIn, and other social platforms that support OpenGraph.', null=True, verbose_name=b'Open Graph Image URL', blank=True)),
                ('canonical_microsite', models.URLField(help_text=b'The primary directemployers microsite for this company.', null=True, verbose_name=b'Canonical Microsite URL', blank=True)),
                ('member', models.BooleanField(default=False, verbose_name=b'DirectEmployers Association Member')),
                ('digital_strategies_customer', models.BooleanField(default=False, verbose_name=b'Digital Strategies Customer')),
                ('enhanced', models.BooleanField(default=False, verbose_name=b'Enhanced')),
                ('prm_access', models.BooleanField(default=False)),
                ('product_access', models.BooleanField(default=False)),
                ('posting_access', models.BooleanField(default=False)),
                ('user_created', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['name'],
                'verbose_name': 'Company',
                'verbose_name_plural': 'Companies',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='company',
            unique_together=set([('name', 'user_created')]),
        ),
    ]
