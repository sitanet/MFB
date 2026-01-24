from django.urls import path
from . import views

urlpatterns = [
    # Vendor Authentication URLs
    path('login/', views.vendor_login, name='vendor_login'),
    path('logout/', views.vendor_logout, name='vendor_logout'),
    path('dashboard/', views.vendor_dashboard, name='vendor_dashboard'),
    
    # Vendor User Management URLs
    path('vendor-users/', views.vendor_user_list, name='vendor_user_list'),
    path('vendor-users/create/', views.vendor_user_create, name='vendor_user_create'),
    path('vendor-users/<uuid:uuid>/edit/', views.vendor_user_edit, name='vendor_user_edit'),
    path('vendor-users/<uuid:uuid>/toggle-active/', views.vendor_user_toggle_active, name='vendor_user_toggle_active'),
    path('vendor-users/<uuid:uuid>/delete/', views.vendor_user_delete, name='vendor_user_delete'),
    
    # Client User Management URLs
    path('client-users/<int:user_id>/delete/', views.delete_client_user, name='delete_client_user'),
    
    # Company Management URLs (require vendor login)
    path('company_list/', views.company_list, name='company_list'),
    path('update_company/<uuid:uuid>/', views.update_company, name='update_company'),
    path('create_company/', views.create_company, name='create_company'),
    path('<uuid:uuid>/delete/', views.company_delete, name='company_delete'),
    path('<uuid:uuid>/', views.company_detail, name='company_detail'),
    
    # Branch Management URLs (require vendor login)
    path('branch_list/', views.branch_list, name='branch_list'),
    path('create_branch/', views.create_branch, name='create_branch'),
    path('branch/update/<uuid:uuid>/', views.update_branch, name='update_branch'),
    path('branches/delete/<uuid:uuid>/', views.branch_delete, name='branch_delete'),
    path('<uuid:uuid>/branch_detail/', views.branch_detail, name='branch_detail'),
    path('branch/<uuid:uuid>/create-admin/', views.create_branch_admin, name='create_branch_admin'),
    path('branch/<uuid:uuid>/edit-admin/', views.edit_branch_admin, name='edit_branch_admin'),
    path('branch/<uuid:uuid>/toggle-active/', views.toggle_branch_active, name='toggle_branch_active'),
    path('branch/<uuid:uuid>/renew/', views.renew_branch_expiration, name='renew_branch_expiration'),
    path('expired-branches/', views.expired_branches_list, name='expired_branches_list'),
    
    # Session Management (client-side, requires client login)
    path('company/session_mgt/', views.session_mgt, name='session_mgt'),
    path('session_mgt/<uuid:uuid>/update/', views.session_mgt, name='session_mgt'),
    path('session_mgt/<uuid:uuid>/pending-repayments/', views.get_pending_loan_repayments, name='get_pending_loan_repayments'),
    path('session_mgt/<uuid:uuid>/process-repayments/', views.process_loan_repayments, name='process_loan_repayments'),
    
    # Other URLs
    path('users/', views.display_users_and_branches, name='display_users_and_branches'),
    path('verify-phone/', views.verify_phone, name='verify_phone'),
    path('sms-webhook/', views.sms_delivery_webhook, name='sms_webhook'),
    path('sms-troubleshoot/', views.sms_troubleshoot, name='sms_troubleshoot'),
    path('resend_otp_branch/', views.resend_otp_branch, name='resend_otp_branch'),
    
    # Branch Superuser Management (Vendor)
    path('branch-superusers/', views.branch_superuser_list, name='branch_superuser_list'),
    path('branch-superusers/<uuid:uuid>/', views.branch_superuser_detail, name='branch_superuser_detail'),
    path('branch-superusers/<uuid:branch_uuid>/user/<uuid:user_uuid>/edit/', views.branch_superuser_edit, name='branch_superuser_edit'),
    path('branch-superusers/<uuid:branch_uuid>/user/<uuid:user_uuid>/toggle/', views.branch_superuser_toggle, name='branch_superuser_toggle'),
]
