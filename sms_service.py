# sms_service.py
import requests
import os
import json
from kivy.logger import Logger

class SMSService:
    def __init__(self):
        # The API key is now set here. For production, use environment variables.
        self.api_key = os.environ.get('FAST2SMS_API_KEY')
        self.sender_id = 'FSTSSM'  # Fast2SMS default sender ID
    
    def send_otp(self, phone, otp, security_code):
        """Send OTP via Fast2SMS API"""
        try:
            # Using the real SMS sending method.
            # To switch back to demo mode, comment the line below and uncomment the demo line.
            return self._send_otp_real(phone, otp, security_code)
            # return self._send_otp_demo(phone, otp, security_code)
            
        except Exception as e:
            Logger.error(f"SMS Service: Failed to send OTP - {str(e)}")
            return {'return': False, 'message': str(e)}
    
    def _send_otp_real(self, phone, otp, security_code):
        """Real SMS sending implementation"""
        if not self.api_key:
            Logger.error("SMS Service: FAST2SMS_API_KEY environment variable not set.")
            return {
                'return': False, 
                'message': 'SMS service is not configured by the administrator.'
            }
        
        url = "https://www.fast2sms.com/dev/bulkV2"
        
        # Format message
        message = f"Your Invest karo verification code is {otp}. Security Code: {security_code}. Do not share with anyone."
        
        payload = {
            "sender_id": self.sender_id,
            "message": message,
            "route": "v3",
            "numbers": phone
        }
        
        headers = {
            'authorization': self.api_key,
            'Content-Type': "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        result = response.json()
        
        Logger.info(f"SMS Service: API Response - {result}")
        
        if result.get('return'):
            return {
                'return': True,
                'message': 'OTP sent successfully',
                'request_id': result.get('request_id')
            }
        else:
            return {
                'return': False,
                'message': result.get('message', 'Failed to send OTP')
            }
    
    def _send_otp_demo(self, phone, otp, security_code):
        """Demo mode - shows OTP in popup instead of sending real SMS"""
        Logger.info(f"SMS Service: DEMO - Would send to {phone}: OTP={otp}, Security={security_code}")
        
        return {
            'return': True,
            'message': 'OTP generated (Demo Mode)',
            'demo': True,
            'otp': otp,
            'security_code': security_code
        }

# Global instance
sms_service = SMSService()