import pysolr

from copy import deepcopy
from django.conf import settings
from django.core import mail


class Solr(object):
    def __init__(self, solr_location=None):
        if hasattr(mail, 'outbox'):
            solr_location = settings.TEST_SOLR_INSTANCE['current']
        elif not solr_location:
            solr_location = settings.SOLR['all']
        self.location = solr_location
        self.solr = pysolr.Solr(self.location)
        self.q = '*:*'
        self.params = {
            'fq': [],
            'fl': [],
            'start': 0,
            'rows': 10,
            'sort': '',
            'wt': 'json',
            'facet': 'false',
            'facet.field': [],
            'facet.query': [],
            'facet.mincount': 1,
            'facet.limit': -1,
        }

    def _clone(self):
        clone = Solr(self.location)
        clone.q = deepcopy(self.q)
        clone.params = deepcopy(self.params)
        return clone

    def add_join(self, from_field, to_field, search_terms='*:*'):
        """
        Adds a join to the query. Because the join needs to come first in the
        query, this overwrites any existing part of the query.

        inputs:
        :from_field: The field that is being joined from. Any additional
            search terms for these documents must be applied to the 'q'
            parameter.
        :to_field: The field that is being joined to. Any search terms for
            these documents must come from the 'fq' parameter. The resulting
            documents and any facets will come from the documents selected
            by this field.
        :search terms: Any initial search terms to apply to the query.

        """
        solr = self._clone()
        solr.q = "{!join from=%s to=%s}%s" % (from_field, to_field,
                                              search_terms)
        return solr

    def add_query(self, query_string, bool_operator='AND'):
        """
        Adds the query_string to the query. If the query already exists, adds
        the new query string to the existing query seperated by bool_operator.

        inputs:
        :query_string: The query string to be added.
        :bool_operator: The operator separating query strings. Only used if
            query strings are added multiple times.

        """
        solr = self._clone()
        solr.q = "%s %s (%s)" % (solr.q, bool_operator, query_string)
        return solr

    def add_filter_query(self, query_string):
        """
        Adds a filter query.

        inputs:
        :query_string: The filter query to be added.

        """
        solr = self._clone()
        solr.params['fq'].append(query_string)
        return solr

    def add_return_field(self, field, alias=None):
        """
        Adds a field to be returned with results. Leave blank to return all
        fields.

        inputs:
        :field: The field to be returned with the results. Can be a
            solr-supported function.
        :alias: The name the field name that the requested field is rerturned
            as.

        """
        solr = self._clone()
        if not alias:
            solr.params['fl'].append(field)
        else:
            solr.params['fl'].append("%s:%s" % (alias, field))
        return solr

    def result_start_row(self, start):
        """
        Sets the starting row for result retrieval.

        """
        solr = self._clone()
        solr.params['start'] = start
        return solr

    def rows_to_fetch(self, rows):
        """
        Sets the total number of rows to fetch.

        """
        solr = self._clone()
        solr.params['rows'] = rows
        return solr

    def add_facet_field(self, field):
        """
        Adds a field to facet on.

        """
        solr = self._clone()
        solr.params['facet'] = 'true'
        solr.params['facet.field'].append(field)
        return solr

    def add_facet_query(self, query_string):
        """
        Adds a query to facet on.

        """
        solr = self._clone()
        solr.params['facet'] = 'true'
        solr.params['facet.field'].append(query_string)
        return solr

    def add_facet_prefix(self, prefix, fieldname=None):
        """
        Adds a facet prefix. This applies to all facets, so it should only be
        set when only one field is being faceted on.

        """
        key = "f.%s.facet.prefix" % fieldname if fieldname else 'facet.prefix'

        solr = self._clone()
        solr.params[key] = prefix
        return solr

    def sort(self, sort_field, order='desc'):
        solr = self._clone()
        query = '{sort_field} {order}'
        solr.params['sort'] = query.format(sort_field=sort_field, order=order)
        return solr

    def reset(self):
        """
        Resets all of the fields to their defaults.

        """
        solr = self._clone()
        solr.q = '*:*'
        solr.params = {
            'fq': [],
            'start': 0,
            'rows': 10,
            'sort': '',
            'wt': 'json',
            'facet': 'false',
            'facet.field': [],
            'facet.query': [],
        }
        return solr

    def search(self, **kwargs):
        """
        Searches solr with given q and kwargs.

        """
        clone = self._clone()

        if 'q' in kwargs:
            clone.q = kwargs['q']
            del kwargs['q']
        clone.params.update(kwargs)

        return clone.solr.search(q=clone.q, **clone.params)

    def delete(self):
        """
        Deletes all documents matching the current q.

        """
        self.solr.delete(q=self.q)


def format_date(date, time_format="23:59:59Z"):
    """
    Switches dates to the solr format, ignoring time zones because the pysolr
    upload does the same.

    inputs:
    :date: The datetime object to be solr formatted.

    outputs:
    A date formated YYYY-mm-ddThh:mm:ssZ, e.g. 2013-08-14T20:03:12Z
    """
    date_format = "%Y-%m-%dT{time}".format(time=time_format)
    return date.strftime(date_format)


def dict_to_object(results):
    objs = []
    for x in results:
        objs.append(type('SearchResult', (object, ), x))
    return objs


# def is_bot(ua):
#     """
#     Determines if the provided user agent is likely to be a bot

#     Inputs:
#     :ua: User Agent string

#     Outputs:
#     :bot: Is :ua: likely to be a bot
#     """
#     ua = ua.lower()
#     bot = False
#     for bot_ua in settings.BOTS:
#         if bot_ua in ua or ua in ['', '-']:
#             bot = True
#             break
#     return bot
