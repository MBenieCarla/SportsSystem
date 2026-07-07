from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    # Dashboard
    path('', views.AdminDashboardView.as_view(), name='dashboard'),
    
    # User management
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/<int:user_id>/detail/', views.UserDetailView.as_view(), name='user_detail'),
    path('users/<int:user_id>/deactivate/', views.UserDeactivateView.as_view(), name='user_deactivate'),
    path('users/<int:user_id>/reactivate/', views.UserReactivateView.as_view(), name='user_reactivate'),
    path('users/<int:user_id>/assign-role/', views.UserRoleAssignView.as_view(), name='user_assign_role'),
    
    # Role management
    path('roles/', views.RoleListView.as_view(), name='role_list'),
    path('roles/create/', views.RoleCreateView.as_view(), name='role_create'),
    path('roles/<int:group_id>/', views.RolePermissionUpdateView.as_view(), name='role_update'),
    path('roles/<int:group_id>/delete/', views.RoleDeleteView.as_view(), name='role_delete'),
    
    # Profile moderation
    path('moderate/<int:user_id>/', views.ProfileModerateView.as_view(), name='moderate_profile'),
    
    # Audit log
    path('audit-log/', views.AuditLogView.as_view(), name='audit_log'),
]