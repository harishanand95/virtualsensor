from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^read/$', views.read_from_file, name='read'),
    url(r'^read$', views.read_from_file, name='read'),
    url(r'^create$', views.create, name='create'),
    url(r'^create/$', views.create, name='create'),
    url(r'^$', views.index, name='index'),
]