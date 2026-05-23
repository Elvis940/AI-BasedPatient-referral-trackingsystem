from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('adminapp.urls')),  # This makes home page the first page
    path('user-management/', include('user_management.urls')),
    path('chw/', include('chw.urls')),
    path('doctor/', include('doctor.urls')),
    path('patients/', include('patients.urls')),
    path('ai/', include('ai_assessment.urls')),
    path('referrals/', include('referrals.urls')),
    
    # Single logout URL - using Django's built-in LogoutView
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)