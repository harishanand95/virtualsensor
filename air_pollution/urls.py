from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^read/$', views.read_from_file, name='read'),
    url(r'^read$', views.read_from_file, name='read'),
    url(r'^create$', views.create, name='create'),
    url(r'^create/$', views.create, name='create'),
    url(r'^streetlight$', views.streetlight, name='streetlight'),
    url(r'^streetlight/$', views.streetlight, name='streetlight'),
    url(r'^signin$', views.signin, name='signin'),
    url(r'^signin/$', views.signin, name='signin'),
    url(r'^$', views.index, name='index'),
]