"""
User Models for Multi-Database Architecture

This module contains user-related models that are stored in the CLIENT database (default).
Company and Branch models are referenced by ID from the VENDOR database.
"""

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.utils.timezone import now
from accounts_admin.models import Account
from django.utils import timezone
from datetime import timedelta

import random
import string
from django.utils.text import slugify

from django.contrib.auth.hashers import make_password, check_password


class Role(models.Model):
    """
    User Role model - Stored in CLIENT database
    """
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    """
    Custom User Manager for Multi-Database Architecture
    """
    
    def create_user(
        self,
        first_name,
        last_name,
        username,
        email,
        role,
        phone_number=None,
        cashier_gl=None,
        cashier_ac=None,
        branch_id=None,  # Changed from branch to branch_id
        gl_no=None,
        ac_no=None,
        password=None,
    ):
        """Create a regular user in the client database"""
        if not email:
            raise ValueError("User must have an email address")
        if not username:
            raise ValueError("User must have a username")

        user = self.model(
            email=self.normalize_email(email),
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=role,
            phone_number=phone_number,
            cashier_gl=cashier_gl,
            cashier_ac=cashier_ac,
            branch=branch,  # Store branch ID as string
            gl_no=gl_no,
            ac_no=ac_no,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, first_name, last_name, username, email, password=None):
        """Create superuser with default company/branch in vendor database"""
        from company.models import Company, Branch
        
        # Work with vendor database for Company operations
        try:
            default_company = Company.objects.using('vendor_db').get(
                company_name="Default Company"
            )
        except Company.DoesNotExist:
            # Create default company in vendor database
            default_company = Company(
                company_name="Default Company",
                contact_person="Admin",
                office_address="123 Default Street",
                contact_phone_no="1234567890",
                registration_date=now().date(),
                expiration_date=now().date().replace(year=now().year + 1),
                license_key="DEFAULTLICENSEKEY",
            )
            default_company.save(using='vendor_db')

        # Work with vendor database for Branch operations
        try:
            default_branch = Branch.objects.using('vendor_db').get(
                company=default_company,
                branch_name="Demo Branch"
            )
        except Branch.DoesNotExist:
            # Create default branch in vendor database
            default_branch = Branch(
                company=default_company,
                company_name=default_company.company_name,
                branch_code="MAIN",
                branch_name="Demo Branch",
                address="Demo Address",
                cac_number="CAC123",
                license_number="LIC123",
                company_type="Demo",
                bvn_number="12345678901",
                phone_number="+2348066311516",
                session_date=now().date(),
                system_date_date=now().date(),
                session_status="Active",
            )
            default_branch.save(using='vendor_db')

        # Create superuser in client database with branch_id reference
        user = self.create_user(
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=email,
            role=User.SYSTEM_ADMINISTRATOR,
            branch=default_branch,  # Store branch ID as string
            phone_number="+2348066311516",
            cashier_gl=None,
            cashier_ac=None,
            gl_no="99999",
            ac_no="00001",
            password=password,
        )
        user.is_admin = True
        user.is_active = True
        user.is_staff = True
        user.is_superadmin = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    """
    Custom User model - Stored in CLIENT database
    References Branch by ID from vendor database for security separation.
    """
    
    # Role choices
    SYSTEM_ADMINISTRATOR = 1
    GENERAL_MANAGER = 2
    BRANCH_MANAGER = 3
    ASSISTANT_MANAGER = 4
    ACCOUNTANT = 5
    ACCOUNTS_ASSISTANT = 6
    CREDIT_SUPERVISOR = 7
    CREDIT_OFFICER = 8
    VERIFICATION_OFFICER = 9
    CUSTOMER_SERVICE_UNIT = 10
    TELLER = 11
    M_I_S_OFFICER = 12
    CUSTOMER = 13 

    ROLE_CHOICE = (
        (SYSTEM_ADMINISTRATOR, 'System Administration'),
        (GENERAL_MANAGER, 'General Manager'),
        (BRANCH_MANAGER, 'Branch Manager'),
        (ASSISTANT_MANAGER, 'Assistant Manager'),
        (ACCOUNTANT, 'Accountant'),
        (ACCOUNTS_ASSISTANT, 'Accounts Assistant'),
        (CREDIT_SUPERVISOR, 'Credit Supervisor'),
        (CREDIT_OFFICER, 'Credit Officer'),
        (VERIFICATION_OFFICER, 'Verification Officer'),
        (CUSTOMER_SERVICE_UNIT, 'Customer Service Unit'),
        (TELLER, 'Teller'),
        (M_I_S_OFFICER, 'Management Information System'),
        (CUSTOMER, 'Customer'),
    )

    # Basic user information
    profile_picture = models.ImageField(upload_to='users/profile_pictures', default='images/avatar.jpg')
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=100, unique=True)
    phone_number = models.CharField(max_length=16, blank=True, null=True)
    role = models.PositiveSmallIntegerField(choices=ROLE_CHOICE, blank=True, null=True)
    
    # Branch reference - CHANGED: Now stores branch ID instead of ForeignKey
    # Branch reference - COMPULSORY for all users
    branch = models.CharField(max_length=20, help_text="Vendor DB Branch ID")

    # Authentication and security fields
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    last_otp_sent = models.DateTimeField(blank=True, null=True)
    cashier_gl = models.CharField(max_length=6, blank=True, null=True)
    cashier_ac = models.CharField(max_length=1, blank=True, null=True)
    activation_code = models.CharField(max_length=20, blank=True, null=True, unique=True)
    
    # Customer relationship
    # Make sure this line around line 163 looks like this:
    customer = models.ForeignKey(
        'customers.Customer', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True  # This makes it optional initially
    )

    # Transaction PIN (securely hashed)
    transaction_pin = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        help_text="Securely hashed 4–6 digit transaction PIN"
    )

    # Account information
    gl_no = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="General Ledger number linked to this user (Customer or Teller)."
    )
    ac_no = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Account number linked to this user (Customer or Teller)."
    )

    # System fields
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now_add=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_superadmin = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']

    objects = UserManager()

    def __str__(self):
        return self.username

    # --- Cross-Database Helper Methods ---
    
    def get_branch(self):
        """Get the branch object from vendor database"""
        if not self.branch_id:
            return None
            
        try:
            from company.models import Branch
            return Branch.objects.using('vendor_db').get(id=self.branch_id)
        except (Branch.DoesNotExist, ValueError):
            return None
    
    def get_company(self):
        """Get the company object from vendor database through branch"""
        branch = self.get_branch()
        if branch:
            return branch.company
        return None
    
    @property
    def branch_name(self):
        """Get branch name for display purposes"""
        branch = self.get_branch()
        return branch.branch_name if branch else None
    
    @property
    def company_name(self):
        """Get company name for display purposes"""
        company = self.get_company()
        return company.company_name if company else None
    
    def set_branch_by_id(self, branch_id):
        """Set branch by ID with validation"""
        if not branch_id:
            self.branch_id = None
            return True
            
        try:
            from company.models import Branch
            # Validate branch exists in vendor database
            Branch.objects.using('vendor_db').get(id=branch_id)
            self.branch_id = str(branch_id)
            return True
        except (Branch.DoesNotExist, ValueError):
            return False

    # --- Transaction PIN Management ---
    
    def set_transaction_pin(self, raw_pin):
        """Hash and set a new transaction PIN"""
        if raw_pin:
            self.transaction_pin = make_password(raw_pin)

    def check_transaction_pin(self, raw_pin):
        """Verify that the provided PIN matches the stored hash"""
        if not self.transaction_pin:
            return False
        return check_password(raw_pin, self.transaction_pin)

    # --- Permission Methods ---
    
    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return True

    def get_role(self):
        """Get human-readable role name"""
        roles = dict(self.ROLE_CHOICE)
        return roles.get(self.role, "Unknown Role")

    # --- OTP Methods ---
    
    def is_otp_valid(self, otp, expiry_minutes=5):
        """Check if OTP matches and is within expiry time"""
        if self.otp_code != otp:
            return False
        if not self.last_otp_sent:
            return False
        if timezone.now() > self.last_otp_sent + timedelta(minutes=expiry_minutes):
            return False
        return True

    # --- Override Save Method ---
    
    def save(self, *args, **kwargs):
        """Custom save method with additional processing"""
        # Auto-generate activation code if role is Customer
        if self.role == self.CUSTOMER and not self.activation_code and self.branch_id:
            branch = self.get_branch()
            if branch:
                branch_code = slugify(branch.branch_name)[:3].upper()
                random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
                self.activation_code = f"{branch_code}{random_part}"

        # Auto-hash PIN if a plain PIN is assigned
        if self.transaction_pin and not self.transaction_pin.startswith("pbkdf2_"):
            self.transaction_pin = make_password(self.transaction_pin)

        super().save(*args, **kwargs)


class UserProfile(models.Model):
    """Extended user profile information - Stored in CLIENT database"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True)
    address = models.CharField(max_length=250, blank=True, null=True)
    country = models.CharField(max_length=15, blank=True, null=True)
    state = models.CharField(max_length=15, blank=True, null=True)
    city = models.CharField(max_length=15, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.email if self.user else "No User"


class UserActivityLog(models.Model):
    """User activity tracking - Stored in CLIENT database"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    ip_address = models.GenericIPAddressField()
    function_used = models.CharField(max_length=255)
    date_time = models.DateTimeField(auto_now_add=True)
    user_agent = models.TextField()

    class Meta:
        ordering = ['-date_time']
        indexes = [
            models.Index(fields=['user', 'date_time']),
            models.Index(fields=['function_used']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.function_used} at {self.date_time}"


class Clients(models.Model):
    """Client information model - Stored in CLIENT database"""
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField()

    def __str__(self):
        return self.name