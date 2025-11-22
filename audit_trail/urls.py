from django.urls import path
from . import views

app_name = 'audit_trail'

urlpatterns = [
    # Main dashboard
    path('', views.audit_dashboard, name='dashboard'),
    
    # Audit trail management
    path('list/', views.audit_list, name='list'),
    path('detail/<int:audit_id>/', views.audit_detail, name='detail'),
    path('statistics/', views.audit_statistics, name='statistics'),
    path('configuration/', views.audit_configuration, name='configuration'),
    
    # Export functionality
    path('export/csv/', views.export_audit_csv, name='export_csv'),
    
    # Alerts
    path('alerts/', views.audit_alerts, name='alerts'),
    path('alerts/resolve/<int:alert_id>/', views.resolve_alert, name='resolve_alert'),
    
    # API endpoints
    path('api/log/', views.audit_api_log, name='api_log'),
]