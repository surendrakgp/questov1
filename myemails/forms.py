from django.db.models import Q
from django.forms import ModelForm
from myemails.models import EmailTemplate

from postajob.fields import NoValidationChoiceField
from universal.helpers import get_company


class EventFieldForm(ModelForm):
    field = NoValidationChoiceField(choices=[('', '---------')])

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request')
        super(EventFieldForm, self).__init__(*args, **kwargs)
        setattr(self, 'request', request)
        initial = self.initial.get('field')
        choices = [('', '---------')]
        if initial:
            # It doesn't matter that we aren't actually retrieving the full
            # choice list at this point in time. This is just to preserve the
            # current value - the full list is retrieved via ajax on load.
            choices.append((initial, initial))
        self.fields['field'] = NoValidationChoiceField(choices=choices)
        if not request.user.is_superuser:
            company = get_company(request)
            queryset = EmailTemplate.objects.filter(
                Q(owner=company) | Q(owner__isnull=True))
            self.fields['email_template'].queryset = queryset
