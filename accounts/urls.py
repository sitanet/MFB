from django.urls import path
from . import views



urlpatterns = [
   
    path('myAccount/', views.myAccount, name='myAccount'),
    path('registeruser/', views.registeruser, name='registeruser'),
    path('registerusermasterintelligent/', views.registerusermasterintelligent, name='registerusermasterintelligent'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard_2/', views.dashboard_2, name='dashboard_2'),
    path('dashboard_3/', views.dashboard_3, name='dashboard_3'),
    path('dashboard_4/', views.dashboard_4, name='dashboard_4'),
    path('dashboard_5/', views.dashboard_5, name='dashboard_5'),
    path('dashboard_6/', views.dashboard_6, name='dashboard_6'),
    path('dashboard_7/', views.dashboard_7, name='dashboard_7'),
    path('dashboard_8/', views.dashboard_8, name='dashboard_8'),
    path('dashboard_9/', views.dashboard_9, name='dashboard_9'),
    path('dashboard_10/', views.dashboard_10, name='dashboard_10'),
    path('dashboard_11/', views.dashboard_11, name='dashboard_11'),
    path('dashboard_12/', views.dashboard_12, name='dashboard_12'),
    path('customer_dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('profile/', views.profile, name='profile'),
    path('change_password/', views.change_password, name='change_password'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout, name='logout'),
    path('verify_otp/', views.verify_otp, name='verify_otp'),

    path('resend_otp/', views.resend_otp, name='resend_otp'),
   
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    path('forgot_password/', views.forgot_password, name='forgot_password'),
    path('reset_password_validate/<uidb64>/<token>/', views.reset_password_validate, name='reset_password_validate'),
    path('reset_password/', views.reset_password, name='reset_password'),
    path('change_password/', views.change_password, name='change_password'),
    path('user_admin/', views.user_admin, name='user_admin'),
    path('display_all_user/', views.display_all_user, name='display_all_user'),
    path('edit_user/<uuid:uuid>/', views.edit_user, name='edit_user'),
    path('delete_user/<uuid:uuid>/', views.delete_user, name='delete_user'),
    path('verify_user/<uuid:uuid>/', views.verify_user, name='verify_user'),


    path('register/', views.register, name='register'),
    path('user_verify_otp/', views.user_verify_otp, name='user_verify_otp'),
    path('user_resend_otp/', views.user_resend_otp, name='user_resend_otp'),
    path('contact-support/', views.contact_support, name='contact_support'),

    path('auto-logout/', views.auto_logout_settings, name='auto_logout_settings'),
    
    # Role Permission Management
    path('manage_permissions/', views.manage_role_permissions, name='manage_role_permissions'),
    path('view_role_permissions/', views.view_role_permissions, name='view_role_permissions'),
]