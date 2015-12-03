from functools import partial
from django.conf import settings
from universal.decorators import not_found_when, warn_when

def site_misconfigured(request):
    try:
        return not settings.SITE.canonical_company.has_packages
    except AttributeError:
        return True

message_when_site_misconfigured = partial(
    warn_when,
    condition=site_misconfigured,
    message='Please contact your member representative to activate this '
            'feature.')

error_when_site_misconfigured = partial(
    not_found_when,
    condition=site_misconfigured,
    message='Accessed company owns no site packages.')
