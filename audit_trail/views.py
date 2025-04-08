from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from .models import AuditLog
from .utils import user_can_view_audit_logs, user_can_delete_audit_logs, user_can_export_audit_logs
import csv
from django.http import HttpResponse

class AuditLogBaseView(LoginRequiredMixin):
    """Base view with common audit log functionality"""
    
    def dispatch(self, request, *args, **kwargs):
        if not user_can_view_audit_logs(request.user):
            raise PermissionDenied("You don't have permission to view audit logs")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        """Base queryset with select_related optimizations"""
        return AuditLog.objects.select_related('user', 'content_type')

class AuditLogListView(AuditLogBaseView, ListView):
    model = AuditLog
    template_name = 'audit_trail/log_list.html'
    context_object_name = 'logs'
    paginate_by = 50
    ordering = ['-timestamp']

    # Available date ranges
    DATE_RANGES = {
        'today': lambda: timezone.now().date(),
        'yesterday': lambda: timezone.now().date() - timedelta(days=1),
        'week': lambda: timezone.now().date() - timedelta(days=7),
        'month': lambda: timezone.now().date() - timedelta(days=30),
        'year': lambda: timezone.now().date() - timedelta(days=365),
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.GET
        
        # Apply date filter
        if date_range := params.get('date_range'):
            if date_range in self.DATE_RANGES:
                date_value = self.DATE_RANGES[date_range]()
                if date_range == 'today':
                    queryset = queryset.filter(timestamp__date=date_value)
                else:
                    queryset = queryset.filter(timestamp__date__gte=date_value)
        
        # Apply custom date range
        if start_date := params.get('start_date'):
            queryset = queryset.filter(timestamp__date__gte=start_date)
        if end_date := params.get('end_date'):
            queryset = queryset.filter(timestamp__date__lte=end_date)
        
        # Apply action filter
        if action := params.get('action'):
            queryset = queryset.filter(action=action)
        
        # Apply user filter
        if user_id := params.get('user_id'):
            queryset = queryset.filter(user_id=user_id)
        
        # Apply role filter
        if role := params.get('role'):
            queryset = queryset.filter(user_role=role)
        
        # Apply branch filter
        if branch := params.get('branch'):
            queryset = queryset.filter(user_branch=branch)
        
        # Apply search
        if search := params.get('search'):
            queryset = queryset.filter(
                Q(user__username__icontains=search) |
                Q(message__icontains=search) |
                Q(ip_address__icontains=search) |
                Q(object_id__icontains=search) |
                Q(user_role__icontains=search) |
                Q(user_branch__icontains=search)
            )
        
        return queryset.order_by('-timestamp')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        params = self.request.GET
        
        context.update({
            'date_range': params.get('date_range', ''),
            'start_date': params.get('start_date', ''),
            'end_date': params.get('end_date', ''),
            'action': params.get('action', ''),
            'user_id': params.get('user_id', ''),
            'role': params.get('role', ''),
            'branch': params.get('branch', ''),
            'search': params.get('search', ''),
            'date_ranges': list(self.DATE_RANGES.keys()),
            'action_choices': AuditLog.ACTION_CHOICES,
            'can_delete': user_can_delete_audit_logs(self.request.user),
            'can_export': user_can_export_audit_logs(self.request.user),
        })
        
        return context

class AuditLogDetailView(AuditLogBaseView, DetailView):
    model = AuditLog
    template_name = 'audit_trail/log_detail.html'
    context_object_name = 'log'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        log = self.object
        
        context.update({
            'can_delete': user_can_delete_audit_logs(self.request.user),
            'formatted_before': self.format_json(log.before),
            'formatted_after': self.format_json(log.after),
        })
        
        return context
    
    def format_json(self, data):
        """Format JSON data for display"""
        if not data:
            return None
        try:
            import json
            return json.dumps(data, indent=2, sort_keys=True)
        except:
            return str(data)

class AuditLogExportView(AuditLogBaseView):
    """View for exporting audit logs to CSV"""
    
    def dispatch(self, request, *args, **kwargs):
        if not user_can_export_audit_logs(request.user):
            raise PermissionDenied("You don't have permission to export audit logs")
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="audit_logs_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Timestamp', 'User', 'Role', 'Branch', 'Action', 
            'Object Type', 'Object ID', 'IP Address', 'Message'
        ])
        
        queryset = AuditLogListView.get_queryset(self)
        
        for log in queryset:
            writer.writerow([
                log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                log.user.username if log.user else 'System',
                log.user_role,
                log.user_branch,
                log.get_action_display(),
                log.content_type.model if log.content_type else '',
                log.object_id,
                log.ip_address,
                log.message,
            ])
        
        return response

class AuditLogDeleteView(AuditLogBaseView):
    """View for deleting audit logs"""
    
    def dispatch(self, request, *args, **kwargs):
        if not user_can_delete_audit_logs(request.user):
            raise PermissionDenied("You don't have permission to delete audit logs")
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        days = request.POST.get('days', 365)
        cutoff_date = timezone.now() - timedelta(days=int(days))
        
        deleted_count, _ = AuditLog.objects.filter(
            timestamp__lte=cutoff_date
        ).delete()
        
        # Add success message
        from django.contrib import messages
        messages.success(request, f"Successfully deleted {deleted_count} audit log entries older than {days} days")
        
        return redirect('audit_log_list')

def transaction_error_view(request):
    """View for displaying transaction errors"""
    if not request.user.has_perm('audit_trail.can_view_auditlog'):
        return render(request, 'audit_trail/permission_denied.html', status=403)
    return render(request, 'audit_trail/transaction_error.html', status=400)






from django.http import HttpResponse
import csv

def export_audit_logs(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="audit_logs.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Timestamp', 'User', 'Action', 'Object Type', 'Object ID', 'Message'])
    
    # Apply the same filters as your list view
    logs = AuditLog.objects.all()
    
    for log in logs:
        writer.writerow([
            log.timestamp,
            log.user.username if log.user else 'System',
            log.get_action_display(),
            log.content_type.model if log.content_type else '',
            log.object_id,
            log.message
        ])
    
    return response