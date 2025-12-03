"""
Company Models for Multi-Database Architecture

These models are stored in the VENDOR database and contain
only basic company/branch structure controlled by the software vendor.
"""

from django.utils import timezone
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils.timezone import now

class Company(models.Model):
    """
    Company model - Stored in VENDOR database
    
    This model is controlled by the software vendor and contains
    basic company structure and licensing information.
    """
    company_name = models.CharField(max_length=100, null=True, blank=True)
    contact_person = models.CharField(max_length=100)
    office_address = models.CharField(max_length=100)
    contact_phone_no = models.CharField(max_length=100)
    session_date = models.DateField(null=True, blank=True)
    system_date_date = models.DateField(null=True, blank=True)
    registration_date = models.DateField()
    expiration_date = models.DateField()
    license_key = models.CharField(max_length=50)
    session_status = models.CharField(max_length=12, null=True, blank=True)
    email = models.EmailField(max_length=255, unique=True, null=True, blank=True)
    float_account_number = models.CharField(
        max_length=25,
        null=True,
        blank=True,
        help_text="The 9PSB wallet or float account number assigned to this company."
    )
    last_notification_date = models.DateField(null=True, blank=True)
    float_gl_no = models.CharField(
        max_length=25,
        null=True,
        blank=True,
        help_text="GL number linked to the company's float account."
    )
    float_ac_no = models.CharField(
        max_length=25,
        null=True,
        blank=True,
        help_text="Internal ledger account number linked to the float account."
    )
    mobile_teller_gl_no = models.CharField(
        max_length=25,
        null=True,
        blank=True,
        help_text="GL number linked to the company's Mobile Teller account."
    )
    mobile_teller_ac_no = models.CharField(
        max_length=25,
        null=True,
        blank=True,
        help_text="Internal ledger account number linked to the Mobile Teller account."
    )

    class Meta:
        # This ensures the model is routed to vendor_db
        app_label = 'company'

    def __str__(self):
        return str(self.company_name)


class Branch(models.Model):
    """
    Branch model - Stored in VENDOR database
    
    This model is controlled by the software vendor and contains
    branch structure and subscription plans.
    """
    PLAN_CHOICES = [
        ("Starter", "Starter"),
        ("Basic", "Basic"),
        ("Premium", "Premium"),
        ("Professional", "Professional"),
        ("Ultimate", "Ultimate"),
        ("Enterprise", "Enterprise"),
    ]

    company_name = models.CharField(max_length=100)
    company = models.ForeignKey(
        "Company",
        on_delete=models.CASCADE,
        related_name="branches"
    )
    branch_code = models.CharField(max_length=6)
    branch_name = models.CharField(max_length=90)
    logo = models.ImageField(upload_to='branch_logos/', blank=True, null=True)
    address = models.TextField()
    cac_number = models.CharField(max_length=100)
    license_number = models.CharField(max_length=100)
    company_type = models.CharField(max_length=50)
    bvn_number = models.CharField(max_length=11)
    phone_number = models.CharField(max_length=20)
    phone_verified = models.BooleanField(default=False)
    head_office = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, null=True, blank=True)
    plan = models.CharField(max_length=15, choices=PLAN_CHOICES, default="Starter")
    session_date = models.DateField(null=True, blank=True, default=now)
    system_date_date = models.DateField(null=True, blank=True)
    session_status = models.CharField(max_length=10, null=True, blank=True)
    expire_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # This ensures the model is routed to vendor_db
        app_label = 'company'

    def save(self, *args, **kwargs):
        # Only set expire_date if not already set (e.g., on creation)
        if not self.expire_date and not self.pk:  # only on first save
            from datetime import timedelta
            self.expire_date = timezone.now().date() + timedelta(days=30)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.company_name} - {self.branch_name} - {self.plan}"


class SmsDelivery(models.Model):
    """
    SmsDelivery model - Stored in CLIENT database (default)
    
    This model references Branch but is stored in client database.
    Uses branch_id to reference branch in vendor database.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('error', 'Error')
    ]
    
    # Store branch ID instead of ForeignKey to reference vendor database
    branch_id = models.CharField(
        max_length=10, 
        null=True,
        help_text="Branch ID from vendor database"
    )
    phone_number = models.CharField(max_length=20)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_branch(self):
        """
        Helper method to get branch from vendor database
        
        Returns:
            Branch object or None
        """
        if self.branch_id:
            return Branch.objects.using('vendor_db').get(id=self.branch_id)
        return None
    
    def __str__(self):
        return f"SMS to {self.phone_number} ({self.status})"