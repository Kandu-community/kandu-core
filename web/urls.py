from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required
# from django.contrib.admin.views.decorators import staff_member_required

from views import *

urlpatterns = patterns('',
    url(r'^registration/', UserRegistration.as_view(), name='web_user_registration'),
    (r'^login/', 'django.contrib.auth.views.login', {'template_name': 'web/login.html'}),
    (r'^logout/', 'django.contrib.auth.views.logout', {'next_page': '/web/'}),

    url(r'^update-migrate/$', ManageConfig.as_view(), name='web_config'),
    url(r'^update-migrate/(?P<operation>\w+)/$', ManageConfig.as_view(), name='web_config'),

    url(r'^map/$', login_required(MapView.as_view()), name='web_map'),

    url(r'^$', login_required(BaseFormList.as_view()), name='web_list'),
    url(r'^(?P<model_name>\w+)/$', login_required(FormList.as_view()), name='web_list'),
    url(r'^(?P<model_name>\w+)/create/', FormCreate.as_view(), name='web_create'),
    url(r'^(?P<model_name>\w+)/(?P<pk>\d+)/update/', FormUpdate.as_view(), name='web_update'),
    url(r'^(?P<model_name>\w+)/(?P<pk>\d+)/delete/', FormDelete.as_view(), name='web_delete'),
)