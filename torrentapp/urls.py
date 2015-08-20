from django.conf.urls import include, url
from django.contrib import admin

from torrentapp import views, tracker

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', views.index),
    url(r'^log$', views.log),
    url(r'^users/$', views.redirect_to_front),
    url(r'^accounts/profile/$', views.redirect_to_front),
    url(r'^tracker/(.+)/announce$', tracker.announce),
    url(r'^(.+).torrent$', views.torrent),
    url(r'^accounts/', include('registration.backends.simple.urls')),

    url(r'^api/push_log$', views.push_log),
    url(r'^api/torrent_data$', views.torrent_data),
]
