import json
import urllib
import urllib2
from urlparse import urlparse, urlunparse, parse_qs, parse_qsl
from urllib import urlencode
import datetime
import logging

from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from django.conf import settings
from django.utils.encoding import smart_str, smart_unicode

from universal.helpers import get_domain


def update_url_if_protected(url, user):
    """
    Adds a key that bypasses authorization on protected sites
    if the site is protected and the user has access to the site.

    """
    from seo.models import SeoSite

    search_domain = urlparse(url).netloc
    protected_domains = []
    for key in settings.PROTECTED_SITES.keys():
        try:
            protected_domains.append(SeoSite.objects.get(pk=key).domain)
        except SeoSite.DoesNotExist:
            pass

    cleaned_protected_domains = [get_domain(domain)
                                 for domain in protected_domains]

    if search_domain in cleaned_protected_domains:
        indx = cleaned_protected_domains.index(search_domain)
        groups = settings.PROTECTED_SITES[settings.PROTECTED_SITES.keys()[indx]]
        if list(set(groups) & set(user.groups.values_list('id', flat=True))):
            if '?' in url:
                url = "%s&key=%s" % (url, settings.SEARCH_API_KEY)
            else:
                url = "%s?key=%s" % (url, settings.SEARCH_API_KEY)

    return url


def get_rss_soup(rss_url):
    """
    Turn a URL into a BeautifulSoup object

    Inputs:
    :rss_url:      URL of an RSS feed

    Outputs:
                   BeautifulSoup object
    """

    rss_feed = urllib2.urlopen(rss_url).read()
    return BeautifulSoup(rss_feed, "html.parser")


def validate_dotjobs_url(search_url, user):
    """
    Validate (but not parse) a .jobs URL. Nothing is returned if the URL has no
    no rss link is found. Only the title is returned if the rss url is invalid.

    Inputs:
    :search_url:   URL to be validated

    Outputs:
    :title:        The title attribute taken from the rss link
    :rss_url:      The href attribute taken from the rss link
    """
    if not search_url:
        return None, None

    if search_url.find('://') == -1:
        search_url = "http://" + search_url

    search_url = update_url_if_protected(search_url, user)

    logger = logging.getLogger(__name__)

    # Encode parameters
    try:
        search_parts = list(urlparse(search_url.rstrip('/')))
        search_parts[4] = parse_qsl(search_parts[4])
        search_parts[4] = urllib.urlencode(search_parts[4])
        search_url = urlunparse(tuple(search_parts))
    except Exception as e:
        logger.error("Failed to parse dotjobs url: %s" % search_url)
        logger.exception(e)
        return None, None

    try:
        page = urllib.urlopen(search_url).read()
        soup = BeautifulSoup(page, "html.parser")
    except Exception as e:
        logger.error("Failed to download or parse page with rss link: %s"
                     % search_url)
        logger.exception(e)
        return None, None

    link = soup.find("link", {"type": "application/rss+xml"})

    if link:
        title = link.get('title')
        rss_url = link.get('href')
        try:
            params = ''
            if rss_url.find('?') == -1:
                params += '?num_items=1'
            else:
                params += '&num_items=1'
            get_rss_soup(rss_url+params)
        except Exception:
            return title, None
        return title, rss_url
    else:
        return None, None


def get_json(json_url):
    """
    Turn a remote json file into a Python dictionary

    Inputs:
    :json_url:    URL of a json file

    Outputs:
                    List of one or more Python dictionaries
    """
    json_feed = urllib2.urlopen(json_url).read()
    try:
        return json.loads(json_feed)
    except ValueError:
        return []


def parse_feed(feed_url, frequency='W', num_items=100, offset=0,
               return_items=None, use_json=True, last_sent=None,
               ignore_dates=False):
    """
    Parses job data from an RSS feed and returns it as a list of dictionaries.
    The data returned is limited based on the corresponding data range (daily,
    weekly, or monthly).

    Inputs:
    :feed_url:      URL of an RSS feed
    :frequency:     String 'D', 'W', or 'M'.
    :num_items:     Maximum number of items to be retrieved.
    :offset:        The page on which the RSS feed is on.
    :return_items: The number of items to be returned; if not provided,
        equals :num_items:
    :use_json:       Default feed to json, if available; Default: True
    :last_sent: Date that this saved search, if one exists, was sent; used to
        grab jobs during a wider span of time in the event that saved searches
        encounter issues and don't send for a period of time; Default: None
    :ignore_dates: Boolean that determines if we should ignore job publish
        dates; :last_sent: will still be used to denote NEW jobs, but filtering
        based on publish date will be bypassed. Default: False

    Outputs:
    :tuple:         First index is a list of :return_items: jobs
                    Second index is the total job count
    """
    return_items = return_items or num_items
    if feed_url.find('?') > -1:
        separator = '&'
    else:
        separator = '?'

    if use_json:
        feed_url = feed_url.replace('feed/rss', 'feed/json')

    interval = get_interval_from_frequency(frequency)

    end = datetime.date.today()
    start = end + datetime.timedelta(days=interval)
    if last_sent is not None:
        last_sent_date = last_sent.date()
        last_sent_diff = last_sent_date - start
        start = min([start, last_sent_date])

    item_list = []

    feed_url += '%snum_items=%s&offset=%s' % (
        separator, str(num_items), str(offset))

    if (('days_ago=' not in feed_url) and (last_sent is not None)
            and (not ignore_dates)):
        feed_url += '&days_ago=%s' % -last_sent_diff.days

    is_json = 'feed/json' in feed_url
    if is_json:
        items = get_json(feed_url)
    else:
        rss_soup = get_rss_soup(feed_url)
        items = rss_soup.find_all('item')

    for item in items:
        if is_json:
            item['link'] = item.pop('url')
            item['pubdate'] = dateparser.parse(item.pop('date_new'))
            item_dict = item
            from seo.models import Company
            try:
                # The json feed provides company name, while the rss feed does
                # not; only try retrieving a company if we're pulling the
                # json feed
                company = Company.objects.get(name=item_dict['company'])
            except Company.DoesNotExist:
                pass
            else:
                if company.member:
                    # All companies have logos specified, but only members
                    # should have their logos shown
                    item_dict['company'] = company
        else:
            item_dict = {}
            item_dict['title'] = item.findChild('title').text
            item_dict['link'] = item.findChild('link').text
            item_dict['pubdate'] = dateparser.parse(
                item.findChild('pubdate').text)
            item_dict['description'] = item.findChild('description').text

        if ignore_dates or date_in_range(start, end,
                                         item_dict['pubdate'].date()):
            if ignore_dates and start <= item_dict['pubdate'].date():
                item_dict['new'] = True

            item_list.append(item_dict)

        if len(item_list) == return_items:
            break

    return item_list, len(item_list)


def date_in_range(start, end, x):
    return start <= x <= end


def url_sort_options(feed_url, sort_by, frequency=None, partner=False):
    """
    Updates urls based on sort by option. 

    Inputs:
    :feed_url:      URL of an RSS feed 
    :sort_by:       What the feed should be sorted by ('Relevance' or 'Date')
    :frequency:     Frequency of saved search ('D', 'W', 'M')
    :partner:       This is a partner saved search; don't add days_ago

    Output:
    :feed_url:      URL updated with sorting options. 'Date' has no additions to
                    the URL and  'Relevance' should has '&date_sort=False' added
    """

    # If unicode is present in the string, escape it
    feed = smart_str(feed_url)
    unparsed_feed = urlparse(feed)
    query = parse_qs(unparsed_feed.query)
    query.pop('date_sort', None)

    if sort_by == "Relevance":
        query.update({'date_sort': 'False'})

    if frequency and not partner:
        interval = -get_interval_from_frequency(frequency)
        query.update({'days_ago': interval})

    unparsed_feed = unparsed_feed._replace(query=urlencode(query, True))
    # Convert byte string back into unicode
    feed_url = smart_unicode(urlunparse(unparsed_feed))

    return feed_url


def get_interval_from_frequency(frequency):
    intervals = {'D': -1,
                 'W': -7,
                 'M': -30}
    return intervals.get(frequency, -1)
