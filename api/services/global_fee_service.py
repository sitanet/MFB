# api/services/global_fee_service.py
from decimal import Decimal
from datetime import date, datetime
from typing import Dict, Optional
from django.utils import timezone

# CORRECTED IMPORTS - Use relative imports to go up one level to api.models
from ..models import GlobalTransferFeeConfiguration, CustomerTransferUsage

class GlobalTransferFeeService:
    """
    Service for managing GLOBAL transfer fees that apply to ALL customers
    
    Key Principles:
    1. Fee amounts are GLOBAL and apply to ALL customers equally
    2. Only free transfer allowances are tracked per customer
    3. Only ONE active fee configuration exists at any time
    """
    
    @staticmethod
    def get_active_fee_configuration(transfer_type: str = 'other_bank') -> Optional[GlobalTransferFeeConfiguration]:
        """Get the currently active global fee configuration"""
        try:
            return GlobalTransferFeeConfiguration.objects.get(
                transfer_type=transfer_type,
                is_active=True
            )
        except GlobalTransferFeeConfiguration.DoesNotExist:
            return None
    
    @staticmethod
    def calculate_fee_for_any_customer(customer_id: str, transfer_amount: Decimal, 
                                     transfer_type: str = 'other_bank') -> Dict:
        """
        Calculate transfer fee for ANY customer using GLOBAL configuration
        
        This method applies the SAME fee logic to ALL customers
        
        Returns:
            {
                'base_fee': Decimal,           # Same for ALL customers
                'applied_fee': Decimal,        # What this customer pays (may be waived)
                'is_waived': bool,
                'waiver_reason': str,
                'remaining_free_today': int,
                'remaining_free_month': int,
                'fee_gl_no': str,              # Same for ALL customers  
                'fee_ac_no': str,              # Same for ALL customers
                'config_name': str
            }
        """
        
        # Get the GLOBAL fee configuration (applies to ALL customers)
        fee_config = GlobalTransferFeeService.get_active_fee_configuration(transfer_type)
        
        if not fee_config:
            return {
                'base_fee': Decimal('0.00'),
                'applied_fee': Decimal('0.00'),
                'is_waived': True,
                'waiver_reason': 'No global fee configuration active',
                'remaining_free_today': 999,
                'remaining_free_month': 999,
                'fee_gl_no': '',
                'fee_ac_no': '',
                'config_name': 'No Configuration'
            }
        
        today = date.today()
        current_month = today.strftime('%Y-%m')
        
        # Get customer's usage (for free allowance tracking only)
        usage, created = CustomerTransferUsage.objects.get_or_create(
            customer_id=customer_id,
            date=today,
            defaults={
                'month': current_month,
                'daily_transfer_count': 0,
                'monthly_transfer_count': 0
            }
        )
        
        # Get monthly usage for this customer
        monthly_usage = CustomerTransferUsage.objects.filter(
            customer_id=customer_id,
            month=current_month
        ).first()
        
        monthly_count = monthly_usage.monthly_transfer_count if monthly_usage else 0
        
        # Calculate remaining free transfers for THIS customer
        remaining_free_today = max(0, fee_config.free_transfers_per_day - usage.daily_transfer_count)
        remaining_free_month = max(0, fee_config.free_transfers_per_month - monthly_count)
        
        # GLOBAL fee amount (SAME for ALL customers)
        base_fee = fee_config.base_fee
        applied_fee = base_fee
        is_waived = False
        waiver_reason = ''
        
        # Apply GLOBAL fee rules (SAME logic for ALL customers)
        
        # Rule 1: Amount below minimum threshold (applies to ALL)
        if transfer_amount < fee_config.min_amount_for_fee:
            is_waived = True
            waiver_reason = f'Amount below ₦{fee_config.min_amount_for_fee} minimum'
            applied_fee = Decimal('0.00')
        
        # Rule 2: Daily free transfers (individual customer allowance)
        elif remaining_free_today > 0:
            is_waived = True
            waiver_reason = f'Free daily transfer {usage.daily_transfer_count + 1} of {fee_config.free_transfers_per_day}'
            applied_fee = Decimal('0.00')
        
        # Rule 3: Monthly free transfers (individual customer allowance)
        elif remaining_free_month > 0:
            is_waived = True
            waiver_reason = f'Free monthly transfer {monthly_count + 1} of {fee_config.free_transfers_per_month}'
            applied_fee = Decimal('0.00')
        
        # Rule 4: Large amount daily limit (applies to ALL)
        elif usage.daily_transfer_amount + transfer_amount > fee_config.max_daily_free_amount:
            # Customer has exceeded daily free amount limit
            # Fee applies (no waiver)
            waiver_reason = ''
        
        return {
            'base_fee': base_fee,                      # GLOBAL: same for all
            'applied_fee': applied_fee,                # What THIS customer pays
            'is_waived': is_waived,
            'waiver_reason': waiver_reason,
            'remaining_free_today': remaining_free_today,
            'remaining_free_month': remaining_free_month,
            'fee_gl_no': fee_config.fee_gl_no,         # GLOBAL: same for all
            'fee_ac_no': fee_config.fee_ac_no,         # GLOBAL: same for all
            'config_name': fee_config.name,
            'fee_config_id': fee_config.id
        }
    
    @staticmethod
    def update_customer_usage_after_transfer(customer_id: str, transfer_amount: Decimal, 
                                           fee_paid: Decimal) -> None:
        """
        Update individual customer usage tracking after successful transfer
        NOTE: This only updates usage counts - fee amounts remain GLOBAL
        """
        
        today = date.today()
        current_month = today.strftime('%Y-%m')
        
        # Update daily usage for this customer
        usage, created = CustomerTransferUsage.objects.get_or_create(
            customer_id=customer_id,
            date=today,
            defaults={'month': current_month}
        )
        
        usage.daily_transfer_count += 1
        usage.daily_transfer_amount += transfer_amount
        usage.daily_fees_paid += fee_paid
        usage.save()
        
        # Update monthly usage for this customer
        monthly_usage, created = CustomerTransferUsage.objects.get_or_create(
            customer_id=customer_id,
            month=current_month,
            date=today,
            defaults={}
        )
        
        monthly_usage.monthly_transfer_count += 1
        monthly_usage.monthly_transfer_amount += transfer_amount
        monthly_usage.monthly_fees_paid += fee_paid
        monthly_usage.save()
    
    @staticmethod
    def get_fee_summary_for_all_customers() -> Dict:
        """Get summary of fee configuration that applies to ALL customers"""
        
        fee_config = GlobalTransferFeeService.get_active_fee_configuration()
        
        if not fee_config:
            return {'error': 'No active fee configuration'}
        
        return {
            'config_name': fee_config.name,
            'base_fee': str(fee_config.base_fee),
            'applies_to': 'ALL CUSTOMERS',
            'free_per_day': fee_config.free_transfers_per_day,
            'free_per_month': fee_config.free_transfers_per_month,
            'min_amount': str(fee_config.min_amount_for_fee),
            'fee_collection_gl': fee_config.fee_gl_no,
            'fee_collection_ac': fee_config.fee_ac_no,
            'is_active': fee_config.is_active,
            'effective_date': fee_config.effective_date.isoformat()
        }
    
    @staticmethod
    def create_global_fee_configuration(config_data: Dict) -> GlobalTransferFeeConfiguration:
        """
        Create new global fee configuration (will apply to ALL customers)
        Automatically deactivates any existing configuration
        """
        
        # Deactivate existing configurations
        GlobalTransferFeeConfiguration.objects.filter(
            transfer_type=config_data.get('transfer_type', 'other_bank'),
            is_active=True
        ).update(is_active=False)
        
        # Create new global configuration
        new_config = GlobalTransferFeeConfiguration.objects.create(
            name=config_data.get('name', 'Other Bank Transfer Fee'),
            transfer_type=config_data.get('transfer_type', 'other_bank'),
            base_fee=Decimal(str(config_data.get('base_fee', '10.00'))),
            free_transfers_per_day=config_data.get('free_transfers_per_day', 3),
            free_transfers_per_month=config_data.get('free_transfers_per_month', 10),
            fee_gl_no=config_data.get('fee_gl_no', ''),
            fee_ac_no=config_data.get('fee_ac_no', ''),
            min_amount_for_fee=Decimal(str(config_data.get('min_amount_for_fee', '100.00'))),
            max_daily_free_amount=Decimal(str(config_data.get('max_daily_free_amount', '50000.00'))),
            created_by=config_data.get('created_by', 'Admin'),
            is_active=True
        )
        
        return new_config