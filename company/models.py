"""
Company Models for Multi-Database Architecture

These models are stored in the VENDOR database and contain
only basic company/branch structure controlled by the software vendor.
"""

import uuid
from django.utils import timezone
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.contrib.auth.hashers import make_password, check_password
from django.utils.timezone import now

class Company(models.Model):
    """
    Company model - Stored in VENDOR database
    
    This model is controlled by the software vendor and contains
    basic company structure and licensing information.
    """
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
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
    email = models.EmailField(max_length=255, null=True, blank=True)  # unique=True removed to allow shared emails
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

    def has_transactions(self):
        """Check if any branch of this company has transactions"""
        from transactions.models import Memtrans
        branch_ids = self.branches.values_list('id', flat=True)
        return Memtrans.all_objects.filter(branch_id__in=branch_ids).exists() or \
               Memtrans.all_objects.filter(cust_branch_id__in=branch_ids).exists()

    def can_delete(self):
        """Check if company can be safely deleted"""
        return not self.has_transactions()




class Branch(models.Model):
    """
    Branch model - Stored in VENDOR database
    
    This model is controlled by the software vendor and contains
    branch structure and subscription plans.
    """
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
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
    is_active = models.BooleanField(default=True, help_text="Uncheck to deactivate branch when subscription is not made")
    
    # Customer limit - set by vendor during branch registration
    max_customers = models.PositiveIntegerField(
        default=0,
        help_text="Maximum number of customers this branch can create. 0 = unlimited."
    )
    
    # Feature flags - enable/disable features per branch
    can_fixed_deposit = models.BooleanField(
        default=True, 
        help_text="Enable Fixed Deposit feature for this branch"
    )
    can_loans = models.BooleanField(
        default=True, 
        help_text="Enable Loans feature for this branch"
    )
    can_transfers = models.BooleanField(
        default=True, 
        help_text="Enable Fund Transfers feature for this branch"
    )
    can_fixed_assets = models.BooleanField(
        default=True, 
        help_text="Enable Fixed Assets feature for this branch"
    )
    can_mobile_banking = models.BooleanField(
        default=False, 
        help_text="Enable Mobile Banking feature for this branch"
    )
    can_sms_alerts = models.BooleanField(
        default=False, 
        help_text="Enable SMS Alerts feature for this branch"
    )
    
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
    
    def get_customer_count(self):
        """Get current number of customers in this branch"""
        from customers.models import Customer
        return Customer.objects.filter(branch_id=self.id).count()
    
    def can_add_customer(self):
        """Check if branch can add more customers based on limit"""
        if self.max_customers == 0:  # 0 = unlimited
            return True
        return self.get_customer_count() < self.max_customers
    
    def remaining_customer_slots(self):
        """Get number of remaining customer slots"""
        if self.max_customers == 0:
            return None  # Unlimited
        return max(0, self.max_customers - self.get_customer_count())

    def has_transactions(self):
        """Check if this branch has any transactions"""
        from transactions.models import Memtrans
        return Memtrans.all_objects.filter(branch_id=self.id).exists() or \
               Memtrans.all_objects.filter(cust_branch_id=self.id).exists()

    def can_delete(self):
        """Check if branch can be safely deleted"""
        return not self.has_transactions()




class SmsDelivery(models.Model):
    """
    SmsDelivery model - Stored in CLIENT database (default)
    
    This model references Branch but is stored in client database.
    Uses branch_id to reference branch in vendor database.
    """
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
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


# ==================== VENDOR USER AUTHENTICATION ====================

class VendorUserManager(BaseUserManager):
    """
    Custom manager for VendorUser model.
    Handles vendor-level user creation for software vendor management.
    """
    
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('Vendor user must have an email address')
        if not username:
            raise ValueError('Vendor user must have a username')
        
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_supervendor', True)
        
        return self.create_user(email, username, password, **extra_fields)


class VendorUser(AbstractBaseUser):
    """
    Vendor User model - Stored in VENDOR database
    
    This model is used for software vendor authentication.
    Completely separate from client User model.
    Vendor users can manage all companies and branches.
    """
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    email = models.EmailField(max_length=255)  # unique=True removed to allow shared emails
    username = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    
    # Permissions
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_supervendor = models.BooleanField(default=False, help_text="Super vendor has full access to all vendor operations")
    
    # Timestamps
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)
    
    objects = VendorUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']
    
    class Meta:
        app_label = 'company'
        verbose_name = 'Vendor User'
        verbose_name_plural = 'Vendor Users'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_short_name(self):
        return self.first_name
    
    def has_perm(self, perm, obj=None):
        return self.is_supervendor
    
    def has_module_perms(self, app_label):
        return self.is_supervendor