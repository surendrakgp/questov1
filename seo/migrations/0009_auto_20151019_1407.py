# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
        ('seo', '0008_auto_20151019_1332'),
    ]

    operations = [
        migrations.CreateModel(
            name='BillboardHotspot',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(help_text=b'Max 50 characters', max_length=50, verbose_name=b'Title')),
                ('text', models.CharField(help_text=b'Max 140 characters.  Use HTML markup for line breaks and formatting.', max_length=140, verbose_name=b'Text')),
                ('url', models.URLField(null=True, verbose_name=b'URL', blank=True)),
                ('display_url', models.TextField(null=True, verbose_name=b'Display URL', blank=True)),
                ('offset_x', models.IntegerField(verbose_name=b'Offset X')),
                ('offset_y', models.IntegerField(verbose_name=b'Offset Y')),
                ('primary_color', models.CharField(default=b'5A6D81', max_length=6, verbose_name=b'Primary Color')),
                ('font_color', models.CharField(default=b'FFFFFF', max_length=6, verbose_name=b'Font Color')),
                ('border_color', models.CharField(default=b'FFFFFF', max_length=6, verbose_name=b'Border Color')),
            ],
            options={
                'verbose_name': 'Billboard Hotspot',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BillboardImage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=200, verbose_name=b'Title')),
                ('image_url', models.URLField(verbose_name=b'Image URL')),
                ('copyright_info', models.CharField(max_length=200, verbose_name=b'Copyright Info')),
                ('source_url', models.URLField(verbose_name=b'Source URL')),
                ('logo_url', models.URLField(null=True, verbose_name=b'Logo Image URL', blank=True)),
                ('sponsor_url', models.URLField(null=True, verbose_name=b'Logo Sponsor URL', blank=True)),
                ('group', models.ForeignKey(to='auth.Group', null=True)),
            ],
            options={
                'verbose_name': 'Billboard Image',
                'verbose_name_plural': 'Billboard Images',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='jobListing',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('city', models.CharField(max_length=200, null=True, blank=True)),
                ('citySlug', models.SlugField(null=True, blank=True)),
                ('country', models.CharField(max_length=200, null=True, blank=True)),
                ('countrySlug', models.SlugField(null=True, blank=True)),
                ('country_short', models.CharField(db_index=True, max_length=3, null=True, blank=True)),
                ('date_new', models.DateTimeField(verbose_name=b'date new')),
                ('date_updated', models.DateTimeField(verbose_name=b'date updated')),
                ('description', models.TextField()),
                ('hitkey', models.CharField(max_length=50)),
                ('link', models.URLField()),
                ('location', models.CharField(max_length=200, null=True, blank=True)),
                ('reqid', models.CharField(max_length=50, null=True, blank=True)),
                ('state', models.CharField(max_length=200, null=True, blank=True)),
                ('stateSlug', models.SlugField(null=True, blank=True)),
                ('state_short', models.CharField(max_length=3, null=True, blank=True)),
                ('title', models.CharField(max_length=200)),
                ('titleSlug', models.SlugField(max_length=200, null=True, blank=True)),
                ('uid', models.IntegerField(unique=True, db_index=True)),
                ('zipcode', models.CharField(max_length=15, null=True, blank=True)),
            ],
            options={
                'verbose_name': 'Job Listing',
                'verbose_name_plural': 'Job Listings',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SpecialCommitment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200)),
                ('commit', models.CharField(help_text=b'VeteranCommit, SummerCommit, etc...', max_length=200, verbose_name=b'Schema.org Commit Code')),
            ],
            options={
                'verbose_name': 'Special Commitment',
                'verbose_name_plural': 'Special Commitments',
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='billboardhotspot',
            name='billboard_image',
            field=models.ForeignKey(to='seo.BillboardImage'),
            preserve_default=True,
        ),
    ]
