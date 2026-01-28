from django.contrib import admin
from .models import (
    Merchant, MerchantTransaction, MerchantActivityLog,
    MerchantCommission, MerchantServiceConfig
)


@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = [
        'merchant_id', 'merchant_name', 'merchant_type', 
        'status', 'is_verified', 'created_at'
    ]
    list_filter = ['status', 'merchant_type', 'is_verified', 'branch']
    search_fields = ['merchant_id', 'merchant_name', 'merchant_code', 'business_name']
    readonly_fields = ['uuid', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Identification', {
            'fields': ('uuid', 'merchant_id', 'merchant_code', 'merchant_name', 'merchant_type')
        }),
        ('Business Details', {
            'fields': ('business_name', 'business_address', 'business_phone', 'business_email')
        }),
        ('Contact Person', {
            'fields': ('contact_person_name', 'contact_person_phone', 'contact_person_email')
        }),
        ('Location', {
            'fields': ('state', 'lga', 'city', 'address')
        }),
        ('Account Links', {
            'fields': ('branch', 'user', 'customer', 'float_gl_no', 'float_ac_no')
        }),
        ('Limits & Commission', {
            'fields': ('daily_transaction_limit', 'single_transaction_limit', 'commission_rate')
        }),
        ('Status', {
            'fields': ('status', 'is_verified', 'verified_by', 'verified_at', 'activated_by', 'activated_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'created_by')
        }),
    )


@admin.register(MerchantTransaction)
class MerchantTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_ref', 'merchant', 'transaction_type',
        'amount', 'status', 'created_at'
    ]
    list_filter = ['transaction_type', 'status', 'created_at']
    search_fields = ['transaction_ref', 'merchant__merchant_name', 'customer_name']
    readonly_fields = ['uuid', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(MerchantActivityLog)
class MerchantActivityLogAdmin(admin.ModelAdmin):
    list_display = ['merchant', 'activity_type', 'description', 'ip_address', 'created_at']
    list_filter = ['activity_type', 'created_at']
    search_fields = ['merchant__merchant_name', 'description']
    readonly_fields = ['uuid', 'created_at']
    date_hierarchy = 'created_at'


@admin.register(MerchantCommission)
class MerchantCommissionAdmin(admin.ModelAdmin):
    list_display = ['merchant', 'amount', 'rate', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['merchant__merchant_name']
    readonly_fields = ['uuid', 'created_at']


@admin.register(MerchantServiceConfig)
class MerchantServiceConfigAdmin(admin.ModelAdmin):
    list_display = [
        'service_type', 'is_enabled', 'charge_type', 
        'charge_value', 'commission_value', 'branch'
    ]
    list_filter = ['service_type', 'is_enabled', 'branch']
    readonly_fields = ['uuid', 'created_at', 'updated_at']
