import re
import json
from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse,HttpResponseRedirect, QueryDict
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render,get_object_or_404, render_to_response, RequestContext
from django.core.urlresolvers import reverse


# Create your views here.
# from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction

from questov1.decorators import user_is_allowed
from usermodel.models import User
from myprofile.models import ProfileUnits, BaseProfileUnitManager
from myprofile import forms
# Create your views here.
from collections import OrderedDict
from .models import Basicinfo, Experience, Education, Social, Skill, ProfileUnits, get_next_or_prev
from .forms import BasicinfoForm, ExperienceForm, EducationForm, SocialForm, SkillForm
from registrations.forms import RegistrationForm


def home(request):
    user=request.user
    
    company_size = request.REQUEST.get('size')
    if company_size:
        company = GeneralInformation.objects.filter(company_size=company_size)
    u=[]
    
    
    
    data_dict = {
            'view_name': 'Home',
            'signupform' : RegistrationForm,
            
            
            }
    return render_to_response("home.html",data_dict,RequestContext(request))

@user_passes_test(User.objects.not_disabled)
def delete_item(request):
    item_id = request.REQUEST.get('item')
    try:
        request.user.profileunits_set.get(id=item_id).delete()
    except ProfileUnits.DoesNotExist:
        pass
    return HttpResponseRedirect(reverse('view_profile'))

@user_is_allowed()
@user_passes_test(User.objects.not_disabled)
def edit_profile(request):
    """
    Main profile view that the user first sees. Ultimately generates the
    following in data_dict:

    :profile_config:    A dictionary of profile units
    :empty_display_names: A list of ProfileUnits that hasn't been made
    """

    user = request.user

    user.update_profile_completion()

    manager = BaseProfileUnitManager(order=['social','basicinfo','skill','experience','education'])
    

    profile_config = manager.displayed_units(user.profileunits_set.all())
    empty_units = [model for model in ProfileUnits.__subclasses__()]

    for units in profile_config.iteritems():
        if units[0].__class__ in empty_units:
            del empty_units[empty_units.index(units[0].__class__)]

    
    empty_names = [model.get_verbose_class() for model in empty_units]
    empty_display_names = []
    for name in empty_names:
        name_with_space = re.sub(r"(\w)([A-Z])", r"\1 \2", name)
        empty_display_names.append(name_with_space)

    data_dict = {'profile_config': profile_config,
                 'unit_names': empty_display_names,
                 'user': user,
                 'view_name': 'My Profile',
                 'can_edit':True,
                 }

    return render_to_response('myprofile/edit_profile.html', data_dict,
                              RequestContext(request))


@user_passes_test(User.objects.not_disabled)
def handle_form(request):
    """
    Handles the user submitting changes to their user profile.

    The form expects a 'module' GET parameter and an optional 'item_id'.  It
    then uses these to update the existing item or create a new instance
    """
    item_id = request.REQUEST.get('id', 'new')
    module = request.REQUEST.get('module')
    module = module.replace(" ", "")

    if module == 'Basicinfo':
        user = request.user
        try:
            key = list(ProfileUnits.objects.filter(user_id=user.id))
            BI = Basicinfo.objects.get(profileunits_ptr_id__in = key)
            item_id = BI.id
        except:
            item_id = 'new'

    item = None
    if item_id != 'new':
        try:
            item = request.user.profileunits_set.get(pk=item_id)
            item = getattr(item, module.lower())
        except ProfileUnits.DoesNotExist:
            # User is trying to access a nonexistent PU
            # or a PU that belongs to someone else
            raise Http404

    item_class = item.__class__

    try:
        form = getattr(forms, module + 'Form')
    except KeyError:
        # Someone must have manipulated request data?
        raise Http404

    data_dict = {'view_name': 'My Profile',
                 'item_id': item_id,
                 'module': module}

    if request.method == 'POST':
        # if request.POST.get('action') == 'updateEmail':
        #     activation = ActivationProfile.objects.get_or_create(user=request.user,
        #                                                          email=item.email)[0]
        #     activation.send_activation_email(primary=False)
        #     return HttpResponse('success')

        if item_id == 'new':
            form_instance = form(user=request.user, data=request.POST, auto_id=False, files=request.FILES)
        else:
            form_instance = form(user=request.user, instance=item, auto_id=False, data=request.POST, files=request.FILES)
        model = form_instance._meta.model
        data_dict['form'] = form_instance
        data_dict['verbose'] = model._meta.verbose_name.title()

        model_name = model._meta.verbose_name.lower()
        if form_instance.is_valid():
            instance = form_instance.save()
            if request.is_ajax():
                suggestions = ProfileUnits.suggestions(request.user)
                return render_to_response('myprofile/suggestions.html',
                                          {'suggestions': suggestions[:3],
                                           'model_name': model_name,
                                           'module': {'item': instance}},
                                          RequestContext(request))
            else:
                return HttpResponseRedirect(reverse('view_profile'))
        else:
            if request.is_ajax():
                return HttpResponse(json.dumps(form_instance.errors), status=400)
            else:
                return render_to_response('myprofile/profile_form.html',
                                          data_dict,
                                          RequestContext(request))
    else:
        # if module == 'Basicinfo':
        #     user = request.user
        #     key = ProfileUnits.objects.filter(user_id=user.id)
        #     try:
        #         a = key.get(content_type = 14)
        #         item_id = a.id
        #     except:
        #         item_id = 'new'

        if item_id == 'new':
            form_instance = form(user=request.user, auto_id=False)
        else:
            form_instance = form(instance=item, auto_id=False)
            # if data_dict['module'] == 'SecondaryEmail':
            #     data_dict['verified'] = item.verified
        model = form_instance._meta.model
        data_dict['form'] = form_instance
        data_dict['verbose'] = model._meta.verbose_name.title()

        return render_to_response('myprofile/profile_form.html',
                                  data_dict,
                                  RequestContext(request))

    return render_to_response('myprofile/profile_form.html',
                                  data_dict,
                                  RequestContext(request))


@user_passes_test(User.objects.not_disabled)
def get_details(request):
    module_config = {}
    item_id = request.GET.get('id')
    module = request.GET.get('module')
    module = module.replace(" ", "")
    item = get_object_or_404(request.user.profileunits_set,
                             pk=item_id)
    item = getattr(item, module.lower())
    model = item.__class__
    module_config['verbose'] = model._meta.verbose_name.title()
    module_config['name'] = module
    module_config['item'] = item
    data_dict = {'module': module_config}
    data_dict['view_name'] = 'My Profile'
    return render_to_response('myprofile/profile_details.html',
                              data_dict, RequestContext(request))


def view_talent(request,slug):
    # try:

    # if "next" in slug:
    #     the_user = request.REQUEST.get('user')
    #     user = User.objects.all()
    #     the_user = get_next_or_prev(user, the_user, 'next')

    User.objects.all().order_by('email')
    if "next" in slug or "prev" in slug:
        print slug
        the_user = request.REQUEST.get('user')
        user = User.objects.all()
        the_user = get_next_or_prev(user, the_user, slug)
    if "myprofile" in slug:
        the_user = request.user

    # elif "prev" in slug:
    #     the_user = request.REQUEST.get('user')
    #     user = User.objects.all()
    #     the_user = get_next_or_prev(user, the_user, slug)


    else:
        BI = Basicinfo.objects.get(slug=slug)
        PI = ProfileUnits.objects.get(id=BI.id)
        the_user = User.objects.get(id=PI.user_id)

        
    manager = BaseProfileUnitManager(order=['social','basicinfo','skill','experience','education'])

    print manager

    profile_config = manager.displayed_units(the_user.profileunits_set.all())

    empty_units = [model for model in ProfileUnits.__subclasses__()]
    
    for units in profile_config.iteritems():
        if units[0].__class__ in empty_units:
            del empty_units[empty_units.index(units[0].__class__)]

    
    empty_names = [model.get_verbose_class() for model in empty_units]
    empty_display_names = []
    for name in empty_names:
        name_with_space = re.sub(r"(\w)([A-Z])", r"\1 \2", name)
        empty_display_names.append(name_with_space)
    
    user_skill = Skill.objects.filter(user=the_user)

    # user.is_authenticated = True

    data_dict = {'profile_config': profile_config,
                 'unit_names': empty_display_names,
                 'the_user': the_user,
                 'user': request.user,
                 'can_edit': False,
                 'view_name': 'Profile',
                 'user_skill':user_skill,
                  }

    return render_to_response('myprofile/edit_profile.html', data_dict,
                              RequestContext(request))

        #return HttpResponse(reverse("company"))
    # except:
    #     return HttpResponseRedirect(reverse("home"))
    # return HttpResponseRedirect(reverse("home"))


def all_talent(request):
    basicinfo = Basicinfo.objects.all()
    skill = Skill.objects.all().order_by('skillname')
    skill_list = list(skill.values_list('skillname',flat=True).distinct())
    located_at = request.REQUEST.get('location')
    if located_at:
        basicinfo = Basicinfo.objects.filter(located_at=located_at)

    skillname = request.REQUEST.get('skillname')
    u=[]
    if skillname:
        skl = Skill.objects.filter(skillname=skillname)
        for s in skl:
            u.append(s.user_id)
        basicinfo = Basicinfo.objects.filter(user_id__in=u)


    # min = request.REQUEST.get('min')
    # max = request.REQUEST.get('max')
    # u=[]
    # if skillname:
    #     skl = Skill.objects.filter(skillname=skillname)
    #     for s in skl:
    #         if s.rating>=min and s.rating<=max:
    #             u.append(s.user_id)
    #     # for index,i in enumerate(s):
    #     #     print (index,i)
    #     #     if i.rating >= min[index] and i.rating <= max[index]:
    #             u.append(s.user_id)
    #     basicinfo = basicinfo.filter(user_id__in=u)
        

    data_dict = {
                'view_name' : 'Talent Database',
                'info' : basicinfo,
                'skill_list' : skill_list,
                'skill':skill
            }
    return render_to_response("talent.html",data_dict,RequestContext(request))



@user_is_allowed
def basicinfo(request):
    user = request.user
    user.update_profile_completion()
    #item = request.user.profileunits_set.get(pk=item_id)
    #Using regular django forms
    #return render(request, 'basicinfo.html', {'form': BasicInfoForm()})
    basic_form = BasicinfoForm()
    if request.method == "POST":
        basic_form = BasicinfoForm(request.POST)
        if basic_form.is_valid():
            if not user.exist:
                basic_form = Basicinfo(**basic_form.cleaned_data).save()
                return HttpResponseRedirect('/experience')
            else:
                return HttpResponseRedirect('/profile/view/')
    return render_to_response('basic_info.html',{'form':basic_form}, context_instance=RequestContext(request))



@login_required()
def experience(request):
    experience_form = ExperienceForm()
    if request.method == "POST":
        experience_form = ExperienceForm(request.POST)
        if experience_form.is_valid():
            new_experience = Experience(**experience_form.cleaned_data)
            new_experience.save()
            return HttpResponseRedirect('/skill')
        else:
            experience_form = ExperienceInfoForm()
    return render_to_response('experience.html',{'form':experience_form}, context_instance=RequestContext(request))

@login_required()
def skill(request):
    skill_form = SkillForm()
    if request.method == "POST":
        skill_form = SkillForm(request.POST)
        if skill_form.is_valid():
            new_skill = Skill(**skill_form.cleaned_data)
            new_skill.save()
            return HttpResponseRedirect('/education')
        else:
            skill_form = SkillForm()
    return render_to_response('skill.html',{'form':skill_form}, context_instance=RequestContext(request))

@login_required()
def education(request):
    education_form = EducationForm()
    if request.method == "POST":
        education_form = EducationForm(request.POST)
        if education_form.is_valid():
            new_education = Education(**education_form.cleaned_data)
            new_education.save()
            return HttpResponseRedirect('/social')
        else:
            education_form = EducationForm()
    return render_to_response('education.html',{'form':education_form}, context_instance=RequestContext(request))

@login_required()
def social(request):
    social_form = SocialForm()
    if request.method == "POST":
        social_form = SocialForm(request.POST)
        if social_form.is_valid():
            new_social = Social(**social_form.cleaned_data)
            new_social.save()
            return HttpResponseRedirect('/home')
        else:
            social_form = SocialForm()
    return render_to_response('social.html',{'form':social_form}, context_instance=RequestContext(request))


