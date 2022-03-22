from django.conf.urls import include, url

from .views import NotifyView, ReturnView


event_patterns = [
    url(r'^pretix_firstcash/', include([
        url(r'^return/(?P<order>[^/]+)/(?P<hash>[^/]+)/(?P<payment>[^/]+)/$', ReturnView.as_view(), name='return'),
        url(r'^notify/(?P<order>[^/]+)/(?P<hash>[^/]+)/(?P<payment>[^/]+)/$', NotifyView.as_view(), name='notify'),
    ])),
]
