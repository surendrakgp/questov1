from django.conf.urls import patterns, url
from django.views.generic import RedirectView


urlpatterns = patterns('mydashboard.views',
    #url(r'^$', RedirectView.as_view(url='/candidates/view/')),
    #url(r'^view/$', 'dashboard', name='dashboard'),
    #url(r'^view$', 'dashboard', name='dashboard'),
    url(r'^view/details$', 'talent_information',
        name='talent_information'),
    #url(r'^view/export$', 'export_candidates', name='export_candidates'),
)
