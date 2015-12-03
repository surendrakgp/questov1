# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProfileUnits',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_updated', models.DateTimeField(auto_now=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Experience',
            fields=[
                ('profileunits_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='myprofile.ProfileUnits')),
                ('title', models.CharField(default=b'Title', max_length=50)),
                ('company_name', models.CharField(default=b'', max_length=50, verbose_name=b'Company Name')),
                ('start_date', models.DateField(verbose_name=b'Start Date')),
                ('stillworking', models.BooleanField(default=True, verbose_name='I still work here')),
                ('end_date', models.DateField(null=True, verbose_name=b'End Date', blank=True)),
                ('usedskills', models.CharField(max_length=120, null=True, verbose_name=b'Your 3 most used skills in this job', blank=True)),
                ('salary', models.CharField(default=b'a', max_length=1, choices=[(b'a', b''), (b'b', b'0-1 lakhs'), (b'c', b'1-2 lakhs'), (b'd', b'2-3 lakhs'), (b'e', b'3-5 lakhs'), (b'f', b'5-8 lakhs'), (b'g', b'8-12 lakhs'), (b'h', b'12-16 lakhs'), (b'i', b'16-20 lakhs'), (b'j', b'20+ lakhs')])),
                ('summary', models.TextField(null=True, blank=True)),
            ],
            options={
            },
            bases=('myprofile.profileunits',),
        ),
        migrations.CreateModel(
            name='Education',
            fields=[
                ('profileunits_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='myprofile.ProfileUnits')),
                ('collegename', models.CharField(max_length=100, verbose_name=b'School/College Name')),
                ('city_name', models.CharField(max_length=255, verbose_name='city', blank=True)),
                ('course', models.CharField(max_length=50)),
                ('start_date', models.DateField(verbose_name=b'Start Date')),
                ('end_date', models.DateField(null=True, verbose_name=b'End Date', blank=True)),
                ('degree', models.CharField(blank=True, max_length=1, choices=[(b'', 'Education Level'), (b'a', 'High School'), (b'b', 'Non-Degree Education'), (b'c', 'Associate'), (b'd', 'Bachelor'), (b'e', 'Master'), (b'f', 'B.Tech+M.Tech'), (b'g', 'Doctoral')])),
                ('activities', models.TextField(null=True, blank=True)),
            ],
            options={
            },
            bases=('myprofile.profileunits',),
        ),
        migrations.CreateModel(
            name='Basicinfo',
            fields=[
                ('profileunits_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='myprofile.ProfileUnits')),
                ('name', models.CharField(default=b'Name', max_length=30)),
                ('mobile', models.CharField(max_length=10)),
                ('slug', models.SlugField(unique=True)),
                ('located_at', models.CharField(max_length=20, null=True, verbose_name=b'Current Location', blank=True)),
                ('dateofbirth', models.DateField(null=True, verbose_name=b'Date of Birth', blank=True)),
                ('profesional_Headline', models.CharField(max_length=120, null=True, blank=True)),
                ('about_you', models.TextField(null=True, blank=True)),
                ('Job_Search_Status', models.CharField(default=b'b', max_length=1, choices=[(b'a', b'Actively searching'), (b'b', b'Open to offers'), (b'c', b'Just networking')])),
                ('desired_Salary', models.CharField(default=b' ', max_length=3, choices=[(b'a', b''), (b'b', b'0-1 lakhs'), (b'c', b'1-2 lakhs'), (b'd', b'2-3 lakhs'), (b'e', b'3-5 lakhs'), (b'f', b'5-8 lakhs'), (b'g', b'8-12 lakhs'), (b'h', b'12-16 lakhs'), (b'i', b'16-20 lakhs'), (b'j', b'20+ lakhs')])),
                ('Website_URL', models.CharField(max_length=100, null=True, blank=True)),
                ('Personal_URL', models.CharField(max_length=100, null=True, blank=True)),
                ('Profile_Pic', models.FileField(null=True, upload_to=b'talent/profile_pic', blank=True)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
            options={
            },
            bases=('myprofile.profileunits',),
        ),
        migrations.CreateModel(
            name='Skill',
            fields=[
                ('profileunits_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='myprofile.ProfileUnits')),
                ('skillname', models.CharField(max_length=30, verbose_name=b'Add Your Skill')),
                ('rating', models.CharField(default=b'', max_length=1, choices=[(b'', b''), (b'0', b'1'), (b'1', b'2'), (b'2', b'3'), (b'3', b'4'), (b'4', b'5'), (b'5', b'6'), (b'6', b'7'), (b'7', b'8'), (b'8', b'9'), (b'9', b'10')])),
            ],
            options={
            },
            bases=('myprofile.profileunits',),
        ),
        migrations.CreateModel(
            name='Social',
            fields=[
                ('profileunits_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='myprofile.ProfileUnits')),
                ('social_select', models.CharField(blank=True, max_length=1, null=True, choices=[(b'', b''), (b'f', b'Facebook'), (b't', b'Twitter'), (b'l', b'Linkedin'), (b'p', b'Google Plus'), (b'g', b'Github')])),
                ('link', models.CharField(max_length=30, null=True, blank=True)),
            ],
            options={
            },
            bases=('myprofile.profileunits',),
        ),
        migrations.AddField(
            model_name='profileunits',
            name='content_type',
            field=models.ForeignKey(editable=False, to='contenttypes.ContentType', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='profileunits',
            name='user',
            field=models.ForeignKey(blank=True, editable=False, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
    ]
