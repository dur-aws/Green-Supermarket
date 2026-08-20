from django.urls import path

from .views import (
    UserLoginView, UserLogoutView, UserProfileView,
    AdminUserListView, AdminUserDetailView, AdminUserCreateView,
    AdminUserUpdateView, AdminUserDeleteView, AdminUserPasswordResetView, manage_role_permissions
)


urlpatterns = [
    # Authentication
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('profile/', UserProfileView.as_view(), name='user_profile'),

    # Admin User Management
    path('', AdminUserListView.as_view(), name='user_list'),
    path('add/', AdminUserCreateView.as_view(), name='user_create'),
    path('<int:user_id>/', AdminUserDetailView.as_view(), name='user_detail'),
    path('<int:user_id>/edit/', AdminUserUpdateView.as_view(), name='user_edit'),
    path('<int:user_id>/delete/', AdminUserDeleteView.as_view(), name='user_delete'),
    path('<int:user_id>/reset-password/', AdminUserPasswordResetView.as_view(), name='admin_user_password_reset'),
    path('roles/<int:role_id>/permissions/', manage_role_permissions, name='manage_role_permissions'),
]

