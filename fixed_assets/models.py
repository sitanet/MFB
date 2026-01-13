import uuid
from django.db import models
from accounts_admin.models import Account
from datetime import date, timedelta
from decimal import Decimal
from profit_solutions.tenant_managers import TenantManager

class AssetType(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class AssetGroup(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class AssetClass(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name


class AssetLocation(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Department(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Officer(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class DepreciationMethod(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    method = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.method


from datetime import date
from decimal import Decimal
from django.core.exceptions import ValidationError

from company.models import Branch

from decimal import Decimal  # ✅ Import Decimal for precision

from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from company.models import Branch
from accounts_admin.models import Account
from .models import AssetType, AssetGroup, AssetClass, AssetLocation, Department, Officer, DepreciationMethod

class FixedAsset(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    DEPRECIATION_FREQUENCY_CHOICES = [
        ('12', 'Monthly'),
        ('4', 'Quarterly'),
        ('2', 'Semi-Annually'),
        ('1', 'Annually'),
    ]

    asset_name = models.CharField(max_length=255)
    asset_type = models.ForeignKey(AssetType, on_delete=models.PROTECT)
    asset_group = models.ForeignKey(AssetGroup, on_delete=models.PROTECT)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT)
    gl_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='gl_accounts')
    ac_no = models.CharField(max_length=50)  # Ensure it's populated correctly
    asset_id = models.CharField(max_length=50, unique=True, db_index=True)
    asset_serial_no = models.CharField(max_length=100, unique=True, db_index=True)
    asset_model_no = models.CharField(max_length=100, blank=True, null=True)
    asset_class = models.ForeignKey(AssetClass, on_delete=models.PROTECT)
    asset_location = models.ForeignKey(AssetLocation, on_delete=models.PROTECT)
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    officer = models.ForeignKey(Officer, on_delete=models.PROTECT)
    date_of_purchase = models.DateField()
    assigned_date = models.DateField(blank=True, null=True)
    asset_cost = models.DecimalField(max_digits=15, decimal_places=2)
    bank_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='bank_accounts')
    allowance_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='allowance_accounts')
    expense_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='expense_accounts')
    asset_life_months = models.PositiveIntegerField()
    minimum_asset_cost = models.DecimalField(max_digits=15, decimal_places=2)
    residual_value = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    depreciation_method = models.ForeignKey(DepreciationMethod, on_delete=models.PROTECT)
    depreciation_rate = models.DecimalField(max_digits=5, decimal_places=2)
    depreciation_frequency = models.CharField(max_length=10, choices=DEPRECIATION_FREQUENCY_CHOICES, default='12')
    total_depreciation = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    is_disposed = models.BooleanField(default=False)

    # Foreign keys to Account model for profit and loss GL accounts
    fixed_asset_profit_gl = models.ForeignKey(
        Account, related_name="profit_gl", on_delete=models.SET_NULL, null=True, blank=True
    )
    fixed_asset_loss_gl = models.ForeignKey(
        Account, related_name="loss_gl", on_delete=models.SET_NULL, null=True, blank=True
    )

    # Blank fields for manually entered account numbers (not ForeignKeys)
    fixed_asset_profit_ac_no = models.CharField(max_length=50, blank=True, null=True)
    fixed_asset_loss_ac_no = models.CharField(max_length=50, blank=True, null=True)

    @property
    def net_book_value(self):
        """Calculate Net Book Value (NBV) dynamically."""
        return max(self.asset_cost - self.total_depreciation, Decimal("0.00"))

    def clean(self):
        """Ensure valid financial constraints."""
        if self.residual_value > self.asset_cost:
            raise ValidationError("Residual value cannot be greater than asset cost.")
        if self.depreciation_rate <= 0:
            raise ValidationError("Depreciation rate must be greater than zero.")
        if self.asset_life_months <= 0:
            raise ValidationError("Asset life must be greater than zero.")

    def update_depreciation(self, amount):
        """Updates total depreciation and saves the asset."""
        self.total_depreciation += amount
        self.save()

    def save(self, *args, **kwargs):
        """Ensure asset is marked as disposed only when needed."""
        if self.is_disposed and not self.pk:
            raise ValidationError("Cannot manually set asset as disposed.")
        super().save(*args, **kwargs)

    # Tenant-aware manager
    objects = TenantManager()
    all_objects = models.Manager()

    def __str__(self):
        return f"{self.asset_id} - {self.asset_name} ({self.asset_type}) (Disposed: {self.is_disposed})"



from django.utils.timezone import now
class AssetRevaluation(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    asset = models.ForeignKey(FixedAsset, on_delete=models.CASCADE, related_name="revaluations")
    previous_value = models.DecimalField(max_digits=15, decimal_places=2)
    new_value = models.DecimalField(max_digits=15, decimal_places=2)
    previous_residual = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    new_residual = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0.00"))
    reason = models.TextField(blank=True, null=True)
    revaluation_date = models.DateField(default=now)

    def __str__(self):
        return f"Revaluation for {self.asset.asset_name} on {self.revaluation_date}"












class AssetTransaction(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    # Transaction Details
    asset = models.ForeignKey(FixedAsset, on_delete=models.CASCADE, related_name="transactions")
    transaction_date = models.DateField()
    transaction_type = models.CharField(max_length=50)  # e.g., Purchase, Depreciation, Disposal
    transaction_amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"AssetTransaction - {self.asset.asset_name} - {self.transaction_type}"



from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal

class AssetDisposal(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    asset = models.OneToOneField("FixedAsset", on_delete=models.CASCADE, related_name="disposal")
    disposal_date = models.DateField(default=timezone.now)
    disposal_price = models.DecimalField(max_digits=15, decimal_places=2)
    disposal_reason = models.TextField()

    @property
    def net_book_value(self):
        """Get the Net Book Value (NBV) at the time of disposal."""
        return max(self.asset.asset_cost - self.asset.total_depreciation, self.asset.residual_value)

    @property
    def gain_or_loss(self):
        """Calculate profit or loss on disposal."""
        return self.disposal_price - self.net_book_value

    def clean(self):
        """Validation to ensure correct disposal process."""
        if self.asset.is_disposed:
            raise ValidationError("This asset has already been disposed and cannot be disposed again.")
        if self.asset.total_depreciation >= self.asset.asset_cost:
            raise ValidationError("Asset is fully depreciated and cannot be disposed.")
        if self.disposal_price < Decimal("0.00"):
            raise ValidationError("Disposal price cannot be negative.")
        if self.disposal_price > self.asset.asset_cost:
            raise ValidationError("Disposal price cannot exceed the original asset cost.")

    def save(self, *args, **kwargs):
        """Mark the asset as disposed and save the disposal record."""
        self.clean()  # Ensuring all validations run before saving
        self.asset.is_disposed = True
        self.asset.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Disposal of {self.asset.asset_name} on {self.disposal_date} (Gain/Loss: {self.gain_or_loss})"


class AssetTransfer(models.Model):
    """Track asset transfers between branches, departments, locations, or officers"""
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    asset = models.ForeignKey("FixedAsset", on_delete=models.CASCADE, related_name="transfers")
    transfer_date = models.DateField(default=timezone.now)
    
    # From
    from_branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="transfers_out", null=True, blank=True)
    from_department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="transfers_out", null=True, blank=True)
    from_location = models.ForeignKey(AssetLocation, on_delete=models.PROTECT, related_name="transfers_out", null=True, blank=True)
    from_officer = models.ForeignKey(Officer, on_delete=models.PROTECT, related_name="transfers_out", null=True, blank=True)
    
    # To
    to_branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name="transfers_in", null=True, blank=True)
    to_department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="transfers_in", null=True, blank=True)
    to_location = models.ForeignKey(AssetLocation, on_delete=models.PROTECT, related_name="transfers_in", null=True, blank=True)
    to_officer = models.ForeignKey(Officer, on_delete=models.PROTECT, related_name="transfers_in", null=True, blank=True)
    
    reason = models.TextField(blank=True, null=True)
    approved_by = models.CharField(max_length=100, blank=True, null=True)
    transfer_document = models.FileField(upload_to='asset_transfers/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        # Update asset with new values
        if self.to_branch:
            self.asset.branch = self.to_branch
        if self.to_department:
            self.asset.department = self.to_department
        if self.to_location:
            self.asset.asset_location = self.to_location
        if self.to_officer:
            self.asset.officer = self.to_officer
        self.asset.save()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Transfer of {self.asset.asset_name} on {self.transfer_date}"


class AssetImpairment(models.Model):
    """Track asset impairments (write-downs in value)"""
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    asset = models.ForeignKey("FixedAsset", on_delete=models.CASCADE, related_name="impairments")
    impairment_date = models.DateField(default=timezone.now)
    previous_nbv = models.DecimalField(max_digits=15, decimal_places=2)
    impairment_loss = models.DecimalField(max_digits=15, decimal_places=2)
    new_nbv = models.DecimalField(max_digits=15, decimal_places=2)
    reason = models.TextField()
    approved_by = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        # Update asset total_depreciation to reflect impairment
        self.asset.total_depreciation += self.impairment_loss
        self.asset.save()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Impairment of {self.asset.asset_name}: {self.impairment_loss}"


class AssetInsurance(models.Model):
    """Track insurance policies for assets"""
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    asset = models.ForeignKey("FixedAsset", on_delete=models.CASCADE, related_name="insurances")
    policy_number = models.CharField(max_length=100)
    insurance_company = models.CharField(max_length=200)
    coverage_type = models.CharField(max_length=100, choices=[
        ('comprehensive', 'Comprehensive'),
        ('fire', 'Fire'),
        ('theft', 'Theft'),
        ('all_risk', 'All Risk'),
        ('other', 'Other'),
    ])
    coverage_amount = models.DecimalField(max_digits=15, decimal_places=2)
    premium_amount = models.DecimalField(max_digits=15, decimal_places=2)
    start_date = models.DateField()
    expiry_date = models.DateField()
    is_active = models.BooleanField(default=True)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    policy_document = models.FileField(upload_to='asset_insurance/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Insurance {self.policy_number} for {self.asset.asset_name}"
    
    @property
    def is_expired(self):
        return date.today() > self.expiry_date
    
    @property
    def days_to_expiry(self):
        return (self.expiry_date - date.today()).days


class AssetMaintenance(models.Model):
    """Track maintenance and service records for assets"""
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    asset = models.ForeignKey("FixedAsset", on_delete=models.CASCADE, related_name="maintenances")
    maintenance_type = models.CharField(max_length=50, choices=[
        ('preventive', 'Preventive Maintenance'),
        ('corrective', 'Corrective Maintenance'),
        ('emergency', 'Emergency Repair'),
        ('upgrade', 'Upgrade/Enhancement'),
        ('inspection', 'Inspection'),
        ('calibration', 'Calibration'),
    ])
    maintenance_date = models.DateField()
    next_maintenance_date = models.DateField(blank=True, null=True)
    description = models.TextField()
    performed_by = models.CharField(max_length=200)  # Vendor or internal staff
    cost = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    parts_replaced = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=[
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], default='completed')
    invoice_number = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    document = models.FileField(upload_to='asset_maintenance/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-maintenance_date']
    
    def __str__(self):
        return f"{self.get_maintenance_type_display()} for {self.asset.asset_name} on {self.maintenance_date}"


class AssetWarranty(models.Model):
    """Track warranty information for assets"""
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    asset = models.ForeignKey("FixedAsset", on_delete=models.CASCADE, related_name="warranties")
    warranty_provider = models.CharField(max_length=200)
    warranty_type = models.CharField(max_length=50, choices=[
        ('manufacturer', 'Manufacturer Warranty'),
        ('extended', 'Extended Warranty'),
        ('service', 'Service Contract'),
        ('parts', 'Parts Warranty'),
    ])
    start_date = models.DateField()
    expiry_date = models.DateField()
    coverage_details = models.TextField()
    terms_and_conditions = models.TextField(blank=True, null=True)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    warranty_document = models.FileField(upload_to='asset_warranty/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Warranty for {self.asset.asset_name} until {self.expiry_date}"
    
    @property
    def is_expired(self):
        return date.today() > self.expiry_date
    
    @property
    def days_to_expiry(self):
        return (self.expiry_date - date.today()).days


class AssetVerification(models.Model):
    """Track physical verification/audit of assets"""
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    asset = models.ForeignKey("FixedAsset", on_delete=models.CASCADE, related_name="verifications")
    verification_date = models.DateField()
    verified_by = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=[
        ('verified', 'Verified - Asset Found'),
        ('not_found', 'Not Found'),
        ('damaged', 'Found - Damaged'),
        ('relocated', 'Found - Different Location'),
    ])
    physical_condition = models.CharField(max_length=20, choices=[
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('unusable', 'Unusable'),
    ], blank=True, null=True)
    actual_location = models.ForeignKey(AssetLocation, on_delete=models.SET_NULL, null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)
    photo = models.ImageField(upload_to='asset_verification/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-verification_date']
    
    def __str__(self):
        return f"Verification of {self.asset.asset_name} on {self.verification_date}"
