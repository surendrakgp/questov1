from django.shortcuts import render

# Create your views here.
import datetime
import json

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.contrib.auth import logout as log_out
from django.contrib.auth.views import password_reset
from django.contrib.auth.decorators import user_passes_test
from django.http import Http404, HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
from django.template.response import TemplateResponse
from django.views.generic import TemplateView
from django.contrib.auth.forms import AuthenticationForm
from registrations.models import ActivationProfile
from registrations.forms import RegistrationForm
from usermodel.decorators import user_is_allowed
from myprofile.forms import *
from usermodel.models import User

def register(request):
    """
    Registration form. Creates inactive user (which in turn sends an activation
    email) and redirect to registration complete page.

    """
    signupform = RegistrationForm()
    if request.method == "POST":
        signupform = RegistrationForm(request.POST)
        if signupform.is_valid():
            new_user = User.objects.create_user(request=request,
                                                **signupform.cleaned_data)
            email = signupform.cleaned_data['email']
            password = signupform.cleaned_data['password1']
            new_user = User.objects.create_user(request=request,**signupform.cleaned_data)
            new_user = authenticate(email=email, password=password)
            login(request, new_user)
            user_is_allowed = True
            #expire_login(request, user)
            return HttpResponseRedirect('/profile/view/edit?module=Basicinfo&id=new')

        else:
            context = {
                'form':AuthenticationForm(),
                'signupform':signupform,
            }
            return TemplateResponse(request,'registration/login.html',context)
    else:
        form = AuthenticationForm()
        return render_to_response('registration/login.html', {'form':form,'signupform':signupform}, context_instance=RequestContext(request))
        #return HttpResponse(json.dumps({'errors': form.errors.items()}))

@user_is_allowed()
def activate(request, 
            # activation_key,invitation=False
             ):
    """
    Activates user and returns a boolean to activated. Activated is passed
    into the template to display an appropriate message if the activation
    passes or fails.

    Inputs:
    :activation_key: string representing an activation key for a user
    """
    logged_in = True
    if request.user.is_anonymous():
        logged_in = False
    #activated = ActivationProfile.objects.activate_user(activation_key)



    ctx = {
            'Registration' : RegistrationForm,
            'BasicinfoForm': BasicinfoForm,
            'ExperienceForm': ExperienceForm,
            'EducationForm': EducationForm,
            'SkillForm': SkillForm,
            'SclForm': SclForm,
            'num_modules': len(settings.PROFILE_COMPLETION_MODULES)
            }

    # if invitation:
    #     if activated is False and not request.user.is_anonymous():
    #         activated = request.user
    #         ctx['activated'] = activated

    #     if activated is not False:
    #         if activated.in_reserve:
    #             activated.in_reserve = False
    #             password = User.objects.make_random_password()
    #             activated.set_password(password)
    #             # Without this, user isn't prompted for a new password when
    #             # invited to use My.jobs. See PD-1444
    #             activated._User__original_password = activated.password
    #             activated.save()
    #             ctx['password'] = password
    template = 'registration.html'
    return render_to_response(template, ctx,
                              context_instance=RequestContext(request))
