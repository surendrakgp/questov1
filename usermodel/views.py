import base64
import datetime
import json
import logging
import urllib2
from urlparse import urlparse
import uuid

from django.conf import settings
from django.contrib.auth import logout, authenticate
from django.contrib.auth.decorators import user_passes_test
from django.db import IntegrityError
from django.forms import Form, model_to_dict
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, redirect, render, Http404
from django.template import RequestContext
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView

from captcha.fields import ReCaptchaField

#from universal.helpers import get_domain
#from myjobs.decorators import user_is_allowed
#from myjobs.forms import ChangePasswordForm, EditCommunicationForm
#from myjobs.helpers import expire_login, log_to_jira, get_title_template
from usermodel.models import Ticket, User, FAQ, CustomHomepage
#from myprofile.forms import (InitialNameForm, InitialEducationForm,
#                             InitialAddressForm, InitialPhoneForm,
#                             InitialWorkForm)
#from myprofile.models import ProfileUnits, Name
#from registration.forms import RegistrationForm, CustomAuthForm
#from tasks import process_sendgrid_event

logger = logging.getLogger('__name__')


def contact_faq(request):
    """
    Grabs FAQ and orders them by alphabetical order on question.

    """
    faq = FAQ.objects.filter(is_visible=True).order_by('question')
    if not faq.count() > 0:
        return HttpResponseRedirect(reverse('contact'))
    data_dict = {'faq': faq}
    return render_to_response('contact-faq.html', data_dict, RequestContext(request))

def contact(request):
    #print form.is_valid()
    if request.POST:
        print type(request.POST)
        name = request.POST.get('name')
        contact_type = request.POST.get('type')
        reason = request.POST.get('reason')
        from_email = request.POST.get('email')
        phone_num = request.POST.get('phone')
        comment = request.POST.get('comment')
        form = CaptchaForm(request.POST)
        if form.is_valid():
            components = []
            component_ids = {'My.jobs Error': {'id': '12903'},
                             'Job Seeker': {'id': '12902'},
                             'Employer': {'id': '12900'},
                             'Partner': {'id': '12901'},
                             'Request Demo': {'id': '13900'}}
            if component_ids.get(reason):
                components.append(component_ids.get(reason))
            components.append(component_ids.get(contact_type))
            issue_dict = {
                'summary': '%s - %s' % (reason, from_email),
                'description': '%s' % comment,
                'issuetype': {'name': 'Task'},
                'customfield_10400': str(name),
                'customfield_10401': str(from_email),
                'customfield_10402': str(phone_num),
                'components': components}

            subject = 'Contact My.jobs by a(n) %s' % contact_type
            body = """
                   Name: %s
                   Is a(n): %s
                   Email: %s

                   %s
                   """ % (name, contact_type, from_email, comment)

            to_jira = log_to_jira(subject, body, issue_dict, from_email)
            if to_jira:
                time = datetime.datetime.now().strftime(
                    '%A, %B %d, %Y %l:%M %p')
                return HttpResponse(json.dumps({'validation': 'success',
                                                'name': name,
                                                'c_type': contact_type,
                                                'reason': reason,
                                                'c_email': from_email,
                                                'phone': phone_num,
                                                'comment': comment,
                                                'c_time': time}))
            else:
                return HttpResponse('success')
        else:
            return HttpResponse(json.dumps({'validation': 'failed',
                                            'errors': form.errors.items()}))
    else:
        #form = CaptchaForm()
        data_dict = {}
    return render_to_response('contact.html', data_dict,
                              RequestContext(request))
