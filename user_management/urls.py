from django.urls import path
from . import views

app_name = 'user_management'

urlpatterns = [
    # User Management
    path('users/', views.all_users, name='all_users'),
    path('users/add/', views.add_user, name='add_user'),
    path('users/<int:user_id>/', views.view_user, name='view_user'),
    path('users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    
    # Roles & Permissions
    path('roles-permissions/', views.roles_permissions, name='roles_permissions'),
]