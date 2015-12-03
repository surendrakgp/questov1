import csv
import json
import operator
from datetime import datetime
from collections import Counter, OrderedDict
from itertools import groupby

from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.core import mail
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response


from universal.helpers import (get_company, get_domain, get_int_or_none,
                               sequence_to_dict)

from usermodel.models import User
from usermodel.decorators import user_is_allowed
from myprofile.models import ProfileUnits# , PrimaryNameProfileUnitManager 

from urlparse import urlparse

# Create your views here.


def talent_information(request):
    print user_is_allowed
    """
    Sends user info, primary name, and searches to talent_information.html.
    Gathers the employer's (request.user) companies and microsites and puts
    the microsites' domains in a list for further checking and logic,
    see helpers.py.

    """
    
    user_id = get_int_or_none(request.REQUEST.get('user'))
    print user_id

    
    try:
        talent = User.objects.get(id=user_id)
    except User.DoesNotExist:
        raise Http404

    
    manager = PrimaryNameProfileUnitManager(order=['basicinfo',
                                                    'experience',
                                                    'education',
                                                    'skill'
                                                    'social'])
    print type(talent)
    models = manager.displayed_units(talent.profileunits_set.all())


    
    data_dict = {
        'user_info': models,

    }
    print data_dict
    return render_to_response('mydashboard/talent_information.html',
                              data_dict, RequestContext(request))


