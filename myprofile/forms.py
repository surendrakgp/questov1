from django.conf import settings
from django.forms import *
from django.utils.translation import ugettext_lazy as _
from questov1.forms import BaseUserForm
from .models import *

def generate_custom_widgets(model):
    """
    Generates custom widgets and sets placeholder values and class names based
    on field type

    Inputs:
    :model:       model class from form Meta
    
    Outputs:
    :widgets:     dictionary of widgets with custom attributes defined
    """
    fields = model._meta.fields
    widgets = {}
    
    for field in fields:
        internal_type = field.get_internal_type()
        # exclude profile unit base fields
        if field.model == model:
            attrs = {}
            attrs['id'] = 'id_' + model.__name__.lower() + '-' + field.attname
            attrs['placeholder'] = field.verbose_name.title()
            if field.choices:
                widgets[field.attname] = Select(attrs=attrs)
            elif internal_type == 'BooleanField':
                attrs['label_class'] = 'checkbox'
                widgets[field.attname] = CheckboxInput(attrs=attrs)
            elif internal_type == 'DateField':
                widgets[field.attname] = DateInput(
                format=settings.FORM_DATE_FORMAT, attrs=attrs)
            elif internal_type == 'FileField':
                widgets[field.attname] = FileInput(attrs=attrs)
            elif internal_type == 'TextField':
                widgets[field.attname] = Textarea(attrs=attrs)
            else:
                widgets[field.attname] = TextInput(attrs=attrs)
                pass
    return widgets


class BasicinfoForm(BaseUserForm):
    class Meta:
        form_name = _("Basic Information")
        model = Basicinfo
        exclude = ['slug']
        widgets = generate_custom_widgets(model)
        
class ExperienceForm(BaseUserForm):
    def __init__(self, *args, **kwargs):
        super(ExperienceForm, self).__init__(*args, **kwargs)
        self.fields['start_date'].input_formats = settings.DATE_INPUT_FORMATS
        self.fields['end_date'].input_formats = settings.DATE_INPUT_FORMATS

    class Meta:
        model = Experience
        widgets = generate_custom_widgets(model)
        widgets['start_date'].attrs['placeholder'] = 'ie 05/30/2005'
        widgets['end_date'].attrs['placeholder'] = 'ie 06/01/2007'
        fields = '__all__'


class EducationForm(BaseUserForm):
    def __init__(self, *args, **kwargs):
        super(EducationForm, self).__init__(*args, **kwargs)
        self.fields['start_date'].input_formats = settings.DATE_INPUT_FORMATS
        self.fields['end_date'].input_formats = settings.DATE_INPUT_FORMATS

    class Meta:
        model = Education
        widgets = generate_custom_widgets(model)
        widgets['start_date'].attrs['placeholder'] = 'ie 05/30/2005'
        widgets['end_date'].attrs['placeholder'] = 'ie 06/01/2007'
        fields = '__all__'

class SkillForm(BaseUserForm):
    def __init__(self, *args, **kwargs):
        super(SkillForm, self).__init__(*args, **kwargs)
    
    class Meta:
        model = Skill
        fields = '__all__'
        widgets = generate_custom_widgets(model)
        

class SocialForm(BaseUserForm):
    def __init__(self, *args, **kwargs):
        super(SocialForm, self).__init__(*args, **kwargs)   
 
    class Meta:
        model = Social
        widgets = generate_custom_widgets(model)
        fields = '__all__'
