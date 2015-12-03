import datetime
import uuid

from django.core.validators import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.template.defaultfilters import slugify
from django.db.models.signals import post_save, post_delete
from django.utils.translation import ugettext_lazy as _
from collections import OrderedDict
from itertools import chain
from usermodel.models import User
# Create your models here.

class ProfileUnits(models.Model):
    """
    This is the parent class for all user information. Creating any new
    profile unit instances (Education, Name, Email etc) end up in the
    ProfileUnits queryset as well.
    
    """
    date_created = models.DateTimeField(editable=False, auto_now=False, auto_now_add= True)
    date_updated = models.DateTimeField(editable=False, auto_now=True, auto_now_add= False)
    content_type = models.ForeignKey(ContentType, editable=False, null=True)
    user = models.ForeignKey(User, editable=False, null=True, blank=True)

    def save(self, *args, **kwargs):
        """
        Custom save method to set the content type of the instance.
        
        """
        if not self.content_type:
            self.content_type = ContentType.objects.get_for_model(self.__class__)
        super(ProfileUnits, self).save(*args, **kwargs)

    def get_fields(self):
        """
        Returns the module type, value, and field type for all        
        fields on a specific model
        """
        field_list = []
        for field in self._meta.local_fields:
            if not field.primary_key:
                field_list.append([field.verbose_name.title(),
                                   self.__getattribute__(field.name),
                                   field.get_internal_type()])
        return field_list

    def __unicode__(self):
        return self.content_type

    def get_model_name(self):
        return self.content_type.model

    @classmethod
    def get_verbose_class(object):
        return object.__name__

    def get_verbose(self):
        return self.content_type.name.title()

def get_next_or_prev(models,item,direction):
    getit=False
    if direction == "prev":
        models =list(reversed(models))
    for m in models:
        if getit:
            return m
        if str(item)==str(m):
            getit=True
    if getit:
        return models[0]
    return False

Salary_Choices = (
        ('a',''),
        ('b','0-1 lakhs'),
        ('c','1-2 lakhs'),
        ('d','2-3 lakhs'),
        ('e','3-5 lakhs'),
        ('f','5-8 lakhs'),
        ('g','8-12 lakhs'),
        ('h','12-16 lakhs'),
        ('i','16-20 lakhs'),
        ('j','20+ lakhs'),
)

Job_ssChoices = (
    ('a','Actively searching'),
    ('b','Open to offers'),
    ('c','Just networking'),
)


class Basicinfo(ProfileUnits):
    name = models.CharField(max_length = 30, default = 'Name')
    mobile = models.CharField(max_length=10)
    slug = models.SlugField(unique=True)
    located_at = models.CharField(max_length=20, verbose_name = 'Current Location',null=True, blank=True)
    dateofbirth = models.DateField('Date of Birth', blank=True, auto_now=False, auto_now_add = False, null= True )
    profesional_Headline = models.CharField(max_length = 120,blank = True, null=True)
    about_you = models.TextField(null=True, blank=True)
    Job_Search_Status = models.CharField(max_length = 1, choices = Job_ssChoices, default='b' )
    desired_Salary = models.CharField(max_length = 3, choices=Salary_Choices, default=' ' )
    Website_URL = models.CharField(max_length=100, null=True, blank=True)
    Personal_URL = models.CharField(max_length=100, blank = True, null=True)
    Profile_Pic = models.FileField(upload_to = 'talent/profile_pic', blank = True, null=True)
    # employee_Referal = models.TextField(max_length = 200,blank = True, null=True )
    updated = models.DateTimeField(auto_now_add = False, auto_now = True)

    def __unicode__(self):
        return self.name

    def save(self,*args,**kwargs):
        self.slug = "%s-%s"%(slugify(self.name),uuid.uuid4())
        super(Basicinfo,self).save(*args,**kwargs)

class Experience(ProfileUnits):
    title = models.CharField(max_length = 50, default = 'Title')
    company_name = models.CharField(verbose_name="Company Name", max_length = 50, default = '')
    start_date = models.DateField(verbose_name="Start Date")
    stillworking =  models.BooleanField(default=True, verbose_name=_("I still work here"))
    end_date = models.DateField(verbose_name="End Date", blank = True, null =True)
    #industries = models.CharField(max_length = 50)
    usedskills = models.CharField('Your 3 most used skills in this job', max_length = 120, null = True, blank=True)
    salary = models.CharField(max_length = 1, choices = Salary_Choices, default='a' )
    summary = models.TextField(blank = True,null= True)

    def __unicode__(self):
        return self.title

rating_choices = (
    ('',''),
    ('0','1'),
    ('1','2'),
    ('2','3'),
    ('3','4'),
    ('4','5'),
    ('5','6'),
    ('6','7'),
    ('7','8'),
    ('8','9'),
    ('9','10'),
    )

class Skill(ProfileUnits):
    skillname = models.CharField(verbose_name = "Add Your Skill", max_length=30)
    rating = models.CharField(max_length=1,choices = rating_choices, default = '')
    def __unicode__(self):
        return self.skillname

edulevel_choices = (
    ('', _('Education Level')),
    ('a', _('High School')),
    ('b', _('Non-Degree Education')),
    ('c', _('Associate')),
    ('d', _('Bachelor')),
    ('e', _('Master')),
    ('f', _('B.Tech+M.Tech')),
    ('g', _('Doctoral')),

)

class Education(ProfileUnits):
    collegename = models.CharField(verbose_name="School/College Name", max_length = 100)
    city_name = models.CharField(max_length=255, blank=True, verbose_name=_('city'))
    # country_sub_division_code = models.CharField(max_length=5, blank=True, verbose_name=_("State/Region"))
    course = models.CharField(max_length = 50)
    start_date = models.DateField(verbose_name="Start Date",blank=False)
    end_date = models.DateField(verbose_name="End Date", null=True, blank=True)
    degree = models.CharField(max_length = 1, choices = edulevel_choices, blank=True )
    activities = models.TextField(blank = True, null=True)

    def __unicode__(self):
        return self.collegename


socialchoices = (
    ('',''),
    ('f','Facebook'),
    ('t','Twitter'),
    ('l','Linkedin'),
    ('p','Google Plus'),
    ('g','Github'),
    )

class Social(ProfileUnits):
    social_select = models.CharField(max_length=1, choices=socialchoices, null=True, blank=True)
    link = models.CharField(max_length=30, null=True, blank=True)

    def __unicode__(self):
        return "%s %s"%(self.social_select,self.link)


class BaseProfileUnitManager(object):
    """
    Class for managing how profile units are displayed

    Visible units are returned by displayed_units

    Displayed and excluded models are defined as lists of model names

    Child classes can define custom display logic per model in
    <model_name>_is_displayed methods
        i.e.
            def name_is_displayed(self, unit):
                return unit.is_primary()

    Each input accepts a list of model names as strings i.e. ['name','address']
    Inputs:
    :displayed: List of units one wants to be displayed
    :excluded:  List of units one would want to exclude from being displayed
    :order:     List of units to order the output for displayed_units
    """
    def __init__(self, displayed=None, excluded=None, order=None):
        self.displayed = displayed or []
        self.excluded = excluded or []
        self.order = order or []

    def is_displayed(self, unit):
        """
        Returns True if a unit should be displayed
        Input:
        :unit: An instance of ProfileUnit
        """
        try:
            field_is_displayed = getattr(self.unit.get_model_name()+'_is_displayed')
            if field_is_displayed:
                return field_is_displayed(unit)
        except AttributeError:
            pass
        if not self.displayed and not self.excluded:
            return True
        elif self.displayed and self.excluded:
            return unit.get_model_name() in self.displayed \
                and unit.get_model_name() not in self.excluded
        elif self.excluded:
            return unit.get_model_name() not in self.excluded
        elif self.displayed:
            return unit.get_model_name() in self.displayed
        else:
            return True

    def order_units(self, profileunits, order):
        """
        Sorts the dictionary from displayed_units

        Inputs:
        :profileunits:  Dict of profileunits made in displayed_units
        :order:         List of model names (as strings)

        Outputs:
        Returns an OrderedDict of the sorted list
        """
        sorted_units = []
        units_map = {item[0]: item for item in profileunits.items()}
        for item in order:
            try:
                sorted_units.append(units_map[item])
                units_map.pop(item)
            except KeyError:
                pass
        sorted_units.extend(units_map.values())
        return OrderedDict(sorted_units)

    def displayed_units(self, profileunits):
        """
        Returns a dictionary of {model_names:[profile units]} to be displayed

         Inputs:
        :profileunits:  The default value is .all() profileunits, but you can
                        input your own QuerySet of profileunits if you are
                        using specific filters

        Outputs:
        :models:        Returns a dictionary of profileunits, an example:
                        {u'name': [<Name: Foo Bar>, <Name: Bar Foo>]}
        """
        models = {}

        for unit in profileunits:
            if self.is_displayed(unit):
                models.setdefault(unit.get_model_name(), []).append(
                    getattr(unit, str(unit.get_model_name())))

        if self.order:
            models = self.order_units(models, self.order)

        return models


# class PrimaryNameProfileUnitManager(BaseProfileUnitManager):
#     """
#     Excludes primary name from displayed_units and sets self.primary_name
#     """
#     def __init__(self, displayed=None, excluded=None, order=None):
#         super(PrimaryNameProfileUnitManager, self).__init__(displayed,
#                                                             excluded, order)

#     def name_is_displayed(self, profileunit):
#         if profileunit.name.primary:
#             self.primary_name = profileunit.name.get_full_name()
#         return False
