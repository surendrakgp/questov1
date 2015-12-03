# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('seo', '0005_auto_20151019_1327'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='companyuser',
            name='date_added',
        ),
    ]
