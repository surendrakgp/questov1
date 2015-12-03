from django import template
from django.forms.fields import BooleanField, CheckboxInput
from django.utils.encoding import force_text

register = template.Library()

@register.assignment_tag
def is_boolean_field(field):
    return type(field.field) == BooleanField


@register.filter
def is_checkbox_field(field):
    return type(field.field.widget) == CheckboxInput


@register.filter(name='readable_boolean')
def readable_boolean(value):
    value_lookup = {
        "True": "Yes",
        "False": "No"
    }
    return value_lookup.get(force_text(value), value)


@register.simple_tag(name='add_required_label')
def add_required_label(field, *classes):
    if not classes:
        classes = ()
    if field.errors:
        classes += ('label-required',)
    if field.field.required:
        field.label = u"{label} *".format(label=unicode(field.label))
    label = field.label_tag(attrs={'class': ' '.join(classes)})
    return label.replace(":", "")
