from rest_framework import serializers

# Adjust import paths if your app labels differ
from accounts.models import Role, User, UserProfile
from company.models import Company, Branch
from accounts_admin.models import Account_Officer, Region
from customers.models import Customer, KYCDocument
from loans.models import Loans, LoanHist
from transactions.models import Memtrans

from .helpers import normalize_account



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

class MemtransSerializer(serializers.ModelSerializer):
    class Meta:
        model = Memtrans
        fields = '__all__'





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
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Automatically link to current user
        user = self.context['request'].user
        return Beneficiary.objects.create(user=user, **validated_data)






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
from transactions.models import Memtrans  # Import from transactions app

class MemtransSerializer(serializers.ModelSerializer):
    # Your Memtrans model already has the perfect field names!
    trx_no = serializers.CharField()
    trx_type = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    sys_date = serializers.DateTimeField()
    description = serializers.CharField()
    
    class Meta:
        model = Memtrans
        fields = ['trx_no', 'trx_type', 'amount', 'sys_date', 'description']