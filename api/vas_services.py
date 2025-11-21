# api/vas_services.py
import requests
import json
import logging
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from typing import Dict, Any, Optional, Tuple
from datetime import timedelta

from .models import (
    VASTransaction, VASProvider, DataPlan, VASCharges, 
    VASTokenCache, BillsCategory, BillsBiller
)
from customers.models import Customer
from transactions.models import Memtrans

logger = logging.getLogger(__name__)


class VASAPIClient:
    """Client for external VAS API"""
    
    def __init__(self):
        self.base_url = getattr(settings, 'VAS_API_BASE_URL', 'https://api.vas-provider.com')
        self.api_key = getattr(settings, 'VAS_API_KEY', '')
        self.api_secret = getattr(settings, 'VAS_API_SECRET', '')
        self.timeout = 30

    def get_auth_token(self) -> str:
        """Get or refresh authentication token"""
        try:
            # Check cached token
            token_cache = VASTokenCache.objects.filter(provider='main').first()
            
            if token_cache and not token_cache.is_expired:
                return token_cache.access_token
            
            # Get new token
            auth_data = {
                'api_key': self.api_key,
                'api_secret': self.api_secret
            }
            
            response = requests.post(
                f"{self.base_url}/auth/token",
                json=auth_data,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            access_token = data['access_token']
            expires_in = data.get('expires_in', 3600)  # Default 1 hour
            expires_at = timezone.now() + timedelta(seconds=expires_in)
            
            # Cache token
            VASTokenCache.objects.update_or_create(
                provider='main',
                defaults={
                    'access_token': access_token,
                    'refresh_token': data.get('refresh_token', ''),
                    'expires_at': expires_at
                }
            )
            
            return access_token
            
        except Exception as e:
            logger.error(f"VAS API auth failed: {str(e)}")
            raise

    def make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """Make authenticated API request"""
        try:
            token = self.get_auth_token()
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            url = f"{self.base_url}/{endpoint.lstrip('/')}"
            
            response = requests.request(
                method=method,
                url=url,
                json=data,
                headers=headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"VAS API request failed: {str(e)}")
            raise

    def detect_network(self, phone_number: str) -> Dict:
        """Detect network provider for phone number"""
        return self.make_request('POST', '/network/detect', {
            'phone_number': phone_number
        })

    def purchase_airtime(self, phone_number: str, amount: float, network: str = None) -> Dict:
        """Purchase airtime"""
        return self.make_request('POST', '/airtime/purchase', {
            'phone_number': phone_number,
            'amount': amount,
            'network': network
        })

    def get_data_plans(self, network: str) -> Dict:
        """Get available data plans for network"""
        return self.make_request('GET', f'/data/plans/{network}')

    def purchase_data(self, phone_number: str, plan_id: str, network: str = None) -> Dict:
        """Purchase data plan"""
        return self.make_request('POST', '/data/purchase', {
            'phone_number': phone_number,
            'plan_id': plan_id,
            'network': network
        })

    def get_transaction_status(self, transaction_ref: str) -> Dict:
        """Get transaction status"""
        return self.make_request('GET', f'/transaction/status/{transaction_ref}')

    def get_bills_categories(self) -> Dict:
        """Get bills payment categories"""
        return self.make_request('GET', '/bills/categories')

    def get_bills_billers(self, category_id: str) -> Dict:
        """Get billers for category"""
        return self.make_request('GET', f'/bills/billers/{category_id}')

    def validate_bill_payment(self, biller_code: str, account_number: str) -> Dict:
        """Validate bill payment details"""
        return self.make_request('POST', '/bills/validate', {
            'biller_code': biller_code,
            'account_number': account_number
        })

    def pay_bill(self, biller_code: str, account_number: str, amount: float, customer_data: Dict = None) -> Dict:
        """Pay bill"""
        return self.make_request('POST', '/bills/pay', {
            'biller_code': biller_code,
            'account_number': account_number,
            'amount': amount,
            'customer_data': customer_data or {}
        })


class VASService:
    """Main VAS service class"""
    
    def __init__(self):
        self.api_client = VASAPIClient()

    def get_or_create_customer(self, phone_number: str) -> Customer:
        """Get or create customer from phone number"""
        # Try to find existing customer by phone
        customer = Customer.objects.filter(phone_number=phone_number).first()
        
        if not customer:
            # Create temporary customer record
            customer = Customer.objects.create(
                phone_number=phone_number,
                first_name='VAS',
                last_name='Customer',
                email=f'vas_{phone_number}@temp.com'
            )
        
        return customer

    def get_account_balance(self, customer: Customer) -> Decimal:
        """Get customer account balance"""
        try:
            # Use the primary account or first available account
            accounts = customer.accounts.filter(is_active=True).order_by('-balance')
            if accounts.exists():
                return accounts.first().balance
            return Decimal('0.00')
        except Exception:
            return Decimal('0.00')

    def calculate_charges(self, transaction_type: str, amount: Decimal) -> Tuple[Decimal, Decimal]:
        """Calculate charges and cashback for transaction"""
        try:
            charge_config = VASCharges.objects.get(
                transaction_type=transaction_type, 
                is_active=True
            )
            charges = Decimal(str(charge_config.calculate_charge(float(amount))))
            cashback = Decimal(str(charge_config.calculate_cashback(float(amount))))
            return charges, cashback
        except VASCharges.DoesNotExist:
            # Default charges
            default_charge = amount * Decimal('0.01')  # 1%
            default_cashback = amount * Decimal('0.005')  # 0.5%
            return default_charge, default_cashback

    def debit_account(self, customer: Customer, amount: Decimal, description: str, reference: str) -> bool:
        """Debit customer account via Memtrans"""
        try:
            # Get primary account
            account = customer.accounts.filter(is_active=True).first()
            if not account:
                raise Exception("No active account found")

            # Check balance
            if account.balance < amount:
                raise Exception("Insufficient balance")

            # Create debit transaction
            memtrans = Memtrans.objects.create(
                customer=customer,
                account_number=f"{account.gl_no}{account.ac_no}",
                transaction_type='DEBIT',
                amount=amount,
                description=description,
                reference=reference,
                status='SUCCESS',
                balance_before=account.balance,
                balance_after=account.balance - amount
            )

            # Update account balance
            account.balance -= amount
            account.save()

            logger.info(f"Account debited: {customer.phone_number} - {amount} - {reference}")
            return True

        except Exception as e:
            logger.error(f"Account debit failed: {str(e)}")
            return False

    def credit_account(self, customer: Customer, amount: Decimal, description: str, reference: str) -> bool:
        """Credit customer account (for reversals/cashback)"""
        try:
            # Get primary account
            account = customer.accounts.filter(is_active=True).first()
            if not account:
                raise Exception("No active account found")

            # Create credit transaction
            memtrans = Memtrans.objects.create(
                customer=customer,
                account_number=f"{account.gl_no}{account.ac_no}",
                transaction_type='CREDIT',
                amount=amount,
                description=description,
                reference=reference,
                status='SUCCESS',
                balance_before=account.balance,
                balance_after=account.balance + amount
            )

            # Update account balance
            account.balance += amount
            account.save()

            logger.info(f"Account credited: {customer.phone_number} - {amount} - {reference}")
            return True

        except Exception as e:
            logger.error(f"Account credit failed: {str(e)}")
            return False

    @transaction.atomic
    def detect_network(self, phone_number: str) -> Dict:
        """Detect network for phone number"""
        try:
            # Call external API
            result = self.api_client.detect_network(phone_number)
            
            return {
                'success': True,
                'network': result.get('network', 'UNKNOWN'),
                'provider': result.get('provider', 'Unknown')
            }
            
        except Exception as e:
            logger.error(f"Network detection failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'network': 'UNKNOWN'
            }

    @transaction.atomic
    def purchase_airtime(self, phone_number: str, amount: Decimal, customer_id: str = None) -> Dict:
        """Purchase airtime"""
        try:
            # Get or create customer
            customer = self.get_or_create_customer(phone_number)
            
            # Calculate charges and cashback
            charges, cashback = self.calculate_charges('AIRTIME', amount)
            total_amount = amount + charges

            # Check balance
            balance = self.get_account_balance(customer)
            if balance < total_amount:
                return {
                    'success': False,
                    'error': 'Insufficient balance',
                    'balance_required': float(total_amount),
                    'current_balance': float(balance)
                }

            # Create transaction record
            vas_transaction = VASTransaction.objects.create(
                customer=customer,
                transaction_type='AIRTIME',
                phone_number=phone_number,
                amount=amount,
                charges=charges,
                total_amount=total_amount,
                cashback_amount=cashback,
                status='PROCESSING'
            )

            # Debit account
            debit_success = self.debit_account(
                customer=customer,
                amount=total_amount,
                description=f"Airtime purchase - {phone_number}",
                reference=vas_transaction.transaction_reference
            )

            if not debit_success:
                vas_transaction.status = 'FAILED'
                vas_transaction.error_message = 'Account debit failed'
                vas_transaction.save()
                return {
                    'success': False,
                    'error': 'Account debit failed',
                    'transaction_id': str(vas_transaction.id)
                }

            try:
                # Call external API
                api_result = self.api_client.purchase_airtime(
                    phone_number=phone_number,
                    amount=float(amount)
                )

                # Update transaction
                vas_transaction.external_reference = api_result.get('reference', '')
                vas_transaction.api_response = api_result
                vas_transaction.network = api_result.get('network', '')

                if api_result.get('success', False):
                    vas_transaction.status = 'SUCCESS'
                    vas_transaction.completed_at = timezone.now()
                    
                    # Credit cashback if applicable
                    if cashback > 0:
                        self.credit_account(
                            customer=customer,
                            amount=cashback,
                            description=f"Airtime cashback - {phone_number}",
                            reference=f"{vas_transaction.transaction_reference}_CB"
                        )
                else:
                    raise Exception(api_result.get('error', 'External API error'))

            except Exception as api_error:
                # Reverse the debit
                self.credit_account(
                    customer=customer,
                    amount=total_amount,
                    description=f"Airtime reversal - {phone_number}",
                    reference=f"{vas_transaction.transaction_reference}_REV"
                )
                
                vas_transaction.status = 'FAILED'
                vas_transaction.error_message = str(api_error)

            vas_transaction.save()

            return {
                'success': vas_transaction.status == 'SUCCESS',
                'transaction_id': str(vas_transaction.id),
                'reference': vas_transaction.transaction_reference,
                'amount': float(amount),
                'charges': float(charges),
                'cashback': float(cashback),
                'status': vas_transaction.status,
                'error': vas_transaction.error_message if vas_transaction.status == 'FAILED' else None
            }

        except Exception as e:
            logger.error(f"Airtime purchase failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_data_plans(self, network: str = None) -> Dict:
        """Get data plans"""
        try:
            if network:
                # Get plans from external API
                api_result = self.api_client.get_data_plans(network)
                plans = api_result.get('plans', [])
            else:
                # Get all cached plans from database
                plans_qs = DataPlan.objects.filter(is_active=True).select_related('provider')
                plans = []
                
                for plan in plans_qs:
                    plans.append({
                        'id': plan.plan_id,
                        'name': plan.name,
                        'description': plan.description,
                        'validity': plan.validity,
                        'price': float(plan.price),
                        'plan_type': plan.plan_type,
                        'is_hot_deal': plan.is_hot_deal,
                        'bonus_description': plan.bonus_description,
                        'cashback_amount': float(plan.cashback_amount),
                        'provider': plan.provider.name
                    })

            return {
                'success': True,
                'plans': plans
            }

        except Exception as e:
            logger.error(f"Get data plans failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'plans': []
            }

    @transaction.atomic
    def purchase_data(self, phone_number: str, plan_id: str, network: str = None, customer_id: str = None) -> Dict:
        """Purchase data plan"""
        try:
            # Get or create customer
            customer = self.get_or_create_customer(phone_number)
            
            # Get data plan
            data_plan = DataPlan.objects.filter(plan_id=plan_id, is_active=True).first()
            if not data_plan:
                return {
                    'success': False,
                    'error': 'Invalid data plan'
                }

            # Calculate charges and cashback
            charges, _ = self.calculate_charges('DATA', data_plan.price)
            cashback = data_plan.cashback_amount
            total_amount = data_plan.price + charges

            # Check balance
            balance = self.get_account_balance(customer)
            if balance < total_amount:
                return {
                    'success': False,
                    'error': 'Insufficient balance',
                    'balance_required': float(total_amount),
                    'current_balance': float(balance)
                }

            # Create transaction record
            vas_transaction = VASTransaction.objects.create(
                customer=customer,
                transaction_type='DATA',
                phone_number=phone_number,
                amount=data_plan.price,
                charges=charges,
                total_amount=total_amount,
                cashback_amount=cashback,
                data_plan=data_plan,
                data_bundle=data_plan.name,
                network=network or data_plan.provider.name,
                status='PROCESSING'
            )

            # Debit account
            debit_success = self.debit_account(
                customer=customer,
                amount=total_amount,
                description=f"Data purchase - {data_plan.name} - {phone_number}",
                reference=vas_transaction.transaction_reference
            )

            if not debit_success:
                vas_transaction.status = 'FAILED'
                vas_transaction.error_message = 'Account debit failed'
                vas_transaction.save()
                return {
                    'success': False,
                    'error': 'Account debit failed',
                    'transaction_id': str(vas_transaction.id)
                }

            try:
                # Call external API
                api_result = self.api_client.purchase_data(
                    phone_number=phone_number,
                    plan_id=plan_id,
                    network=network
                )

                # Update transaction
                vas_transaction.external_reference = api_result.get('reference', '')
                vas_transaction.api_response = api_result

                if api_result.get('success', False):
                    vas_transaction.status = 'SUCCESS'
                    vas_transaction.completed_at = timezone.now()
                    
                    # Credit cashback if applicable
                    if cashback > 0:
                        self.credit_account(
                            customer=customer,
                            amount=cashback,
                            description=f"Data cashback - {data_plan.name}",
                            reference=f"{vas_transaction.transaction_reference}_CB"
                        )
                else:
                    raise Exception(api_result.get('error', 'External API error'))

            except Exception as api_error:
                # Reverse the debit
                self.credit_account(
                    customer=customer,
                    amount=total_amount,
                    description=f"Data reversal - {data_plan.name}",
                    reference=f"{vas_transaction.transaction_reference}_REV"
                )
                
                vas_transaction.status = 'FAILED'
                vas_transaction.error_message = str(api_error)

            vas_transaction.save()

            return {
                'success': vas_transaction.status == 'SUCCESS',
                'transaction_id': str(vas_transaction.id),
                'reference': vas_transaction.transaction_reference,
                'plan': data_plan.name,
                'amount': float(data_plan.price),
                'charges': float(charges),
                'cashback': float(cashback),
                'status': vas_transaction.status,
                'error': vas_transaction.error_message if vas_transaction.status == 'FAILED' else None
            }

        except Exception as e:
            logger.error(f"Data purchase failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_transaction_history(self, customer_id: str = None, transaction_type: str = None, 
                             page: int = 1, per_page: int = 20) -> Dict:
        """Get VAS transaction history"""
        try:
            # Build query
            queryset = VASTransaction.objects.select_related('customer', 'data_plan', 'provider')
            
            if customer_id:
                queryset = queryset.filter(customer_id=customer_id)
            
            if transaction_type:
                queryset = queryset.filter(transaction_type=transaction_type)

            # Pagination
            offset = (page - 1) * per_page
            total_count = queryset.count()
            transactions = list(queryset[offset:offset + per_page])

            # Format response
            transaction_list = []
            for txn in transactions:
                transaction_list.append({
                    'id': str(txn.id),
                    'reference': txn.transaction_reference,
                    'type': txn.transaction_type,
                    'phone_number': txn.phone_number,
                    'network': txn.network,
                    'amount': float(txn.amount),
                    'charges': float(txn.charges),
                    'cashback': float(txn.cashback_amount),
                    'status': txn.status,
                    'data_bundle': txn.data_bundle,
                    'created_at': txn.created_at.isoformat(),
                    'completed_at': txn.completed_at.isoformat() if txn.completed_at else None
                })

            return {
                'success': True,
                'transactions': transaction_list,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'pages': (total_count + per_page - 1) // per_page
                }
            }

        except Exception as e:
            logger.error(f"Get transaction history failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'transactions': []
            }

    def get_bills_categories(self) -> Dict:
        """Get bills payment categories"""
        try:
            categories = BillsCategory.objects.filter(is_active=True).order_by('sort_order', 'name')
            category_list = []
            
            for category in categories:
                category_list.append({
                    'id': category.id,
                    'name': category.name,
                    'code': category.code,
                    'description': category.description,
                    'icon': category.icon,
                    'billers_count': category.billers.filter(is_active=True).count()
                })

            return {
                'success': True,
                'categories': category_list
            }

        except Exception as e:
            logger.error(f"Get bills categories failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'categories': []
            }