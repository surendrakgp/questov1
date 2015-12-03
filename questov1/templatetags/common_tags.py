import json

from time import strptime, strftime
from django import template
from django.conf import settings

from myjobs import version
from myjobs.models import User
from myjobs.helpers import get_completion, make_fake_gravatar
from seo.models import Company
from universal.helpers import get_company

from django.db.models.loading import get_model

register = template.Library()


@register.simple_tag
def cache_buster():
    cache_buster = "?v=%s" % version.cache_buster
    return cache_buster


@register.simple_tag
def completion_level(level):
    """
    Determines the color of progress bar that should display.

    inputs:
    :level: The completion percentage of a user's profile.

    outputs:
    A string containing the bootstrap bar type
    """

    return get_completion(level)


@register.simple_tag
def get_description(module):
    """
    Gets the description for a module.

    inputs:
    :module: The module to get the description for.

    outputs:
    The description for the module, or an empty string if the module or the
    description doesn't exist.
    """

    try:
        model = get_model("myprofile", module)
        return model.module_description if model.module_description else ""
    except Exception:
        return ""


@register.assignment_tag
def is_a_group_member(user, group):
    """
    Determines whether or not the user is a member of a group

    Inputs:
    :user: User instance
    :group: String of group being checked for

    Outputs:
    Boolean value indicating whether or not the user is a member of the
    requested group
    """

    try:
        return User.objects.is_group_member(user, group)
    except ValueError:
        return False


@register.assignment_tag
def get_company_name(user):
    """
    Gets the name of companies associated with a user

    Inputs:
    :user: User instance

    Outputs:
    A `QuerySet` of companies for which the user is a `CompanyUser`.
    """

    # Only return companies for which the user is a company user
    try:
        return user.company_set.filter(companyuser__user=user)
    except ValueError:
        return Company.objects.none()


@register.simple_tag(takes_context=True)
def active_tab(context, view_name):
    """
    Determines whether a tab should be highlighted as the active tab.

    Inputs:
    :view_name: The name of the view, as a string, for the tab being evaluated.

    Outputs:
    Either "active" if it's the active tab, or an empty string.
    """

    return "active" if context.get('view_name', '') == view_name else ""


@register.simple_tag
def get_gravatar(user, size=20):
    """
    Gets the img or div tag for the gravatar or initials block.
    """
    try:
        return user.get_gravatar_url(size)
    except:
        return ''


@register.simple_tag
def get_gravatar_by_id(user_id, size=20):
    try:
        return User.objects.get(id=user_id).get_gravatar_url(size)
    except:
        return ''


@register.simple_tag
def get_nonuser_gravatar(email, size=20):
    try:
        return make_fake_gravatar(email, size)
    except:
        return ''


@register.assignment_tag(takes_context=True)
def get_ms_name(context):
    """
    Gets the site name for the user's last-visited microsite, if one exists
    """
    request = context.get('request')
    cookie = request.COOKIES.get('lastmicrositename')
    if cookie and len(cookie) > 33:
        cookie = cookie[:30] + '...'
    return cookie


@register.simple_tag(takes_context=True)
def get_ms_url(context):
    """
    Gets the url for the user's last-visited microsite from a cookie,
    or www.my.jobs if that cookie does not exist.
    """
    request = context.get('request')
    cookie = request.COOKIES.get('lastmicrosite')
    if cookie:
        return cookie
    return 'http://www.my.jobs'


@register.simple_tag
def str_to_date(string):
    try:
        return strftime("%b. %d %Y", strptime(string, "%Y-%m-%dT%H:%M:%SZ"))
    except:
        return strftime("%b. %d %Y", strptime(string, "%Y-%m-%dT%H:%M:%S.%fZ"))


@register.simple_tag
def to_string(value):
    return str(value)


@register.filter
def get_attr(obj, attr):
    return obj.get(attr)


@register.simple_tag
def paginated_index(index, page, per_page=None):
    """
    Given an index, page number, and number of items per page, returns a proper
    index.

    inputs:
    :index: The index you are converting from. Should be less than `per_page`.
    :page: The page for which you want to calculate the new index
    :per_page: Number of records per page

    outputs:
    New index which takes pagination into consideration.
    """

    per_page = int(per_page or 10)
    page = int(page or 1) - 1
    index = int(index or 1)
    return page * per_page + index


@register.assignment_tag(takes_context=True)
def gz(context):
    request = context.get('request', None)
    if request == None or settings.DEBUG:
        return ''
    ae = request.META.get('HTTP_ACCEPT_ENCODING', '')
    if 'gzip' in ae:
        return ''
        # We've stopped returning .gz because of a bug in IE11 which causes
        # the static files to not be loaded at all. No longer serving .gz
        # files will also give us the opportunity to see what impact the
        # static files actually have on load time.
        #return '.gz'
    else:
        return ''


@register.assignment_tag
def json_companies(companies):
    info = [{"name": company.name, "id": company.id} for company in companies]
    return json.dumps(info)


@register.filter
def get_suggestions(user):
    """
    Get all profile suggestions for the given user, sorted by profile importance

    Inputs:
    :user: User for whom suggestions will be retrieved

    Outputs:
    :suggestions: List of profile suggestions
    """
    suggestions = [suggestion for suggestion in
                   user.profileunits_set.model.suggestions(user,
                                                           by_priority=False)
                   if suggestion['priority'] == 5]
    return suggestions


@register.assignment_tag(takes_context=True)
def get_company_from_cookie(context):
    request = context.get('request')
    if request:
        return get_company(request)
    return None
