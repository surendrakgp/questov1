# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('seo', '0004_auto_20151019_1327'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompanyUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_added', models.DateTimeField(auto_now=True)),
                ('company', models.ForeignKey(to='seo.Company')),
                ('group', models.ManyToManyField(to='auth.Group', blank=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'mydashboard_companyuser',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='companyuser',
            unique_together=set([('user', 'company')]),
        ),
    ]
