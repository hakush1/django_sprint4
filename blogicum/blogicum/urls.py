"""blogicum URL Configuration."""
from django.conf import settings
from django.contrib import admin
from django.conf.urls.static import static
from django.urls import include, path

from blog.views import RegistrationView

handler404 = 'pages.views.page_not_found'
handler500 = 'pages.views.server_error'


urlpatterns = [
    path('admin/', admin.site.urls),
    path(
        'auth/registration/',
        RegistrationView.as_view(),
        name='registration',
    ),
    path('auth/', include('django.contrib.auth.urls')),
    path('', include('blog.urls')),
    path('pages/', include('pages.urls')),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
