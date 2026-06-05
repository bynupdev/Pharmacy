# from django.urls import path
# from . import views

# app_name = 'accounts'

# urlpatterns = [
#     path('', views.landing_page, name='landing_page'),
#     # Authentication
#     path('login/', views.login_view, name='login'),
#     path('logout/', views.logout_view, name='logout'),
#     path('register/', views.register, name='register'),


    
#     # Password Reset
#     path('password-reset/', views.password_reset_request, name='password_reset'),
#     path('password-reset/<str:token>/', views.password_reset_confirm, name='password_reset_confirm'),
    
#     # Profile Management
#     path('profile/', views.profile, name='profile'),
#     path('change-password/', views.change_password, name='change_password'),
    
#     # User Management (Admin only)
#     path('users/', views.user_list, name='user_list'),
#     path('users/create/', views.user_create, name='user_create'),
#     path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
#     path('users/<int:pk>/toggle/', views.user_toggle_active, name='user_toggle'),
#     path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
#     path('manage-users/', views.manage_users, name='manage_users'),
    
#     # API endpoints
#     path('api/check-username/', views.api_check_username, name='api_check_username'),
#     path('api/check-email/', views.api_check_email, name='api_check_email'),
# ]



from django.urls import path
from . import views

def root_view(request):
    """Show landing page for non-authenticated users, dashboard for authenticated"""
    if request.user.is_authenticated:
        return views.dashboard_router(request)
    return views.landing_page(request)

app_name = 'accounts'

urlpatterns = [
    # path('', views.landing_page, name='landing_page'),
    path('', root_view, name='home'),
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    
    # API endpoints for real-time validation
    path('api/check-pharmacy/', views.check_pharmacy_exists, name='check_pharmacy'),
    path('api/check-email/', views.check_email_exists, name='check_email'),
    
    # Admin dashboards and management
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('approve/<int:request_id>/', views.approve_user, name='approve_user'),
    path('reject/<int:request_id>/', views.reject_user, name='reject_user'),
    path('manage-users/', views.manage_users, name='manage_users'),
    
    # Role dashboards
    path('pharmacist-dashboard/', views.pharmacist_dashboard, name='pharmacist_dashboard'),
    path('technician-dashboard/', views.technician_dashboard, name='technician_dashboard'),
    
    # Profile
    path('profile/', views.profile, name='profile'),
    path('change-password/', views.change_password, name='change_password'),

        # Password Reset
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/<str:token>/', views.password_reset_confirm, name='password_reset_confirm'),
    

]