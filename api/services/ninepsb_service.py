"""
9PSB Service Implementation - Based on Official API Documentation
This implementation uses the exact endpoints and payload formats from the official docs

Base URL: https://baastest.9psb.com.ng/ipaymw-api/v1
"""

import hashlib
import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class NinePsbServiceCorrected:
    """
    9PSB Service implementation based on official API documentation
    """
    
    BASE_URL = 'https://baastest.9psb.com.ng/ipaymw-api/v1'
    TIMEOUT = 30
    MAX_RETRIES = 3
    
    def __init__(self, public_key: str = None, private_key: str = None):
        """
        Initialize 9PSB service with credentials
        
        Args:
            public_key: Client public key from 9PSB (optional, defaults to Django settings)
            private_key: Client private key from 9PSB (optional, defaults to Django settings)
        """
        self.public_key = public_key or getattr(settings, 'PSB_PUBLIC_KEY', '')
        self.private_key = private_key or getattr(settings, 'PSB_PRIVATE_KEY', '')
        self.access_token = None
        self.token_expires_at = None
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                     headers: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make HTTP request to 9PSB API with retry logic
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        default_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        if headers:
            default_headers.update(headers)
        
        if self.access_token:
            default_headers['Authorization'] = f'Bearer {self.access_token}'
        
        logger.info(f"🔗 Making {method} request to: {url}")
        if data:
            logger.info(f"📤 Request payload: {json.dumps(data, indent=2)}")
        
        for attempt in range(self.MAX_RETRIES):
            try:
                if method.upper() == 'GET':
                    response = requests.get(url, headers=default_headers, timeout=self.TIMEOUT)
                elif method.upper() == 'POST':
                    response = requests.post(
                        url, 
                        json=data, 
                        headers=default_headers, 
                        timeout=self.TIMEOUT
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                logger.info(f"📡 Response status: {response.status_code}")
                logger.info(f"📄 Response body: {response.text}")
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return {
                        'success': False,
                        'error': f'Endpoint not found (404): {url}',
                        'suggestion': 'Check if the endpoint path is correct'
                    }
                elif response.status_code == 401:
                    return {
                        'success': False,
                        'error': 'Unauthorized (401): Invalid or expired token',
                        'suggestion': 'Re-authenticate to get a new token'
                    }
                else:
                    return {
                        'success': False,
                        'error': f'HTTP {response.status_code}: {response.text}',
                        'statusCode': response.status_code
                    }
                    
            except requests.exceptions.Timeout:
                logger.warning(f"⏰ Request timeout (attempt {attempt + 1}/{self.MAX_RETRIES})")
                if attempt == self.MAX_RETRIES - 1:
                    return {
                        'success': False,
                        'error': 'Request timeout after all retries',
                        'suggestion': 'Check network connectivity'
                    }
            except requests.exceptions.ConnectionError as e:
                logger.warning(f"🔌 Connection error (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                if attempt == self.MAX_RETRIES - 1:
                    return {
                        'success': False,
                        'error': f'Connection error: {str(e)}',
                        'suggestion': 'Check internet connectivity and API availability'
                    }
            except Exception as e:
                logger.error(f"💥 Unexpected error: {e}")
                return {
                    'success': False,
                    'error': f'Unexpected error: {str(e)}'
                }
        
        return {
            'success': False,
            'error': 'Max retries exceeded'
        }
    
    def authenticate(self) -> Dict[str, Any]:
        """
        Authenticate with 9PSB API
        
        Returns:
            Dict containing authentication result
        """
        # Check cached token first
        cached_token = cache.get('psb_access_token')
        if cached_token:
            self.access_token = cached_token
            logger.info("🔐 Using cached authentication token")
            return {'success': True, 'token': cached_token}
            
        logger.info("🔐 Authenticating with 9PSB API...")
        
        if not self.public_key or not self.private_key:
            return {'success': False, 'error': 'PSB credentials not configured in Django settings'}
        
        payload = {
            'publickey': self.public_key,
            'privatekey': self.private_key
        }
        
        response = self._make_request('POST', '/merchant/authenticate', payload)
        
        if 'access_token' in response:
            self.access_token = response['access_token']
            # Token expires in seconds (usually 7200 = 2 hours)
            expires_in = response.get('expires_in', 7200)
            self.token_expires_at = datetime.now().timestamp() + expires_in
            
            # Cache token for slightly less than expiry time
            cache.set('psb_access_token', self.access_token, expires_in - 60)
            
            logger.info("✅ Authentication successful!")
            return {
                'success': True,
                'message': 'Authentication successful',
                'token': self.access_token,
                'expires_in': expires_in
            }
        elif response.get('code') == 'S1':
            return {
                'success': False,
                'error': 'Invalid credentials',
                'code': response.get('code'),
                'message': response.get('message')
            }
        elif response.get('code') == '96':
            return {
                'success': False,
                'error': 'System malfunction',
                'code': response.get('code'),
                'message': response.get('message')
            }
        else:
            return response
    
    def account_enquiry(self, account_number: str, bank_code: str) -> Dict[str, Any]:
        """
        Perform account enquiry
        
        Args:
            account_number: Customer's account number
            bank_code: Customer's bank code
            
        Returns:
            Dict containing account details
        """
        logger.info(f"🔍 Account enquiry for {account_number} at bank {bank_code}")
        
        # Ensure we're authenticated
        if not self.access_token:
            auth_result = self.authenticate()
            if not auth_result.get('success'):
                return auth_result
        
        payload = {
            'customer': {
                'account': {
                    'number': account_number,
                    'bank': bank_code
                }
            }
        }
        
        response = self._make_request('POST', '/merchant/account/enquiry', payload)
        
        if response.get('code') == '00':
            logger.info("✅ Account enquiry successful!")
            return {
                'success': True,
                'account': response['customer']['account'],
                'code': response['code'],
                'message': response['message']
            }
        elif response.get('code') == '07':
            return {
                'success': False,
                'error': 'Invalid account',
                'code': response['code'],
                'message': response['message']
            }
        elif response.get('code') == '16':
            return {
                'success': False,
                'error': 'Unknown bank code',
                'code': response['code'],
                'message': response['message']
            }
        else:
            return response
    
    def get_bank_list(self) -> Dict[str, Any]:
        """
        Get list of available banks
        
        Returns:
            Dict containing bank list
        """
        logger.info("🏦 Getting bank list...")
        
        # Note: Bank list endpoint doesn't require authentication according to docs
        response = self._make_request('POST', '/merchant/transfer/getbanks')
        
        if response.get('code') == '00':
            bank_list = response.get('BankList', [])
            logger.info(f"✅ Retrieved {len(bank_list)} banks")
            
            return {
                'success': True,
                'banks': bank_list,
                'count': len(bank_list),
                'code': response['code'],
                'message': response['message']
            }
        else:
            return response
    
    def balance_enquiry(self, account_number: str) -> Dict[str, Any]:
        """
        Get account balance
        
        Args:
            account_number: Customer's account number
            
        Returns:
            Dict containing balance information
        """
        logger.info(f"💰 Balance enquiry for account {account_number}")
        
        # Ensure we're authenticated
        if not self.access_token:
            auth_result = self.authenticate()
            if not auth_result.get('success'):
                return auth_result
        
        payload = {
            'account': {
                'accountnumber': account_number
            }
        }
        
        response = self._make_request('POST', '/merchant/account/balanceenquiry', payload)
        
        if response.get('code') == '00':
            logger.info("✅ Balance enquiry successful!")
            return {
                'success': True,
                'account': response['account'],
                'code': response['code'],
                'message': response['message']
            }
        elif response.get('code') == '07':
            return {
                'success': False,
                'error': 'Invalid account',
                'code': response['code'],
                'message': response['message']
            }
        else:
            return response
    
    def _generate_fund_transfer_hash(self, sender_account: str, recipient_account: str, 
                                   bank_code: str, amount: Decimal, reference: str) -> str:
        """
        Generate hash for fund transfer as per documentation
        
        Format: privateKey + senderAccount + recipientAccount + bankCode + amount + reference
        """
        # Format amount to 2 decimal places
        amount_str = f"{amount:.2f}"
        
        raw_data = (
            f"{self.private_key}"
            f"{sender_account}"
            f"{recipient_account}"
            f"{bank_code}"
            f"{amount_str}"
            f"{reference}"
        )
        
        logger.info(f"🔒 Hash composition: privatekey+{sender_account}+{recipient_account}+{bank_code}+{amount_str}+{reference}")
        logger.info(f"🔒 Raw hash data length: {len(raw_data)} characters")
        logger.debug(f"🔒 Full raw hash data (SENSITIVE): {raw_data}")
        
        # Generate SHA512 hash
        hash_object = hashlib.sha512(raw_data.encode('utf-8'))
        hash_result = hash_object.hexdigest().upper()
        
        logger.info(f"🔒 Generated hash: {hash_result[:20]}...{hash_result[-20:]} (truncated for security)")
        
        return hash_result
    
    def fund_transfer(self, reference: str, amount: Decimal, currency: str, 
                     description: str, country: str, recipient_account: str, 
                     recipient_bank: str, recipient_name: str, sender_account: str, 
                     sender_name: str) -> Dict[str, Any]:
        """
        Perform fund transfer
        
        Args:
            reference: Unique transaction reference (max 30 chars)
            amount: Transfer amount
            currency: Currency code (e.g., 'NGN')
            description: Transaction description
            country: Country code (e.g., 'NGA')
            recipient_account: Recipient's account number
            recipient_bank: Recipient's bank code
            recipient_name: Recipient's name
            sender_account: Sender's account number
            sender_name: Sender's name
            
        Returns:
            Dict containing transfer result
        """
        logger.info(f"💸 Fund transfer: {amount} {currency} to {recipient_account}")
        
        # Ensure we're authenticated
        if not self.access_token:
            auth_result = self.authenticate()
            if not auth_result.get('success'):
                return auth_result
        
        # Generate hash
        hash_value = self._generate_fund_transfer_hash(
            sender_account, recipient_account, recipient_bank, amount, reference
        )
        
        payload = {
            'transaction': {
                'reference': reference
            },
            'order': {
                'amount': float(amount),
                'currency': currency,
                'description': description,
                'country': country
            },
            'customer': {
                'account': {
                    'number': recipient_account,
                    'bank': recipient_bank,
                    'name': recipient_name,
                    'senderaccountnumber': sender_account,
                    'sendername': sender_name
                }
            },
            'hash': hash_value
        }
        
        response = self._make_request('POST', '/merchant/account/transfer', payload)
        
        if response.get('code') == '00':
            logger.info("✅ Fund transfer successful!")
            return {
                'success': True,
                'transaction': response['transaction'],
                'code': response['code'],
                'message': response['message']
            }
        elif response.get('code') == '03':
            return {
                'success': False,
                'error': 'Invalid Sender - Account may not be authorized for transfers',
                'code': response['code'],
                'message': response['message']
            }
        elif response.get('code') == '72':
            return {
                'success': False,
                'error': 'Customer debit failed - Insufficient funds',
                'code': response['code'],
                'message': response['message']
            }
        elif response.get('code') == '12':
            return {
                'success': False,
                'error': 'Invalid transaction',
                'code': response['code'],
                'message': response['message']
            }
        elif response.get('code') == '07':
            return {
                'success': False,
                'error': 'Invalid account',
                'code': response['code'],
                'message': response['message']
            }
        elif response.get('code') == '74':
            return {
                'success': False,
                'error': 'Invalid message signature (hash mismatch)',
                'code': response['code'],
                'message': response['message']
            }
        else:
            return response
    
    def transfer_status_query(self, reference: str, linking_reference: str = None, 
                            external_reference: str = None) -> Dict[str, Any]:
        """
        Query transfer status
        
        Args:
            reference: Transaction reference
            linking_reference: Optional linking reference
            external_reference: Optional external reference
            
        Returns:
            Dict containing status result
        """
        logger.info(f"🔍 Transfer status query for reference: {reference}")
        
        # Ensure we're authenticated
        if not self.access_token:
            auth_result = self.authenticate()
            if not auth_result.get('success'):
                return auth_result
        
        # Build query parameters
        params = {'reference': reference}
        if linking_reference:
            params['linkingreference'] = linking_reference
        if external_reference:
            params['externalreference'] = external_reference
        
        # Make GET request with query parameters
        url = f"{self.BASE_URL}/merchant/account/transfer/status"
        
        logger.info(f"🔗 Making GET request to: {url}")
        logger.info(f"📤 Query params: {params}")
        
        try:
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.access_token}'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=self.TIMEOUT)
            
            logger.info(f"📡 Response status: {response.status_code}")
            logger.info(f"📄 Response body: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '00':
                    logger.info("✅ Transfer status query successful!")
                    return {
                        'success': True,
                        'transaction': data['transaction'],
                        'order': data['order'],
                        'customer': data['customer'],
                        'code': data['code'],
                        'message': data['message']
                    }
                else:
                    return data
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}: {response.text}',
                    'statusCode': response.status_code
                }
                
        except Exception as e:
            logger.error(f"💥 Transfer status query error: {e}")
            return {
                'success': False,
                'error': f'Transfer status query failed: {str(e)}'
            }


# Singleton instance for use across the application
ninepsb_service = NinePsbServiceCorrected()