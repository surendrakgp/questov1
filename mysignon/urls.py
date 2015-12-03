from django.conf.urls import patterns, url


urlpatterns = patterns('mysignon.views',
    url(r'^login$', 'sso_authorize', name='sso_authorize'),
)
