import requests
import logging
from django.conf import settings
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class TermiiSMSService:
    """Service for sending SMS via Termii API"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'TERMII_API_KEY', None)
        self.sender_id = getattr(settings, 'TERMII_SENDER_ID', 'FinanceFlex')
        self.sms_url = getattr(settings, 'TERMII_SMS_URL', 'https://api.ng.termii.com/api/sms/send')
        
    def send_sms(self, phone_number: str, message: str) -> Dict[str, Any]:
        """
        Send SMS via Termii API
        
        Args:
            phone_number: Recipient phone number (e.g., '2348012345678')
            message: SMS message content
            
        Returns:
            dict: Response from Termii API
        """
        if not self.api_key:
            logger.error("TERMII_API_KEY not configured")
            return {
                'success': False,
                'error': 'SMS service not configured',
                'message_id': None
            }
        
        # Format phone number for Nigerian numbers
        formatted_phone = self._format_phone_number(phone_number)
        
        payload = {
            "to": formatted_phone,
            "from": self.sender_id,
            "sms": message,
            "type": "plain",
            "api_key": self.api_key,
            "channel": "generic"
        }
        
        try:
            logger.info(f"Sending SMS to {formatted_phone[:8]}****")
            
            response = requests.post(
                self.sms_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get('message') == 'Successfully Sent':
                logger.info(f"SMS sent successfully to {formatted_phone[:8]}****. Message ID: {response_data.get('message_id')}")
                return {
                    'success': True,
                    'message_id': response_data.get('message_id'),
                    'balance': response_data.get('balance'),
                    'user': response_data.get('user')
                }
            else:
                logger.error(f"SMS failed: {response_data}")
                return {
                    'success': False,
                    'error': response_data.get('message', 'SMS sending failed'),
                    'response': response_data
                }
                
        except requests.exceptions.Timeout:
            logger.error("SMS request timeout")
            return {
                'success': False,
                'error': 'SMS service timeout',
                'message_id': None
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"SMS request failed: {str(e)}")
            return {
                'success': False,
                'error': f'SMS service error: {str(e)}',
                'message_id': None
            }
        except Exception as e:
            logger.error(f"Unexpected SMS error: {str(e)}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}',
                'message_id': None
            }
    
    def _format_phone_number(self, phone_number: str) -> str:
        """
        Format phone number for Nigerian mobile numbers
        
        Args:
            phone_number: Input phone number in various formats
            
        Returns:
            str: Formatted phone number with country code
        """
        # Remove all non-digits
        digits_only = ''.join(filter(str.isdigit, phone_number))
        
        # Handle different input formats
        if digits_only.startswith('234'):
            # Already has country code
            return digits_only
        elif digits_only.startswith('0'):
            # Nigerian format starting with 0 (e.g., 08012345678)
            return '234' + digits_only[1:]
        elif len(digits_only) == 10:
            # 10-digit format (e.g., 8012345678)
            return '234' + digits_only
        else:
            # Return as-is if format is unclear
            return digits_only
    
    def send_otp_sms(self, phone_number: str, otp_code: str, expires_in_minutes: int = 5) -> Dict[str, Any]:
        """
        Send OTP via SMS with standard message format
        
        Args:
            phone_number: Recipient phone number
            otp_code: 6-digit OTP code
            expires_in_minutes: OTP expiry time in minutes
            
        Returns:
            dict: SMS sending result
        """
        message = (
            f"Your FinanceFlex verification code is: {otp_code}\n\n"
            f"This code expires in {expires_in_minutes} minutes. "
            f"Do not share this code with anyone.\n\n"
            f"If you didn't request this, please ignore this message."
        )
        
        return self.send_sms(phone_number, message)

# Global instance
sms_service = TermiiSMSService()