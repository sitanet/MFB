from rest_framework import serializers

# Adjust import paths if your app labels differ
from accounts.models import Role, User, UserProfile
from company.models import Company, Branch
from accounts_admin.models import Account_Officer, Region
from customers.models import Customer, KYCDocument
from loans.models import Loans, LoanHist
from transactions.models import Memtrans

from .helpers import normalize_account
from datetime import date
from django.utils import timezone



class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role', read_only=True)

    class Meta:
        model = User
        exclude = ['password']  # don’t expose password hash

class UserWriteSerializer(serializers.ModelSerializer):
    # Allow password set on create/update
    class Meta:
        model = User
        fields = [
            'id','email','username','first_name','last_name','phone_number','role','branch',
            'cashier_gl','cashier_ac','activation_code','customer','is_active'
        ]

    def create(self, validated_data):
        password = self.initial_data.get('password')
        instance = super().create(validated_data)
        if password:
            instance.set_password(password)
            instance.save(update_fields=['password'])
        return instance

    def update(self, instance, validated_data):
        password = self.initial_data.get('password')
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save(update_fields=['password'])
        return instance

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = '__all__'

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = '__all__'

class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = '__all__'

class AccountOfficerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account_Officer
        fields = '__all__'

class CustomerSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = Customer
        fields = '__all__'

class KYCDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCDocument
        fields = '__all__'

class LoansSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loans
        fields = '__all__'

class LoanHistSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanHist
        fields = '__all__'

# class MemtransSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Memtrans
#         fields = '__all__'





from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    confirm_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = self.context["request"].user
        old = attrs.get("old_password")
        new = attrs.get("new_password")
        confirm = attrs.get("confirm_password")

        if not user.check_password(old):
            raise serializers.ValidationError({"old_password": "Current password is incorrect."})

        if new != confirm:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        validate_password(new, user=user)  # uses Django’s password validators
        return attrs



from decimal import Decimal
from rest_framework import serializers


class TransferToFinanceFlexSerializer(serializers.Serializer):
    from_gl_no = serializers.CharField(max_length=10)
    from_ac_no = serializers.CharField(max_length=10)
    to_gl_no = serializers.CharField(max_length=10)
    to_ac_no = serializers.CharField(max_length=10)
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0.01"))
    narration = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=255)

    def validate(self, attrs):
        from_gl = str(attrs.get("from_gl_no", "")).strip()
        from_ac = str(attrs.get("from_ac_no", "")).strip()
        to_gl = str(attrs.get("to_gl_no", "")).strip()
        to_ac = str(attrs.get("to_ac_no", "")).strip()

        if not from_gl or not from_ac:
            raise serializers.ValidationError({"detail": "Source account (GL/AC) is required."})
        if not to_gl or not to_ac:
            raise serializers.ValidationError({"detail": "Destination account (GL/AC) is required."})

        if from_gl == to_gl and from_ac == to_ac:
            raise serializers.ValidationError({"detail": "Cannot transfer to the same account."})

        attrs["from_gl_no"] = from_gl
        attrs["from_ac_no"] = from_ac
        attrs["to_gl_no"] = to_gl
        attrs["to_ac_no"] = to_ac
        return attrs
from rest_framework import serializers
from .models import Beneficiary

class BeneficiarySerializer(serializers.ModelSerializer):
    # 🔧 FIXED: Make these fields writable for POST requests
    # Accept Flutter field names for input, but map to Django model fields
    account = serializers.CharField(write_only=True, required=False, help_text="Flutter-compatible field name")
    bank = serializers.CharField(write_only=True, required=False, help_text="Flutter-compatible field name")
    
    # Also accept Django field names directly
    account_number = serializers.CharField(required=False)
    bank_name = serializers.CharField(required=False)
    
    class Meta:
        model = Beneficiary
        fields = [
            'id',
            'name',
            'bank_name',
            'account_number', 
            'phone_number',
            'nickname',
            'created_at',
            'updated_at',
            # Flutter-compatible fields (write_only for input)
            'account',  
            'bank',     
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'name': {'required': True},
            # Make these optional since we'll handle them in validate()
            'bank_name': {'required': False},
            'account_number': {'required': False},
        }

    def validate(self, data):
        """Handle field mapping and validation."""
        print(f"[DEBUG] 🔍 Raw serializer data: {data}")
        
        # 🔧 FIELD MAPPING: Handle both Flutter and Django field names
        
        # Map 'account' to 'account_number' if provided
        if 'account' in data and not data.get('account_number'):
            data['account_number'] = data.pop('account')
            print(f"[DEBUG] 🔄 Mapped 'account' to 'account_number': {data['account_number']}")
        
        # Map 'bank' to 'bank_name' if provided  
        if 'bank' in data and not data.get('bank_name'):
            data['bank_name'] = data.pop('bank')
            print(f"[DEBUG] 🔄 Mapped 'bank' to 'bank_name': {data['bank_name']}")
        
        # Remove any remaining Flutter-only fields
        data.pop('account', None)
        data.pop('bank', None)
        
        # ✅ VALIDATION: Ensure required fields are present after mapping
        if not data.get('account_number'):
            raise serializers.ValidationError({
                'account_number': 'Account number is required (provide as "account" or "account_number")'
            })
        
        if not data.get('bank_name'):
            raise serializers.ValidationError({
                'bank_name': 'Bank name is required (provide as "bank" or "bank_name")'
            })
        
        if not data.get('name'):
            raise serializers.ValidationError({
                'name': 'Name is required'
            })
        
        # 🔧 VALIDATION: Account number format
        account_number = data.get('account_number')
        if account_number:
            clean_account = ''.join(filter(str.isdigit, account_number))
            if len(clean_account) < 8:
                raise serializers.ValidationError({
                    'account_number': 'Account number must be at least 8 digits'
                })
            data['account_number'] = clean_account
        
        # 🔧 VALIDATION: Unique beneficiary per user (for creates only)
        if not self.instance:  # Creating new beneficiary
            user = self.context['request'].user
            if Beneficiary.objects.filter(user=user, account_number=data['account_number']).exists():
                raise serializers.ValidationError({
                    'account_number': 'This beneficiary already exists in your list'
                })
        
        print(f"[DEBUG] ✅ Final validated data: {data}")
        return data

    def create(self, validated_data):
        """Create beneficiary with current user."""
        user = self.context['request'].user
        print(f"[DEBUG] 💾 Creating beneficiary for user {user.username}: {validated_data}")
        return Beneficiary.objects.create(user=user, **validated_data)

    def to_representation(self, instance):
        """Customize output format for GET requests."""
        data = super().to_representation(instance)
        # Add Flutter-compatible fields for GET requests
        data['account'] = instance.account_number
        data['bank'] = instance.bank_name
        return data

# --- PIN serializers (append to file) ---
import re
from rest_framework import serializers

PIN_REGEX = re.compile(r"^\d{4}$")


class PinSetSerializer(serializers.Serializer):
    current_pin = serializers.CharField(required=False, allow_blank=True, write_only=True)
    pin = serializers.CharField(write_only=True, max_length=4, min_length=4)
    confirm_pin = serializers.CharField(write_only=True, max_length=4, min_length=4)

    def validate(self, attrs):
        pin = attrs.get("pin")
        confirm_pin = attrs.get("confirm_pin")
        if pin != confirm_pin:
            raise serializers.ValidationError({"confirm_pin": "PIN and confirmation do not match."})
        if not PIN_REGEX.match(pin):
            raise serializers.ValidationError({"pin": "PIN must be exactly 4 digits."})
        return attrs


class PinVerifySerializer(serializers.Serializer):
    pin = serializers.CharField(write_only=True, max_length=4, min_length=4)

    def validate_pin(self, value):
        if not PIN_REGEX.match(value):
            raise serializers.ValidationError("PIN must be exactly 4 digits.")
        return value






class CardFundSerializer(serializers.Serializer):
    from_gl_no = serializers.CharField()
    from_ac_no = serializers.CharField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)

    def validate(self, data):
        fg, fa = normalize_account(data.get("from_gl_no"), data.get("from_ac_no"))
        amt = data.get("amount")
        if amt is None or amt <= 0:
            raise serializers.ValidationError({"amount": "Amount must be greater than zero"})
        data["from_gl_no"], data["from_ac_no"] = fg, fa
        return data


class CardWithdrawSerializer(serializers.Serializer):
    to_gl_no = serializers.CharField()
    to_ac_no = serializers.CharField()
    amount = serializers.DecimalField(max_digits=18, decimal_places=2)

    def validate(self, data):
        tg, ta = normalize_account(data.get("to_gl_no"), data.get("to_ac_no"))
        amt = data.get("amount")
        if amt is None or amt <= 0:
            raise serializers.ValidationError({"amount": "Amount must be greater than zero"})
        data["to_gl_no"], data["to_ac_no"] = tg, ta
        return data


from decimal import Decimal
from rest_framework import serializers
from customers.models import VirtualCard

class VirtualCardApplySerializer(serializers.Serializer):
    confirm = serializers.BooleanField(default=True)

class VirtualCardApproveSerializer(serializers.Serializer):
    approve = serializers.BooleanField(default=True)

class VirtualCardSerializer(serializers.ModelSerializer):
    last4 = serializers.SerializerMethodField()
    holder = serializers.SerializerMethodField()
    expiry = serializers.SerializerMethodField()

    class Meta:
        model = VirtualCard
        fields = [
            "id", "status",
            "gl_no", "ac_no",
            "last4", "holder", "expiry",
            "created_at", "activated_at",
        ]

    def get_last4(self, obj):
        num = (obj.card_number or "").replace(" ", "")
        return num[-4:] if len(num) >= 4 else ""

    def get_holder(self, obj):
        user = getattr(getattr(obj, "customer", None), "user", None)
        if user:
            name = user.get_full_name()
            return name or user.get_username()
        return ""

    def get_expiry(self, obj):
        mm = str(obj.expiry_month).zfill(2)
        yy = str(obj.expiry_year)[-2:]
        return f"{mm}/{yy}"


# NEW: fund/withdraw payloads
from decimal import Decimal
from rest_framework import serializers



class CardFundSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0.01"))

class CardWithdrawSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0.01"))

from rest_framework import serializers
from transactions.models import Memtrans

from rest_framework import serializers
from transactions.models import Memtrans

class MemtransSerializer(serializers.ModelSerializer):
    """Serializer for Memtrans model with correct date field handling"""
    
    class Meta:
        model = Memtrans
        fields = '__all__'
    
    def to_representation(self, instance):
        """Custom representation using ses_date instead of non-existent date field"""
        
        # Use ses_date as the primary transaction date (your Memtrans model has this field)
        transaction_date = instance.ses_date
        
        return {
            'id': instance.id,
            'amount': float(instance.amount) if instance.amount else 0.0,
            'type': instance.type or 'transaction',
            'description': instance.description or '',
            'date': transaction_date.isoformat() if transaction_date else '',  # FIXED: Using ses_date
            'code': instance.code or '',
            'gl_no': instance.gl_no or '',
            'ac_no': instance.ac_no or '',
            'trx_no': instance.trx_no or '',
        }



from rest_framework import serializers
from customers.models import Customer

class WalletDetailsSerializer(serializers.ModelSerializer):
    """
    Dedicated serializer for wallet details
    """
    account_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Customer
        fields = [
            'wallet_account',  # 🔥 9PSB wallet account
            'bank_name',       # 🔥 9PSB bank name  
            'bank_code',       # Optional bank code
            'account_name',    # Generated from first_name + last_name
            'gl_no', 
            'ac_no'
        ]
    
    def get_account_name(self, obj):
        """Generate account holder name"""
        return f"{obj.first_name} {obj.last_name}".strip() or 'Account Holder'



from rest_framework import serializers
from customers.models import Customer
from company.models import Company

class CustomerDashboardSerializer(serializers.ModelSerializer):
    """
    Enhanced dashboard serializer that includes company float account details
    """
    full_name = serializers.SerializerMethodField()
    float_account_number = serializers.SerializerMethodField()
    wallet_account = serializers.SerializerMethodField()  # ✅ backward compatible alias

    class Meta:
        model = Customer
        fields = [
            'id',
            'first_name',
            'last_name',
            'full_name',
            'email',
            'gl_no',
            'ac_no',
            'float_account_number',  # ✅ new field from company model
            'wallet_account',        # ✅ optional backward compatibility
            'bank_name',
            'bank_code',
            'balance',
        ]

    def get_full_name(self, obj):
        return f"{obj.first_name or ''} {obj.last_name or ''}".strip()

    def get_float_account_number(self, obj):
        """
        Return float_account_number from Company model (shared across system)
        """
        company = Company.objects.first()
        return company.float_account_number if company else None

    def get_wallet_account(self, obj):
        """
        For backward compatibility – same as float_account_number.
        Remove this later when frontend migrates.
        """
        company = Company.objects.first()
        return company.float_account_number if company else None





class CustomerListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for customer lists
    """
    class Meta:
        model = Customer
        fields = [
            'id', 'first_name', 'last_name', 'email',
            'gl_no', 'ac_no', 
            'wallet_account',  # 🔥 Include wallet data
            'bank_name'        # 🔥 Include bank data
        ]








# 1. serializers.py - Add this to your serializers file
from rest_framework import serializers
from loans.models import LoanHist

class LoanHistSerializer(serializers.ModelSerializer):
    """Serializer for LoanHist model - Loan Ledger entries"""
    
    # Computed fields for frontend
    total_amount = serializers.SerializerMethodField()
    is_credit = serializers.SerializerMethodField()
    branch_name = serializers.SerializerMethodField()
    
    class Meta:
        model = LoanHist
        fields = [
            'id',
            'gl_no',
            'ac_no',
            'cycle',
            'period',
            'trx_date',
            'trx_type',
            'trx_naration',
            'trx_no',
            'principal',
            'interest',
            'penalty',
            'total_amount',
            'is_credit',
            'branch_name',
        ]
    
    def get_total_amount(self, obj):
        """Calculate total amount (principal + interest + penalty)"""
        return float(obj.principal + obj.interest + obj.penalty)
    
    def get_is_credit(self, obj):
        """Determine if transaction is credit or debit based on type"""
        # Adjust these based on your transaction types
        credit_types = ['DISBURSEMENT', 'LOAN_DISBURSEMENT', 'PRINCIPAL_WAIVER', 'INTEREST_WAIVER']
        return obj.trx_type.upper() in credit_types
    
    def get_branch_name(self, obj):
        """Get branch name if available"""
        return obj.branch.name if obj.branch else None


class LoanLedgerSummarySerializer(serializers.Serializer):
    """Serializer for loan ledger summary data"""
    total_principal = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_interest = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_penalty = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_disbursed = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_repaid = serializers.DecimalField(max_digits=15, decimal_places=2)
    outstanding_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    transaction_count = serializers.IntegerField()