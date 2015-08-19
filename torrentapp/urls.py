from django.conf.urls import include, url
from django.contrib import admin

from torrentapp import views

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', views.index),
]
