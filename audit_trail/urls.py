from django.urls import path
from . import views 
from .views import (
    AuditLogListView,
    AuditLogDetailView,
    transaction_error_view 

)


urlpatterns = [
    path('logs/', AuditLogListView.as_view(), name='audit_log_list'),
    path('logs/<int:pk>/', AuditLogDetailView.as_view(), name='audit_log_detail'),
    path('transaction-error/', transaction_error_view, name='transaction_error'),
    path('audit-logs/export/', views.export_audit_logs, name='export_audit_logs'),
 
]