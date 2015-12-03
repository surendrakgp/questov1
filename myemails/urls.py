from django.conf.urls import patterns, url

urlpatterns = patterns(
    'myemails.views',
    url(r'^get-fields/$', 'get_fields', name='get_fields'),
)
