from datetime import datetime, time
import pytz

from django.core.exceptions import ValidationError
from django.forms import (FileField, FileInput, MultiValueField, MultiWidget,
                          Select, fields)
from django.utils.safestring import mark_safe
from django.utils.timezone import localtime, now


hour_choices = [(str(x).zfill(2), str(x).zfill(2)) for x in range(1, 13)]
length_hour_choices = [(str(x).zfill(2), str(x).zfill(2)) for x in range(0, 24)]
minute_choices = [(str(x).zfill(2), str(x).zfill(2)) for x in range(0, 60)]
time_choices = [('AM', 'AM'), ('PM', 'PM')]
month_choices = [
    ('Jan', 'Jan'),
    ('Feb', 'Feb'),
    ('Mar', 'Mar'),
    ('Apr', 'Apr'),
    ('May', 'May'),
    ('Jun', 'Jun'),
    ('Jul', 'Jul'),
    ('Aug', 'Aug'),
    ('Sep', 'Sep'),
    ('Oct', 'Oct'),
    ('Nov', 'Nov'),
    ('Dec', 'Dec'),
]
day_choices = [(str(x).zfill(2), str(x).zfill(2)) for x in range(1, 32)]
year_choices = [(str(x), str(x)) for x in range(2005, 2050)]


class MultipleFileInputWidget(FileInput):
    def render(self, name, value, attrs={}):
        attrs['multiple'] = 'multiple'
        render = super(MultipleFileInputWidget, self).render(name, value, attrs)
        render = "<div class='attachment'><span id='span_attachment'>%s</span></div>" % render
        return mark_safe(render)

    def value_from_datadict(self, data, files, name):
        if hasattr(files, 'getlist'):
            return files.getlist(name)
        return [files.get(name, None)]


class SplitDateDropDownWidget(MultiWidget):
    def __init__(self, attrs=None):
        widgets = (
            Select(attrs=attrs, choices=month_choices),
            Select(attrs=attrs, choices=day_choices),
            Select(attrs=attrs, choices=year_choices),
        )
        super(SplitDateDropDownWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if not value:
            value = localtime(now())
        month = datetime.strftime(value, '%b')
        day = datetime.strftime(value, '%d')
        year = datetime.strftime(value, '%Y')
        return [month, day, year]

    def format_output(self, rendered_widgets):
        return ''.join([
            '<div class="date-time">',
            rendered_widgets[0], rendered_widgets[1], rendered_widgets[2],
            '</div>'
        ])


class SplitDateTimeDropDownWidget(MultiWidget):
    def __init__(self, attrs=None):
        widgets = (
            Select(attrs=attrs, choices=month_choices),
            Select(attrs=attrs, choices=day_choices),
            Select(attrs=attrs, choices=year_choices),
            Select(attrs=attrs, choices=hour_choices),
            Select(attrs=attrs, choices=minute_choices),
            Select(attrs=attrs, choices=time_choices)
        )
        super(SplitDateTimeDropDownWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if not value:
            value = localtime(now())
        else:
            if value.tzinfo:
                value = localtime(value)
            else:
                value = localtime(pytz.utc.localize(value))
        month = datetime.strftime(value, '%b')
        day = datetime.strftime(value, '%d')
        year = datetime.strftime(value, '%Y')
        hour = datetime.strftime(value, '%I')
        minutes = datetime.strftime(value, '%M')
        am_pm = datetime.strftime(value, '%p')
        return [month, day, year, hour, minutes, am_pm]

    def format_output(self, rendered_widgets):
        return ''.join([
            '<div class="date-time">',
            rendered_widgets[0], rendered_widgets[1], rendered_widgets[2],
            '<br/>',
            rendered_widgets[3], rendered_widgets[4], rendered_widgets[5],
            '</div>'
        ])


class TimeDropDownWidget(MultiWidget):
    def __init__(self, attrs=None):
        widgets = (
            Select(attrs=attrs, choices=length_hour_choices),
            Select(attrs=attrs, choices=minute_choices)
        )
        super(TimeDropDownWidget, self).__init__(widgets, attrs)

    def format_output(self, rendered_widgets):
        return ''.join([rendered_widgets[0],
                        '<b> hours</b>', '&nbsp;&nbsp;&nbsp;',
                        rendered_widgets[1], '<b> minutes</b>'])

    def decompress(self, value):
        if value:
            return [value.hour, value.minute]
        return [None, None]


class SplitDateTimeDropDownField(MultiValueField):
    widget = SplitDateTimeDropDownWidget

    def __init__(self, *args, **kwargs):
        list_fields = (
            fields.ChoiceField(choices=month_choices),
            fields.ChoiceField(choices=day_choices),
            fields.ChoiceField(choices=year_choices),
            fields.ChoiceField(choices=hour_choices),
            fields.ChoiceField(choices=minute_choices),
            fields.ChoiceField(choices=time_choices),
        )
        super(SplitDateTimeDropDownField, self). __init__(
            fields=list_fields,
            *args, **kwargs
        )

    def compress(self, decompressed_date_time):
        date_string = " ".join(decompressed_date_time)
        try:
            date_time = datetime.strptime(date_string, "%b %d %Y %I %M %p")
        except ValueError:
            raise ValidationError('Invalid date format.')
        return date_time

class SplitDateDropDownField(MultiValueField):
    widget = SplitDateDropDownWidget

    def __init__(self, *args, **kwargs):
        list_fields = (
            fields.ChoiceField(choices=month_choices),
            fields.ChoiceField(choices=day_choices),
            fields.ChoiceField(choices=year_choices),
        )
        super(SplitDateDropDownField, self). __init__(
            fields=list_fields,
            *args, **kwargs
        )

    def compress(self, decompressed_date_time):
        date_string = " ".join(decompressed_date_time)
        try:
            date_time = datetime.strptime(date_string, "%b %d %Y")
        except ValueError:
            raise ValidationError('Invalid date format.')
        return date_time


class TimeDropDownField(MultiValueField):
    widget = TimeDropDownWidget

    def __init__(self, *args, **kwargs):

        list_fields = (
            fields.ChoiceField(required=False, choices=length_hour_choices),
            fields.ChoiceField(required=False, choices=minute_choices),
        )

        super(TimeDropDownField, self). __init__(
            fields=list_fields,
            *args, **kwargs
        )

    def compress(self, decompressed_time):
        return time(int(decompressed_time[0]), int(decompressed_time[1]))


class MultipleFileField(FileField):
    widget = MultipleFileInputWidget

    def to_python(self, data):
        if not data:
            return None
        file_list = []
        for f in data:
            file_list.append(super(MultipleFileField, self).to_python(f))
        return file_list
