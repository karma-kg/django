from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'karma.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', 'karma_app.views.index'), # root
    url(r'^login$', 'karma_app.views.login_view'), # login
    url(r'^logout$', 'karma_app.views.logout_view'), # logout
    url(r'^signup$', 'karma_app.views.signup'), # signup
)
