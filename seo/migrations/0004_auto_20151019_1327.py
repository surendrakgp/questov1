# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('seo', '0003_remove_companyuser_date_added'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='companyuser',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='companyuser',
            name='company',
        ),
        migrations.RemoveField(
            model_name='companyuser',
            name='group',
        ),
        migrations.RemoveField(
            model_name='companyuser',
            name='user',
        ),
        migrations.DeleteModel(
            name='CompanyUser',
        ),
    ]
