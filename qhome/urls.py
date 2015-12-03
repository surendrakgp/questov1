from django.conf.urls import include, url, patterns
from django.contrib import admin
from django.conf import settings

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'questov1.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^login/$','django.contrib.auth.views.login',name='login'),
    url(r'^logout/$','django.contrib.auth.views.logout',{'next_page':'/'},name='logout'),
)
