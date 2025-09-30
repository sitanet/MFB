from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.utils.timezone import now  # For default datetime
from accounts_admin.models import Account
# Importing the related models
from company.models import Company, Branch
from django.utils import timezone
from datetime import timedelta


class Role(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    def create_user(
        self, first_name, last_name, username, email, role, phone_number=None,
        cashier_gl=None, cashier_ac=None, branch=None, password=None
    ):
        if not email:
            raise ValueError('User must have an email address')
        if not username:
            raise ValueError('User must have a username')

        user = self.model(
            email=self.normalize_email(email),
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=role,
            phone_number=phone_number,
            cashier_gl=cashier_gl,
            cashier_ac=cashier_ac,
            branch=branch,  # Assign the branch to the user
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, first_name, last_name, username, email, password=None):
        # Ensure default Company and Branch exist
        default_company, created = Company.objects.get_or_create(
            company_name="Default Company",
            defaults={
                "contact_person": "Admin",
                "office_address": "123 Default Street",
                "contact_phone_no": "1234567890",
                "registration_date": now().date(),
                "expiration_date": now().date().replace(year=now().year + 1),
                "license_key": "DEFAULTLICENSEKEY",
            }
        )
        default_branch, created = Branch.objects.get_or_create(
            company=default_company,
            
            defaults={
                "branch_code":"MAIN",
                "branch_name": "Demo Branch",
                "session_date": now().date(),
                "system_date_date": now().date(),
                "session_status": "Active",
            }
        )

        # Create the superuser
        user = self.create_user(
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=email,
            role=User.SYSTEM_ADMINISTRATOR,
            branch=default_branch,  # Pass the default branch to the user
            phone_number='+2348066311516',
            cashier_gl=None,
            cashier_ac=None,
            password=password,
        )
        user.is_admin = True
        user.is_active = True
        user.is_staff = True
        user.is_superadmin = True
        user.save(using=self._db)
        return user



class User(AbstractBaseUser):
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
    )

    profile_picture = models.ImageField(upload_to='users/profile_pictures', default='images/avatar.jpg')
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    username = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=100, unique=True)
    phone_number = models.CharField(max_length=16, blank=True, null=True)
    role = models.PositiveSmallIntegerField(choices=ROLE_CHOICE, blank=True, null=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True, related_name="users")
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    last_otp_sent = models.DateTimeField(blank=True, null=True)
    cashier_gl = models.CharField(max_length=6, blank=True, null=True)
    cashier_ac = models.CharField(max_length=1, blank=True, null=True)

    # Required fields
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now_add=True)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_superadmin = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    objects = UserManager()

    def __str__(self):
        return self.username

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, app_label):
        return True

    def get_role(self):
        roles = dict(self.ROLE_CHOICE)
        return roles.get(self.role, "Unknown Role")

    def is_otp_valid(self, otp, expiry_minutes=5):
        """Check if OTP matches and is within expiry time"""
        if self.otp_code != otp:
            return False
        if not self.last_otp_sent:
            return False
        if timezone.now() > self.last_otp_sent + timedelta(minutes=expiry_minutes):
            return False
        return True


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True)
    address = models.CharField(max_length=250, blank=True, null=True)
    country = models.CharField(max_length=15, blank=True, null=True)
    state = models.CharField(max_length=15, blank=True, null=True)
    city = models.CharField(max_length=15, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.email


class UserActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    function_used = models.CharField(max_length=255)
    date_time = models.DateTimeField(auto_now_add=True)
    user_agent = models.TextField()

    def __str__(self):
        return f"{self.user.username} - {self.function_used} at {self.date_time}"


class Clients(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    date_of_birth = models.DateField()

    def __str__(self):
        return self.name
