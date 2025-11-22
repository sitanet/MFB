from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import json

User = get_user_model()

class AuditAction(models.TextChoices):
    """Enum for audit trail actions"""
    CREATE = 'CREATE', 'Create'
    UPDATE = 'UPDATE', 'Update'
    DELETE = 'DELETE', 'Delete'
    LOGIN = 'LOGIN', 'Login'
    LOGOUT = 'LOGOUT', 'Logout'
    VIEW = 'VIEW', 'View'
    EXPORT = 'EXPORT', 'Export'
    IMPORT = 'IMPORT', 'Import'
    APPROVE = 'APPROVE', 'Approve'
    REJECT = 'REJECT', 'Reject'
    TRANSACTION = 'TRANSACTION', 'Transaction'

class AuditCategory(models.TextChoices):
    """Categories for audit trails"""
    AUTHENTICATION = 'AUTH', 'Authentication'
    CUSTOMER = 'CUSTOMER', 'Customer Management'
    ACCOUNT = 'ACCOUNT', 'Account Management'
    TRANSACTION = 'TRANSACTION', 'Transactions'
    LOAN = 'LOAN', 'Loan Management'
    REPORT = 'REPORT', 'Reports'
    ADMIN = 'ADMIN', 'Administration'
    FIXED_ASSETS = 'FIXED_ASSETS', 'Fixed Assets'
    FIXED_DEPOSIT = 'FIXED_DEPOSIT', 'Fixed Deposits'
    CBN_RETURNS = 'CBN_RETURNS', 'CBN Returns'
    SETTINGS = 'SETTINGS', 'Settings'
    BULK_OPERATIONS = 'BULK_OPS', 'Bulk Operations'

class AuditTrail(models.Model):
    """
    Comprehensive audit trail model for tracking all user activities
    in the FinanceFlex banking application
    """
    # Basic Information
    id = models.BigAutoField(primary_key=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, blank=True, null=True)
    
    # Action Details
    action = models.CharField(max_length=20, choices=AuditAction.choices)
    category = models.CharField(max_length=20, choices=AuditCategory.choices)
    description = models.TextField()
    
    # Target Object (Generic Foreign Key for any model)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Additional Context
    model_name = models.CharField(max_length=100, blank=True)
    object_repr = models.TextField(blank=True)  # String representation of the object
    
    # Data Changes (for UPDATE actions)
    old_values = models.JSONField(blank=True, null=True)
    new_values = models.JSONField(blank=True, null=True)
    
    # Request Information
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_method = models.CharField(max_length=10, blank=True)  # GET, POST, PUT, DELETE
    request_path = models.CharField(max_length=500, blank=True)
    
    # Additional Metadata
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)  # Request duration
    
    # Banking-Specific Fields
    account_number = models.CharField(max_length=20, blank=True, db_index=True)
    customer_id = models.CharField(max_length=20, blank=True, db_index=True)
    transaction_reference = models.CharField(max_length=100, blank=True, db_index=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Compliance Fields
    compliance_level = models.CharField(
        max_length=10,
        choices=[
            ('LOW', 'Low'),
            ('MEDIUM', 'Medium'),
            ('HIGH', 'High'),
            ('CRITICAL', 'Critical')
        ],
        default='LOW'
    )
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'user']),
            models.Index(fields=['action', 'category']),
            models.Index(fields=['account_number']),
            models.Index(fields=['customer_id']),
            models.Index(fields=['transaction_reference']),
            models.Index(fields=['compliance_level']),
            models.Index(fields=['ip_address']),
        ]
        verbose_name = 'Audit Trail'
        verbose_name_plural = 'Audit Trails'
    
    def __str__(self):
        return f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {self.user} - {self.action} - {self.description}"
    
    def save(self, *args, **kwargs):
        # Automatically set model_name if content_object is provided
        if self.content_object and not self.model_name:
            self.model_name = self.content_object._meta.label
        
        # Set object representation
        if self.content_object and not self.object_repr:
            self.object_repr = str(self.content_object)
        
        super().save(*args, **kwargs)
    
    @property
    def user_display(self):
        """Display user information for audit trails"""
        if self.user:
            full_name = f"{self.user.first_name} {self.user.last_name}".strip()
            display_name = full_name if full_name else self.user.username
            return f"{display_name} ({self.user.email})"
        return "System"

    @property
    def user_name_only(self):
        """Display only user name for audit trails"""
        if self.user:
            full_name = f"{self.user.first_name} {self.user.last_name}".strip()
            return full_name if full_name else self.user.username
        return "System"

    
    @property
    def formatted_timestamp(self):
        """Formatted timestamp for display"""
        return self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    
    @property
    def changes_summary(self):
        """Summary of changes for UPDATE actions"""
        if self.action == AuditAction.UPDATE and self.old_values and self.new_values:
            changes = []
            for key in self.new_values.keys():
                if key in self.old_values and self.old_values[key] != self.new_values[key]:
                    changes.append(f"{key}: {self.old_values[key]} → {self.new_values[key]}")
            return "; ".join(changes) if changes else "No changes detected"
        return ""

class AuditConfiguration(models.Model):
    """Configuration settings for audit trail"""
    
    # What to track
    track_authentication = models.BooleanField(default=True)
    track_customer_operations = models.BooleanField(default=True)
    track_account_operations = models.BooleanField(default=True)
    track_transactions = models.BooleanField(default=True)
    track_loans = models.BooleanField(default=True)
    track_reports = models.BooleanField(default=True)
    track_admin_operations = models.BooleanField(default=True)
    track_fixed_assets = models.BooleanField(default=True)
    track_cbn_returns = models.BooleanField(default=True)
    track_view_actions = models.BooleanField(default=False)  # Usually too noisy
    
    # Retention settings
    retention_days = models.PositiveIntegerField(default=2555)  # 7 years for banking compliance
    auto_cleanup_enabled = models.BooleanField(default=True)
    
    # Alert settings
    enable_real_time_alerts = models.BooleanField(default=True)
    alert_on_failed_logins = models.BooleanField(default=True)
    alert_on_high_value_transactions = models.BooleanField(default=True)
    high_value_threshold = models.DecimalField(max_digits=15, decimal_places=2, default=1000000)
    
    # Security settings
    log_ip_addresses = models.BooleanField(default=True)
    log_user_agents = models.BooleanField(default=True)
    encrypt_sensitive_data = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = 'Audit Configuration'
        verbose_name_plural = 'Audit Configurations'
    
    def __str__(self):
        return f"Audit Config - Updated {self.updated_at.strftime('%Y-%m-%d')}"

class AuditAlert(models.Model):
    """Alerts generated by the audit system"""
    
    ALERT_TYPES = [
        ('SECURITY', 'Security Alert'),
        ('COMPLIANCE', 'Compliance Alert'),
        ('PERFORMANCE', 'Performance Alert'),
        ('ERROR', 'Error Alert'),
    ]
    
    SEVERITY_LEVELS = [
        ('INFO', 'Information'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    ]
    
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)
    title = models.CharField(max_length=200)
    message = models.TextField()
    audit_trail = models.ForeignKey(AuditTrail, on_delete=models.CASCADE, related_name='alerts')
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['alert_type', 'severity']),
            models.Index(fields=['is_resolved']),
        ]
    
    def __str__(self):
        return f"{self.get_severity_display()} - {self.title}"

class AuditStatistics(models.Model):
    """Daily statistics for audit trails"""
    
    date = models.DateField(unique=True, db_index=True)
    total_actions = models.PositiveIntegerField(default=0)
    unique_users = models.PositiveIntegerField(default=0)
    failed_attempts = models.PositiveIntegerField(default=0)
    high_value_transactions = models.PositiveIntegerField(default=0)
    
    # Category breakdown
    authentication_actions = models.PositiveIntegerField(default=0)
    customer_actions = models.PositiveIntegerField(default=0)
    transaction_actions = models.PositiveIntegerField(default=0)
    report_actions = models.PositiveIntegerField(default=0)
    admin_actions = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name = 'Audit Statistics'
        verbose_name_plural = 'Audit Statistics'
    
    def __str__(self):
        return f"Audit Stats - {self.date}"