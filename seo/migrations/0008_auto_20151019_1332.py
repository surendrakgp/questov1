# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('flatpages', '0001_initial'),
        ('auth', '0001_initial'),
        ('seo', '0007_companyuser_date_added'),
    ]

    operations = [
        migrations.CreateModel(
            name='City',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, db_index=True)),
            ],
            options={
                'verbose_name': 'City',
                'verbose_name_plural': 'Cities',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Country',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, db_index=True)),
                ('abbrev', models.CharField(db_index=True, max_length=255, null=True, blank=True)),
                ('abbrev_short', models.CharField(db_index=True, max_length=255, null=True, blank=True)),
            ],
            options={
                'verbose_name': 'Country',
                'verbose_name_plural': 'Countries',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='CustomPage',
            fields=[
                ('flatpage_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='flatpages.FlatPage')),
                ('meta', models.TextField(blank=True)),
                ('meta_description', models.CharField(max_length=255, blank=True)),
                ('group', models.ForeignKey(blank=True, to='auth.Group', null=True)),
            ],
            options={
                'verbose_name': 'Custom Page',
                'verbose_name_plural': 'Custom Pages',
            },
            bases=('flatpages.flatpage',),
        ),
        migrations.CreateModel(
            name='State',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, db_index=True)),
                ('nation', models.ForeignKey(to='seo.Country')),
            ],
            options={
                'verbose_name': 'State',
                'verbose_name_plural': 'States',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='state',
            unique_together=set([('name', 'nation')]),
        ),
        migrations.AddField(
            model_name='city',
            name='nation',
            field=models.ForeignKey(to='seo.Country'),
            preserve_default=True,
        ),
    ]
