from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib.contenttypes.models import ContentType
from .models import AuditLog
import json

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        'timestamp',
        'safe_user_display',
        'colored_action',
        'safe_object_display',
        'ip_address',
        'truncated_message'
    )
    list_filter = (
        'action',
        ('timestamp', admin.DateFieldListFilter),
        'content_type',
    )
    search_fields = (
        'user__username',
        'user__email',
        'message',
        'ip_address',
        'object_id'
    )
    readonly_fields = (
        'timestamp',
        'safe_user_display',
        'colored_action',
        'safe_object_link',
        'ip_address',
        'formatted_before',
        'formatted_after',
        'full_message'
    )
    date_hierarchy = 'timestamp'
    list_per_page = 25
    actions = None
    show_full_result_count = False

    fieldsets = (
        ('Metadata', {
            'fields': (
                'timestamp',
                'safe_user_display',
                'colored_action',
                'safe_object_link',
                'ip_address'
            )
        }),
        ('State Changes', {
            'fields': (
                'formatted_before',
                'formatted_after',
            ),
            'classes': ('collapse',)
        }),
        ('Details', {
            'fields': ('full_message',)
        }),
    )

    def safe_user_display(self, obj):
        if not obj.user:
            return format_html('<span style="color:#666;">System</span>')
        
        user_str = f"{obj.user.username}"
        try:
            # Try default auth URL first
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, user_str)
        except:
            try:
                # Try custom user model URL
                url = reverse(f'admin:{obj.user._meta.app_label}_{obj.user._meta.model_name}_change', args=[obj.user.id])
                return format_html('<a href="{}">{}</a>', url, user_str)
            except:
                # Final fallback - just show username
                return user_str
    safe_user_display.short_description = 'User'
    safe_user_display.admin_order_field = 'user__username'

    def colored_action(self, obj):
        colors = {
            'CREATE': '#4CAF50',  # Green
            'UPDATE': '#2196F3',   # Blue
            'DELETE': '#F44336',   # Red
            'VIEW': '#9E9E9E',     # Gray
            'LOGIN': '#388E3C',    # Dark Green
            'LOGOUT': '#D32F2F',   # Dark Red
            'ACCESS': '#FF9800',   # Orange
        }
        return format_html(
            '<span style="display:inline-block; padding:2px 8px; border-radius:12px; background:{}; color:white; font-size:0.9em;">{}</span>',
            colors.get(obj.action, '#607D8B'),
            obj.get_action_display()
        )
    colored_action.short_description = 'Action'

    def safe_object_display(self, obj):
        if not obj.content_type:
            return '-'
        
        obj_str = f"{obj.content_type.model.capitalize()} #{obj.object_id}"
        
        try:
            if obj.content_object:
                try:
                    url = reverse(
                        f'admin:{obj.content_type.app_label}_{obj.content_type.model}_change',
                        args=[obj.object_id]
                    )
                    return format_html('<a href="{}">{}</a>', url, str(obj.content_object))
                except:
                    return format_html('<span>{}</span>', str(obj.content_object))
            return format_html('<span style="color:#999;">{} (deleted)</span>', obj_str)
        except Exception as e:
            return format_html('<span style="color:#999;">{} (error: {})</span>', obj_str, str(e))
    safe_object_display.short_description = 'Object'

    def safe_object_link(self, obj):
        return self.safe_object_display(obj)
    safe_object_link.short_description = 'Related Object'

    def truncated_message(self, obj):
        if not obj.message:
            return '-'
        return (obj.message[:60] + '...') if len(obj.message) > 60 else obj.message
    truncated_message.short_description = 'Message'

    def full_message(self, obj):
        return obj.message or '-'
    full_message.short_description = 'Full Message'

    def formatted_before(self, obj):
        return self._format_json(obj.before)
    formatted_before.short_description = 'Before State'

    def formatted_after(self, obj):
        return self._format_json(obj.after)
    formatted_after.short_description = 'After State'

    def _format_json(self, data):
        if not data:
            return mark_safe('<span style="color:#999;">(empty)</span>')
        
        try:
            formatted = json.dumps(data, indent=2, sort_keys=True)
            return mark_safe(f'<pre style="white-space:pre-wrap; word-wrap:break-word; background:#f5f5f5; padding:10px; border-radius:4px;">{formatted}</pre>')
        except Exception as e:
            return mark_safe(f'<span style="color:#900;">Error formatting: {str(e)}</span>')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm('audit_trail.can_delete_auditlog')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.has_perm('audit_trail.can_delete_auditlog'):
            qs = qs.filter(user=request.user)
        return qs.select_related('user', 'content_type')

    class Media:
        css = {
            'all': ('admin/css/auditlog.css',)
        }