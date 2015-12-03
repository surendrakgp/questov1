# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('seo', '0006_remove_companyuser_date_added'),
    ]

    operations = [
        migrations.AddField(
            model_name='companyuser',
            name='date_added',
            field=models.DateTimeField(default=datetime.date(2015, 10, 19), auto_now=True),
            preserve_default=False,
        ),
    ]
