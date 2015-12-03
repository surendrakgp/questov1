from django.forms import (ChoiceField, MultiWidget, MultiValueField, Select,
                          ValidationError, fields)
from datetime import date
from calendar import monthrange

EXP_MONTH = [(x, x) for x in xrange(1, 13)]
EXP_YEAR = [(x, x) for x in xrange(date.today().year, date.today().year + 15)]


class ExpWidget(MultiWidget):
    def __init__(self, attrs=None):
        widgets = (
            Select(attrs=attrs, choices=EXP_MONTH),
            Select(attrs=attrs, choices=EXP_YEAR)
        )
        super(ExpWidget, self).__init__(widgets, attrs)

    def decompress(self, value):
        if value:
            return [value.month, value.year]
        else:
            return [date.today().month, date.today().year]

    def format_output(self, rendered_widgets):
        html = ' '.join(rendered_widgets)
        return '<span style="white-space: nowrap">%s</span>' % html


class ExpField(MultiValueField):
    widget = ExpWidget

    def __init__(self, *args, **kwargs):
        kwargs['fields'] = (
            ChoiceField(choices=EXP_MONTH),
            ChoiceField(choices=EXP_YEAR),
        )
        super(ExpField, self).__init__(*args, **kwargs)

    def clean(self, value):
        exp_date = super(ExpField, self).clean(value)
        if date.today() > exp_date:
            raise ValidationError("This card is expired.")
        return exp_date

    def compress(self, data_list):
        if data_list:
            empty = fields.EMPTY_VALUES
            if (data_list[1] in empty) or (data_list[1] in empty):
                raise ValidationError("The expiration date you entered is "
                                      "invalid.")
            year = int(data_list[1])
            month = int(data_list[0])
            day = monthrange(year, month)[1]
            return date(year, month, day)
        return None
