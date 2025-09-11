from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('', include('portal.urls', namespace='portal')),  # Include portal URLs with namespace
    path('', RedirectView.as_view(pattern_name='portal:students', permanent=False)),
]