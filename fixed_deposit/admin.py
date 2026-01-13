from django.contrib import admin
from .models import (
    FixedDeposit, FixedDepositHist, FDProduct, FDInterestSlab, 
    FDInterestAccrual, FDRenewalHistory
)


@admin.register(FixedDeposit)
class FixedDepositAdmin(admin.ModelAdmin):
    list_display = ['fixed_ac_no', 'customer', 'deposit_amount', 'interest_rate', 
                    'tenure_months', 'start_date', 'maturity_date', 'status']
    list_filter = ['status', 'interest_type', 'auto_renewal', 'is_lien_marked', 'tds_applicable']
    search_fields = ['fixed_ac_no', 'customer__first_name', 'customer__last_name', 'certificate_number']
    readonly_fields = ['uuid', 'interest_amount', 'maturity_amount', 'accrued_interest', 
                       'created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('uuid', 'customer', 'branch', 'fd_product', 'cycle')
        }),
        ('Account Details', {
            'fields': ('cust_gl_no', 'cust_ac_no', 'fixed_gl_no', 'fixed_ac_no', 
                       'fixed_int_gl_no', 'fixed_int_ac_no')
        }),
        ('Deposit Details', {
            'fields': ('deposit_amount', 'interest_rate', 'tenure_months', 
                       'start_date', 'maturity_date', 'status')
        }),
        ('Interest Calculation', {
            'fields': ('interest_type', 'compound_frequency', 'interest_option',
                       'interest_amount', 'maturity_amount', 'accrued_interest', 'interest_paid')
        }),
        ('Senior Citizen', {
            'fields': ('is_senior_citizen', 'senior_citizen_extra_rate'),
            'classes': ('collapse',)
        }),
        ('TDS', {
            'fields': ('tds_applicable', 'tds_rate', 'tds_deducted'),
            'classes': ('collapse',)
        }),
        ('Premature Withdrawal', {
            'fields': ('premature_penalty_rate', 'penalty_amount'),
            'classes': ('collapse',)
        }),
        ('Auto Renewal', {
            'fields': ('auto_renewal', 'renewal_count', 'original_fd'),
            'classes': ('collapse',)
        }),
        ('Nominee Details', {
            'fields': ('nominee_name', 'nominee_relationship', 'nominee_phone', 
                       'nominee_address', 'nominee_id_type', 'nominee_id_number', 'nominee_percentage'),
            'classes': ('collapse',)
        }),
        ('Lien', {
            'fields': ('is_lien_marked', 'lien_amount', 'lien_reference', 'lien_date'),
            'classes': ('collapse',)
        }),
        ('Certificate', {
            'fields': ('certificate_number', 'certificate_issued', 'certificate_issue_date'),
            'classes': ('collapse',)
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at', 'created_by', 'last_interest_calc_date', 'remarks'),
            'classes': ('collapse',)
        }),
    )


@admin.register(FixedDepositHist)
class FixedDepositHistAdmin(admin.ModelAdmin):
    list_display = ['fixed_ac_no', 'trx_date', 'trx_type', 'trx_no', 'principal', 'interest']
    list_filter = ['trx_type', 'trx_date']
    search_fields = ['fixed_ac_no', 'trx_no']


@admin.register(FDProduct)
class FDProductAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'product_code', 'base_interest_rate', 'min_deposit', 
                    'max_deposit', 'interest_type', 'is_active']
    list_filter = ['is_active', 'interest_type', 'tds_applicable', 'allow_premature_withdrawal']
    search_fields = ['product_name', 'product_code']


@admin.register(FDInterestSlab)
class FDInterestSlabAdmin(admin.ModelAdmin):
    list_display = ['product', 'min_amount', 'max_amount', 'min_tenure', 'max_tenure', 'interest_rate']
    list_filter = ['product']


@admin.register(FDInterestAccrual)
class FDInterestAccrualAdmin(admin.ModelAdmin):
    list_display = ['fixed_deposit', 'accrual_date', 'accrued_amount', 'cumulative_accrued', 'is_paid']
    list_filter = ['accrual_date', 'is_paid']
    search_fields = ['fixed_deposit__fixed_ac_no']


@admin.register(FDRenewalHistory)
class FDRenewalHistoryAdmin(admin.ModelAdmin):
    list_display = ['original_fd', 'renewal_date', 'renewal_type', 'original_principal', 
                    'renewed_principal', 'is_auto_renewal']
    list_filter = ['renewal_type', 'is_auto_renewal', 'renewal_date']
    search_fields = ['original_fd__fixed_ac_no']
