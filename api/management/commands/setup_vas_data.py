# api/management/commands/setup_vas_data.py
from django.core.management.base import BaseCommand
from api.models import (
    VASProvider, DataPlan, VASCharges, 
    BillsCategory, BillsBiller
)

class Command(BaseCommand):
    help = 'Setup sample VAS data'

    def handle(self, *args, **options):
        self.stdout.write('Setting up VAS data...')
        
        # Create providers
        providers_data = [
            {'name': 'MTN', 'code': 'MTN', 'api_endpoint': 'https://api.mtn.com'},
            {'name': 'AIRTEL', 'code': 'AIRTEL', 'api_endpoint': 'https://api.airtel.com'},
            {'name': 'GLO', 'code': 'GLO', 'api_endpoint': 'https://api.glo.com'},
            {'name': '9MOBILE', 'code': '9MOBILE', 'api_endpoint': 'https://api.9mobile.com'},
        ]
        
        for provider_data in providers_data:
            provider, created = VASProvider.objects.get_or_create(
                code=provider_data['code'],
                defaults=provider_data
            )
            if created:
                self.stdout.write(f'Created provider: {provider.name}')

        # Create sample data plans
        mtn = VASProvider.objects.get(code='MTN')
        data_plans = [
            # HOT deals
            {'provider': mtn, 'plan_id': 'MTN_HOT_1GB', 'name': '1GB', 'validity': '1 Day', 'price': 500, 'plan_type': 'HOT', 'is_hot_deal': True, 'bonus_description': '1GB+1.5mins', 'cashback_percentage': 2.0},
            {'provider': mtn, 'plan_id': 'MTN_HOT_2_5GB', 'name': '2.5GB', 'validity': '2 Days', 'price': 900, 'plan_type': 'HOT', 'is_hot_deal': True, 'cashback_percentage': 2.0},
            
            # Daily plans
            {'provider': mtn, 'plan_id': 'MTN_DAILY_500MB', 'name': '500MB', 'validity': '1 Day', 'price': 200, 'plan_type': 'DAILY', 'cashback_percentage': 2.5},
            {'provider': mtn, 'plan_id': 'MTN_DAILY_1GB', 'name': '1GB', 'validity': '1 Day', 'price': 350, 'plan_type': 'DAILY', 'cashback_percentage': 2.0},
            
            # Weekly plans
            {'provider': mtn, 'plan_id': 'MTN_WEEKLY_1GB', 'name': '1GB', 'validity': '7 Days', 'price': 800, 'plan_type': 'WEEKLY', 'cashback_percentage': 2.0},
            {'provider': mtn, 'plan_id': 'MTN_WEEKLY_2GB', 'name': '2GB', 'validity': '7 Days', 'price': 1200, 'plan_type': 'WEEKLY', 'cashback_percentage': 2.0},
            
            # Monthly plans
            {'provider': mtn, 'plan_id': 'MTN_MONTHLY_2GB', 'name': '2GB', 'validity': '30 Days', 'price': 1500, 'plan_type': 'MONTHLY', 'cashback_percentage': 2.0},
            {'provider': mtn, 'plan_id': 'MTN_MONTHLY_5GB', 'name': '5GB', 'validity': '30 Days', 'price': 3000, 'plan_type': 'MONTHLY', 'cashback_percentage': 2.0},
            
            # XtraValue plans
            {'provider': mtn, 'plan_id': 'MTN_XTRA_15GB', 'name': '15GB', 'validity': '30 Days', 'price': 8000, 'plan_type': 'XTRAVALUE', 'bonus_description': '5GB+10mins', 'cashback_percentage': 2.0},
            {'provider': mtn, 'plan_id': 'MTN_XTRA_25GB', 'name': '25GB', 'validity': '30 Days', 'price': 12000, 'plan_type': 'XTRAVALUE', 'bonus_description': '10GB+20mins', 'cashback_percentage': 2.0},
        ]
        
        for plan_data in data_plans:
            plan, created = DataPlan.objects.get_or_create(
                provider=plan_data['provider'],
                plan_id=plan_data['plan_id'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(f'Created data plan: {plan.name}')

        # Create VAS charges
        charges_data = [
            {'transaction_type': 'AIRTIME', 'fixed_charge': 10.00, 'percentage_charge': 0.0, 'cashback_percentage': 2.0},
            {'transaction_type': 'DATA', 'fixed_charge': 25.00, 'percentage_charge': 0.0, 'cashback_percentage': 2.0},
            {'transaction_type': 'ELECTRICITY', 'fixed_charge': 50.00, 'percentage_charge': 0.0, 'cashback_percentage': 1.0},
            {'transaction_type': 'CABLE_TV', 'fixed_charge': 30.00, 'percentage_charge': 0.0, 'cashback_percentage': 1.5},
        ]
        
        for charge_data in charges_data:
            charge, created = VASCharges.objects.get_or_create(
                transaction_type=charge_data['transaction_type'],
                defaults=charge_data
            )
            if created:
                self.stdout.write(f'Created charges for: {charge.transaction_type}')

        # Create bills categories
        categories_data = [
            {'name': 'Electricity', 'code': 'ELECTRICITY', 'icon': 'electrical_services', 'sort_order': 1},
            {'name': 'Cable TV', 'code': 'CABLE_TV', 'icon': 'tv', 'sort_order': 2},
            {'name': 'Internet', 'code': 'INTERNET', 'icon': 'wifi', 'sort_order': 3},
            {'name': 'Water Bills', 'code': 'WATER', 'icon': 'water_drop', 'sort_order': 4},
            {'name': 'Sports Betting', 'code': 'BETTING', 'icon': 'sports_soccer', 'sort_order': 5},
            {'name': 'Insurance', 'code': 'INSURANCE', 'icon': 'security', 'sort_order': 6},
        ]
        
        for cat_data in categories_data:
            category, created = BillsCategory.objects.get_or_create(
                code=cat_data['code'],
                defaults=cat_data
            )
            if created:
                self.stdout.write(f'Created category: {category.name}')

        # Create sample billers
        electricity_cat = BillsCategory.objects.get(code='ELECTRICITY')
        cabletv_cat = BillsCategory.objects.get(code='CABLE_TV')
        
        billers_data = [
            {'category': electricity_cat, 'name': 'AEDC', 'code': 'AEDC', 'minimum_amount': 1000, 'maximum_amount': 500000},
            {'category': electricity_cat, 'name': 'EKEDC', 'code': 'EKEDC', 'minimum_amount': 1000, 'maximum_amount': 500000},
            {'category': electricity_cat, 'name': 'IKEDC', 'code': 'IKEDC', 'minimum_amount': 1000, 'maximum_amount': 500000},
            {'category': cabletv_cat, 'name': 'DStv', 'code': 'DSTV', 'minimum_amount': 2000, 'maximum_amount': 50000},
            {'category': cabletv_cat, 'name': 'GOtv', 'code': 'GOTV', 'minimum_amount': 1000, 'maximum_amount': 20000},
        ]
        
        for biller_data in billers_data:
            biller, created = BillsBiller.objects.get_or_create(
                code=biller_data['code'],
                defaults=biller_data
            )
            if created:
                self.stdout.write(f'Created biller: {biller.name}')

        self.stdout.write(self.style.SUCCESS('VAS data setup completed!'))