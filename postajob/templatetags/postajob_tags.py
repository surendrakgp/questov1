import bleach

from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import resolve, reverse
from django.template import Library
from django.template.loader import render_to_string
from django.utils.text import slugify
from django.utils.safestring import mark_safe

from postajob.models import PurchasedJob, PurchasedProduct
from universal.helpers import get_company

register = Library()


@register.simple_tag
def get_job_links(job, max_sites=3):
    if hasattr(job, 'is_approved') and not job.is_approved:
        return ''

    locations = job.locations.all()

    sites = job.on_sites()
    domains = [site.domain for site in sites]

    title_slug = bleach.clean(slugify(job.title))

    base_url = 'http://{domain}/{loc_slug}/{title_slug}/{guid}/job/'
    href_tag = '<a href="{url}">{domain}</a>'
    urls = []
    for domain in domains:
        for location in locations:
            loc_slug = bleach.clean(slugify(u'{city}, {state}'.format(
                city=location.city, state=location.state_short)))
            job_url = base_url.format(domain=domain, loc_slug=loc_slug,
                                      title_slug=title_slug, guid=location.guid)

            urls.append(href_tag.format(url=job_url, domain=domain))
    url_html = mark_safe("<br/>".join(urls[:max_sites]))
    if max_sites and len(urls) > max_sites:
        url_html = mark_safe("%s <br/>..." % url_html)
    return url_html



@register.assignment_tag
def get_jobs(purchased_product):
    return PurchasedJob.objects.filter(purchased_product=purchased_product)


@register.simple_tag(takes_context=True)
def get_form_action(context):
    current_url_name = resolve(context['request'].path).url_name
    if context.get('item') and context['item'].pk:
        return 'Edit'
    elif current_url_name == 'purchasedproduct_add':
        return 'Purchase'
    return 'Add'


@register.simple_tag(takes_context=True)
def select(context, pattern, ignore=None):
    """
    Returns "selected" (CSS class for styling selected buttons) if the
    `pattern` occurs as part of the current URL, but does not include `ignore`.
    """
    path = context.get('request').get_full_path()

    if pattern in path:
        if ignore and ignore in path:
            return ''
        
        return 'selected'


@register.assignment_tag
def get_purchase_total(purchases):
    return sum(purchase.purchase_amount for purchase in purchases)


@register.simple_tag
def get_redeemer(offline_purchase):
    # This is only set if a user has redeemed the purchase.
    if offline_purchase.redeemed_by:
        return offline_purchase.redeemed_by.company.name
    # Otherwise attempt to get the name from a Product created from the
    # OfflinePurchase.
    else:
        products = PurchasedProduct.objects.filter(
            offline_purchase=offline_purchase)
        if products:
            return products[0].owner

    # Otherwise the product hasn't been redeemed yet, and therefore there
    # is no redeemer.
    return ''


@register.simple_tag
def get_product_names(offline_purchase):
    products = offline_purchase.products.all()
    names = [product.name for product in products]
    return ", ".join(names)


@register.assignment_tag
def get_content_type(obj):
    return ContentType.objects.get_for_model(obj.__class__)


@register.filter
def get_sites(form):
    return form.fields['site_packages'].queryset.values_list('domain',
                                                             flat=True)


@register.simple_tag(takes_context=True)
def get_purchasedjob_add_link(context):
    """
    Generates add links for creating PurchasedJobs. If the user is blocked, the
    link is replaced with a modal telling them so.
    """
    request = context['request']
    company = get_company(request)

    # Add 'blocked' context variable; determines if we are going to add a real
    # link or a modal when rendering the template.
    context['blocked'] = request.user in company.companyprofile.blocked_users.all()

    if 'purchased_product' not in context:
        # This is called from both the company owner side and the job poster
        # side. The context variable for the current purchased product is
        # different between the two.
        context['purchased_product'] = context['product']

    link = render_to_string('postajob/includes/purchasedjob_add_link.html',
                            context)
    return mark_safe(link)
