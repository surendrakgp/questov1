from itertools import chain
from django.forms import ChoiceField, Select
from django.utils.encoding import force_unicode
from django.utils.html import escape, conditional_escape


class NoValidationChoiceField(ChoiceField):
    def validate(self, value):
        """
        Bypasses the typical choice field validation. Used in cases
        where choices have been inserted, removed, or re-invisioned using
        javascript.

        """
        pass

    def clean(self, value):
        if value is None:
            return super(NoValidationChoiceField, self).clean(value)
        return value


class SelectWithOptionClasses(Select):
    def __init__(self, attrs=None, choices=()):
        self.choices = choices
        super(SelectWithOptionClasses, self).__init__(attrs, [choice[:-1]
                                                              for choice in
                                                              choices])

    def render_option(self, selected_choices, option_value, option_label,
                      option_class=''):
        option_value = force_unicode(option_value)
        if option_value in selected_choices:
            selected_html = u' selected="selected"'
            if not self.allow_multiple_selected:
                selected_choices.remove(option_value)
        else:
            selected_html = ''
        return u'<option value="%s" class="%s"%s>%s</option>' % (
            escape(option_value), escape(option_class), selected_html,
            conditional_escape(force_unicode(option_label)))

    def render_options(self, choices, selected_choices):
        selected_choices = set(force_unicode(choice) for choice in
                               selected_choices)
        choices = [(c[0], c[1], '') for c in choices]
        more_choices = self.choices
        output = []
        for option_value, option_label, option_class in chain(more_choices,
                                                              choices):
            output.append(self.render_option(selected_choices, option_value,
                                             option_label, option_class))
        return u'\n'.join(output)
