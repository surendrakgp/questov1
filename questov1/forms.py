from django.forms import *




class BaseUserForm(ModelForm):
    """
    Most models in the other apps are associated with a user. This base form
    will take a user object as a key word argument and saves the form instance
    to a that specified user. It also takes a few common inputs that can be
    used to customize form rendering.

    Inputs (these are the common inputs we will use for rendering forms):
    :user: a user object. We will always pass a user object in  because all
        ProfileUnits are linked to a user.
    :auto_id: this is a boolean that determines whether a label is displayed or
        not and is by default set to True. Setting this to false uses the
        placeholder text instead, except for boolean and select fields.
    :empty_permitted: allow form to be submitted as empty even if the fields
        are required. This is particularly useful when we combine multiple
        Django forms on the front end and submit it as one request instead of
        several separate requests.
    :only_show_required: Template uses this flag to determine if it should only
        render required forms. Default is False.
    """

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.only_show_required = kwargs.pop('only_show_required', False)
        super(BaseUserForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super(BaseUserForm, self).save(commit=False)
        if self.user and not self.user.is_anonymous():
            instance.user = self.user
            instance.save()
        return instance
