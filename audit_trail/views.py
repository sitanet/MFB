from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
from django.views.decorators.csrf import csrf_exempt
import json
import csv
from .models import AuditTrail, AuditConfiguration, AuditAlert, AuditStatistics, AuditAction, AuditCategory
from .utils import format_currency, create_audit_log
from accounts.utils import get_company_branch_ids_all

@login_required
def audit_dashboard(request):
    """Main audit trail dashboard - filtered by user's company (all branches)"""
    
    # Get all branch IDs belonging to user's company
    company_branch_ids = get_company_branch_ids_all(request.user)
    
    # Get recent audit trails (last 50) - filtered by company branches
    recent_audits = AuditTrail.objects.select_related('user').filter(
        branch_id__in=company_branch_ids
    ).order_by('-timestamp')[:50]
    
    # Get statistics for today - filtered by company branches
    today = timezone.now().date()
    today_stats = AuditTrail.objects.filter(timestamp__date=today, branch_id__in=company_branch_ids)
    
    stats = {
        'today_total': today_stats.count(),
        'today_users': today_stats.values('user').distinct().count(),
        'today_failed': today_stats.filter(success=False).count(),
        'today_transactions': today_stats.filter(category=AuditCategory.TRANSACTION).count(),
    }
    
    # Get top users by activity - filtered by company branches
    top_users = (AuditTrail.objects
                .filter(timestamp__date=today, branch_id__in=company_branch_ids)
                .values('user__first_name', 'user__last_name', 'user__email', 'user__username')
                .annotate(activity_count=Count('id'))
                .order_by('-activity_count')[:10])
    
    # Format user display names
    formatted_top_users = []
    for user in top_users:
        full_name = f"{user['user__first_name'] or ''} {user['user__last_name'] or ''}".strip()
        display_name = full_name if full_name else (user['user__username'] or 'Unknown')
        formatted_top_users.append({
            'name': display_name,
            'email': user['user__email'] or 'No email',
            'activity_count': user['activity_count']
        })
    
    # Get recent alerts
    recent_alerts = AuditAlert.objects.filter(is_resolved=False).order_by('-created_at')[:10]
    
    # Category breakdown for today
    category_stats = (today_stats
                     .values('category')
                     .annotate(count=Count('id'))
                     .order_by('-count'))
    
    context = {
        'recent_audits': recent_audits,
        'stats': stats,
        'top_users': formatted_top_users,
        'recent_alerts': recent_alerts,
        'category_stats': category_stats,
    }
    
    return render(request, 'audit_trail/dashboard.html', context)

@login_required
def audit_list(request):
    """List all audit trails with filtering and pagination - filtered by user's company (all branches)"""
    
    # Get all branch IDs belonging to user's company
    company_branch_ids = get_company_branch_ids_all(request.user)
    
    # Get filter parameters
    user_filter = request.GET.get('user', '')
    action_filter = request.GET.get('action', '')
    category_filter = request.GET.get('category', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search = request.GET.get('search', '')
    success_filter = request.GET.get('success', '')
    
    # Build query - filtered by company branches
    audit_trails = AuditTrail.objects.select_related('user').filter(
        branch_id__in=company_branch_ids
    ).order_by('-timestamp')
    
    # Apply filters
    if user_filter:
        audit_trails = audit_trails.filter(user__id=user_filter)
    
    if action_filter:
        audit_trails = audit_trails.filter(action=action_filter)
    
    if category_filter:
        audit_trails = audit_trails.filter(category=category_filter)
    
    if date_from:
        try:
            date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d').date()
            audit_trails = audit_trails.filter(timestamp__date__gte=date_from_parsed)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d').date()
            audit_trails = audit_trails.filter(timestamp__date__lte=date_to_parsed)
        except ValueError:
            pass
    
    if search:
        audit_trails = audit_trails.filter(
            Q(description__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__username__icontains=search) |
            Q(ip_address__icontains=search) |
            Q(account_number__icontains=search) |
            Q(transaction_reference__icontains=search)
        )
    
    if success_filter:
        audit_trails = audit_trails.filter(success=(success_filter == 'true'))
    
    # Pagination
    paginator = Paginator(audit_trails, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter choices - users from all company branches
    from django.contrib.auth import get_user_model
    User = get_user_model()
    users = User.objects.filter(
        audittrail__isnull=False,
        branch_id__in=company_branch_ids
    ).distinct().order_by('first_name', 'last_name')
    
    # Format users for dropdown
    formatted_users = []
    for user in users:
        full_name = f"{user.first_name} {user.last_name}".strip()
        display_name = full_name if full_name else user.username
        formatted_users.append({
            'id': user.id,
            'name': display_name
        })
    
    context = {
        'page_obj': page_obj,
        'users': formatted_users,
        'actions': AuditAction.choices,
        'categories': AuditCategory.choices,
        'filters': {
            'user': user_filter,
            'action': action_filter,
            'category': category_filter,
            'date_from': date_from,
            'date_to': date_to,
            'search': search,
            'success': success_filter,
        }
    }
    
    return render(request, 'audit_trail/list.html', context)

@login_required
def audit_detail(request, audit_id):
    """View detailed audit trail entry - restricted to user's company branches"""
    
    # Get all branch IDs belonging to user's company
    company_branch_ids = get_company_branch_ids_all(request.user)
    
    # Only allow viewing audit logs from the same company
    audit = get_object_or_404(AuditTrail, id=audit_id, branch_id__in=company_branch_ids)
    
    # Get related audit entries (same user, similar time)
    time_window = timedelta(minutes=5)
    related_audits = AuditTrail.objects.filter(
        user=audit.user,
        timestamp__range=(
            audit.timestamp - time_window,
            audit.timestamp + time_window
        )
    ).exclude(id=audit.id).order_by('timestamp')[:10]
    
    context = {
        'audit': audit,
        'related_audits': related_audits,
    }
    
    return render(request, 'audit_trail/detail.html', context)

@login_required
def audit_statistics(request):
    """Audit trail statistics and reports - filtered by user's company (all branches)"""
    
    # Get all branch IDs belonging to user's company
    company_branch_ids = get_company_branch_ids_all(request.user)
    
    # Get date range
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Daily statistics
    daily_stats = AuditStatistics.objects.filter(
        date__range=(start_date, end_date)
    ).order_by('date')
    
    # Category breakdown for the period - filtered by company branches
    category_breakdown = (AuditTrail.objects
                         .filter(timestamp__date__range=(start_date, end_date), branch_id__in=company_branch_ids)
                         .values('category')
                         .annotate(count=Count('id'))
                         .order_by('-count'))
    
    # Action breakdown - filtered by company branches
    action_breakdown = (AuditTrail.objects
                       .filter(timestamp__date__range=(start_date, end_date), branch_id__in=company_branch_ids)
                       .values('action')
                       .annotate(count=Count('id'))
                       .order_by('-count'))
    
    # User activity - filtered by company branches
    user_activity = (AuditTrail.objects
                    .filter(timestamp__date__range=(start_date, end_date), branch_id__in=company_branch_ids)
                    .values('user__first_name', 'user__last_name', 'user__email', 'user__username')
                    .annotate(activity_count=Count('id'))
                    .order_by('-activity_count')[:20])
    
    # Format user activity
    formatted_user_activity = []
    for user in user_activity:
        full_name = f"{user['user__first_name'] or ''} {user['user__last_name'] or ''}".strip()
        display_name = full_name if full_name else (user['user__username'] or 'Unknown')
        formatted_user_activity.append({
            'name': display_name,
            'email': user['user__email'] or 'No email',
            'activity_count': user['activity_count']
        })
    
    # Failed attempts - filtered by company branches
    failed_attempts = (AuditTrail.objects
                      .filter(timestamp__date__range=(start_date, end_date), success=False, branch_id__in=company_branch_ids)
                      .values('action', 'category')
                      .annotate(count=Count('id'))
                      .order_by('-count')[:10])
    
    context = {
        'daily_stats': daily_stats,
        'category_breakdown': category_breakdown,
        'action_breakdown': action_breakdown,
        'user_activity': formatted_user_activity,
        'failed_attempts': failed_attempts,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'audit_trail/statistics.html', context)

@login_required
def audit_configuration(request):
    """Audit trail configuration settings"""
    
    config = AuditConfiguration.objects.first()
    if not config:
        config = AuditConfiguration.objects.create(updated_by=request.user)
    
    if request.method == 'POST':
        # Update configuration
        config.track_authentication = request.POST.get('track_authentication') == 'on'
        config.track_customer_operations = request.POST.get('track_customer_operations') == 'on'
        config.track_account_operations = request.POST.get('track_account_operations') == 'on'
        config.track_transactions = request.POST.get('track_transactions') == 'on'
        config.track_loans = request.POST.get('track_loans') == 'on'
        config.track_reports = request.POST.get('track_reports') == 'on'
        config.track_admin_operations = request.POST.get('track_admin_operations') == 'on'
        config.track_fixed_assets = request.POST.get('track_fixed_assets') == 'on'
        config.track_cbn_returns = request.POST.get('track_cbn_returns') == 'on'
        config.track_view_actions = request.POST.get('track_view_actions') == 'on'
        
        # Retention settings
        config.retention_days = int(request.POST.get('retention_days', 2555))
        config.auto_cleanup_enabled = request.POST.get('auto_cleanup_enabled') == 'on'
        
        # Alert settings
        config.enable_real_time_alerts = request.POST.get('enable_real_time_alerts') == 'on'
        config.alert_on_failed_logins = request.POST.get('alert_on_failed_logins') == 'on'
        config.alert_on_high_value_transactions = request.POST.get('alert_on_high_value_transactions') == 'on'
        config.high_value_threshold = float(request.POST.get('high_value_threshold', 1000000))
        
        # Security settings
        config.log_ip_addresses = request.POST.get('log_ip_addresses') == 'on'
        config.log_user_agents = request.POST.get('log_user_agents') == 'on'
        config.encrypt_sensitive_data = request.POST.get('encrypt_sensitive_data') == 'on'
        
        config.updated_by = request.user
        config.save()
        
        # Log this configuration change
        create_audit_log(
            user=request.user,
            action=AuditAction.UPDATE,
            category=AuditCategory.ADMIN,
            description="Updated audit trail configuration"
        )
        
        messages.success(request, 'Audit configuration updated successfully.')
        return redirect('audit_trail:configuration')
    
    # Format updated_by user display
    updated_by_display = "System"
    if config.updated_by:
        full_name = f"{config.updated_by.first_name} {config.updated_by.last_name}".strip()
        updated_by_display = full_name if full_name else config.updated_by.username
    
    context = {
        'config': config,
        'updated_by_display': updated_by_display,
    }
    
    return render(request, 'audit_trail/configuration.html', context)

@login_required
def export_audit_csv(request):
    """Export audit trails to CSV - filtered by user's company (all branches)"""
    
    # Get all branch IDs belonging to user's company
    company_branch_ids = get_company_branch_ids_all(request.user)
    
    # Apply same filters as list view - filtered by company branches
    audit_trails = AuditTrail.objects.select_related('user').filter(
        branch_id__in=company_branch_ids
    ).order_by('-timestamp')
    
    # Apply filters from GET parameters
    user_filter = request.GET.get('user', '')
    action_filter = request.GET.get('action', '')
    category_filter = request.GET.get('category', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    if user_filter:
        audit_trails = audit_trails.filter(user__id=user_filter)
    if action_filter:
        audit_trails = audit_trails.filter(action=action_filter)
    if category_filter:
        audit_trails = audit_trails.filter(category=category_filter)
    if date_from:
        try:
            date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d').date()
            audit_trails = audit_trails.filter(timestamp__date__gte=date_from_parsed)
        except ValueError:
            pass
    if date_to:
        try:
            date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d').date()
            audit_trails = audit_trails.filter(timestamp__date__lte=date_to_parsed)
        except ValueError:
            pass
    
    # Limit to reasonable number
    audit_trails = audit_trails[:10000]
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="audit_trail_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Timestamp', 'User', 'Action', 'Category', 'Description', 
        'IP Address', 'Success', 'Account Number', 'Transaction Reference', 
        'Amount', 'Compliance Level'
    ])
    
    for audit in audit_trails:
        writer.writerow([
            audit.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            audit.user_display,
            audit.get_action_display(),
            audit.get_category_display(),
            audit.description,
            audit.ip_address,
            'Yes' if audit.success else 'No',
            audit.account_number,
            audit.transaction_reference,
            format_currency(audit.amount) if audit.amount else '',
            audit.get_compliance_level_display()
        ])
    
    # Log this export
    create_audit_log(
        user=request.user,
        action=AuditAction.EXPORT,
        category=AuditCategory.ADMIN,
        description=f"Exported {audit_trails.count()} audit trail records to CSV"
    )
    
    return response

@login_required
def audit_alerts(request):
    """View and manage audit alerts"""
    
    # Get filter parameters
    alert_type = request.GET.get('type', '')
    severity = request.GET.get('severity', '')
    resolved = request.GET.get('resolved', '')
    
    # Build query
    alerts = AuditAlert.objects.select_related('audit_trail__user', 'resolved_by').order_by('-created_at')
    
    if alert_type:
        alerts = alerts.filter(alert_type=alert_type)
    if severity:
        alerts = alerts.filter(severity=severity)
    if resolved:
        alerts = alerts.filter(is_resolved=(resolved == 'true'))
    
    # Pagination
    paginator = Paginator(alerts, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'alert_types': AuditAlert.ALERT_TYPES,
        'severity_levels': AuditAlert.SEVERITY_LEVELS,
        'filters': {
            'type': alert_type,
            'severity': severity,
            'resolved': resolved,
        }
    }
    
    return render(request, 'audit_trail/alerts.html', context)

@login_required
def resolve_alert(request, alert_id):
    """Resolve an audit alert"""
    
    if request.method == 'POST':
        alert = get_object_or_404(AuditAlert, id=alert_id)
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.resolved_by = request.user
        alert.resolution_notes = request.POST.get('notes', '')
        alert.save()
        
        messages.success(request, 'Alert resolved successfully.')
    
    return redirect('audit_trail:alerts')

@csrf_exempt
def audit_api_log(request):
    """API endpoint for manual audit logging"""
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Create audit log
            audit = AuditTrail.objects.create(
                user=request.user if request.user.is_authenticated else None,
                action=data.get('action', AuditAction.VIEW),
                category=data.get('category', AuditCategory.ADMIN),
                description=data.get('description', ''),
                account_number=data.get('account_number', ''),
                customer_id=data.get('customer_id', ''),
                transaction_reference=data.get('transaction_reference', ''),
                amount=data.get('amount'),
                compliance_level=data.get('compliance_level', 'LOW')
            )
            
            return JsonResponse({'success': True, 'audit_id': audit.id})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Method not allowed'})