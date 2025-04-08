from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.serializers.json import DjangoJSONEncoder
import json

User = get_user_model()

class AuditLogManager(models.Manager):
    def for_branch(self, branch):
        """Filter logs by user's branch"""
        return self.filter(user_branch=str(branch))

    def for_role(self, role):
        """Filter logs by user's role"""
        return self.filter(user_role=role)

    def get_actions(self):
        """Get distinct action types"""
        return self.values_list('action', flat=True).distinct()

class CustomJSONEncoder(DjangoJSONEncoder):
    def default(self, obj):
        """Handle model instances and other special types during JSON serialization"""
        if hasattr(obj, 'pk'):
            return {
                'model': f"{obj._meta.app_label}.{obj._meta.model_name}",
                'id': str(obj.pk),
                'str': str(obj),
                'fields': {
                    f.name: getattr(obj, f.name) 
                    for f in obj._meta.fields 
                    if f.name != 'password'  # Exclude sensitive fields
                }
            }
        return super().default(obj)

class AuditLog(models.Model):
    ACTION_CREATE = 'CREATE'
    ACTION_UPDATE = 'UPDATE'
    ACTION_DELETE = 'DELETE'
    ACTION_VIEW = 'VIEW'
    ACTION_LOGIN = 'LOGIN'
    ACTION_LOGOUT = 'LOGOUT'
    ACTION_ACCESS = 'ACCESS'

    ACTION_CHOICES = [
        (ACTION_CREATE, 'Create'),
        (ACTION_UPDATE, 'Update'),
        (ACTION_DELETE, 'Delete'),
        (ACTION_VIEW, 'View'),
        (ACTION_LOGIN, 'Login'),
        (ACTION_LOGOUT, 'Logout'),
        (ACTION_ACCESS, 'Access'),
    ]

    # Core tracking fields
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='audit_logs',
        verbose_name='User'
    )
    action = models.CharField(
        max_length=10, 
        choices=ACTION_CHOICES,
        verbose_name='Action Type'
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name='Timestamp'
    )

    # Object tracking
    object_id = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        db_index=True,
        verbose_name='Object ID'
    )
    content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name='Content Type'
    )
    content_object = GenericForeignKey('content_type', 'object_id')

    # State tracking
    before = models.JSONField(
        null=True, 
        blank=True, 
        encoder=CustomJSONEncoder,
        verbose_name='Before State'
    )
    after = models.JSONField(
        null=True, 
        blank=True, 
        encoder=CustomJSONEncoder,
        verbose_name='After State'
    )
    message = models.TextField(
        null=True, 
        blank=True,
        verbose_name='Description'
    )

    # Context fields
    ip_address = models.GenericIPAddressField(
        null=True, 
        blank=True,
        verbose_name='IP Address'
    )
    user_agent = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='User Agent'
    )
    user_role = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        verbose_name='User Role'
    )
    user_branch = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        verbose_name='User Branch'
    )
    user_agent = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name='User Agent'
    )

    # Metadata
    is_system = models.BooleanField(
        default=False,
        verbose_name='System Generated'
    )

    objects = AuditLogManager()

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['timestamp', 'user']),
            models.Index(fields=['user_role', 'timestamp']),
        ]
        permissions = [
            ('can_view_auditlog', 'Can view audit logs'),
            ('can_delete_auditlog', 'Can delete audit logs'),
            ('can_export_auditlog', 'Can export audit logs'),
        ]

    def __str__(self):
        return f"{self.get_action_display()} by {self.user or 'System'} on {self.timestamp}"

    def save(self, *args, **kwargs):
        """Capture additional context before saving"""
        if not self.pk:  # Only on creation
            self.capture_context()
        super().save(*args, **kwargs)

    def capture_context(self):
        """Capture user context without modifying User model"""
        if self.user:
            # Capture role display name if get_role_display exists
            if hasattr(self.user, 'get_role_display'):
                self.user_role = self.user.get_role_display()
            # Capture branch if exists
            if hasattr(self.user, 'branch') and self.user.branch:
                self.user_branch = str(self.user.branch)

    def get_absolute_url(self):
        """URL to view this log entry"""
        from django.urls import reverse
        return reverse('audit_log_detail', kwargs={'pk': self.pk})

    @property
    def action_icon(self):
        """Icon representation for UI"""
        icons = {
            self.ACTION_CREATE: 'add',
            self.ACTION_UPDATE: 'edit',
            self.ACTION_DELETE: 'delete',
            self.ACTION_VIEW: 'visibility',
            self.ACTION_LOGIN: 'login',
            self.ACTION_LOGOUT: 'logout',
            self.ACTION_ACCESS: 'lock_open',
        }
        return icons.get(self.action, 'info')

    @classmethod
    def log_action(cls, user, action, obj=None, before=None, after=None, message=None, request=None):
        """Helper method to create audit logs"""
        log = cls(
            user=user,
            action=action,
            content_object=obj,
            before=before,
            after=after,
            message=message,
            is_system=user is None
        )
        
        if request:
            log.ip_address = request.META.get('REMOTE_ADDR')
            log.user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]
        
        log.save()
        return log