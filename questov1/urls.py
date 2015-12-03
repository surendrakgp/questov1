"""questov1 URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include, url, patterns
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from registrations.forms import RegistrationForm
from django.views.generic import RedirectView

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    #url(r'^home/$', 'questov1.views.home', name='home'),
    #url(r'^home/$', 'questov1.views.home', name='login'),
    url(r'^contact/$', 'usermodel.views.contact', name='contact'),
    url(r'^contact-faq', 'usermodel.views.contact_faq', name='contact_faq'),
    url(r'^register/$', 'registrations.views.register', name = 'register'),
    url(r'^$','myprofile.views.home', name='home'),
    url(r'^basicinfo/$', 'myprofile.views.basicinfo', name='basicinfo'),
    url(r'^experience/$', 'myprofile.views.experience', name='experience'),
    url(r'^education/$', 'myprofile.views.education', name='education'),
    url(r'^social/$', 'myprofile.views.social', name='social'),
    url(r'^skill/$', 'myprofile.views.skill', name='skill'),
    url(r'^register/$', 'registrations.views.register', name='register'),
    url(r'^register/profile/view/edit/$', RedirectView.as_view(url='/profile/view/edit?module=Basicinfo&id=new')),
    url(r'^activate/$', 'registrations.views.activate', name='activate'),
    # url(r'^login/$', 'mysignon.views.sso_authorize', name='sso_authorize'),
    url(r'^login/$','django.contrib.auth.views.login',{'extra_context':{'signupform':RegistrationForm}},name='login'),
    # url(r'^login/$','questov1.views.login',name='login'),
    url(r'^logout/$','django.contrib.auth.views.logout',{'next_page':'/'},name='logout'),


    # url(r'^talent/', include('mydashboard.urls')),
    url(r'^talent/all/$','myprofile.views.all_talent',name='all_talent'),
    url(r'^talent/(?P<slug>[\w-]+)/$','myprofile.views.view_talent',name='talent'),
    url(r'^profile/', include('myprofile.urls')),
    url(r'^saved-search/', include('mysearches.urls')),
    # url(r'^api/', include(v1_api.urls)),
    url(r'^authorize/', include('mysignon.urls')),
    # url(r'^message/', include('mymessages.urls')),
    # url(r'^prm/', include('mypartners.urls')),
    # url(r'^posting/', include('postajob.urls')),
    url(r'^reports/', include('myreports.urls')),
)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
