import secrets
import hashlib
from datetime import datetime, timedelta
import time
from functools import wraps

from encryption import encryption

def rate_limit(max_attempts=5, timeout=300):
    """A decorator to rate-limit a function based on the 'phone' argument."""
    def decorator(func):
        attempts = {}
        @wraps(func)
        def wrapper(self, phone, *args, **kwargs):
            current_time = time.time()
            if phone in attempts:
                if attempts[phone]['count'] >= max_attempts:
                    if current_time - attempts[phone]['first_attempt'] < timeout:
                        # Raise an exception or return an error tuple
                        return False, f"Too many attempts. Try again in {timeout/60:.0f} minutes."
                    else: # Reset after timeout
                        attempts[phone] = {'count': 1, 'first_attempt': current_time}
                else:
                    attempts[phone]['count'] += 1
            else: # First attempt
                attempts[phone] = {'count': 1, 'first_attempt': current_time}
            return func(self, phone, *args, **kwargs)
        return wrapper
    return decorator

class Security:
    @staticmethod
    def generate_otp():
        """Generate 6-digit OTP"""
        return str(secrets.randbelow(900000) + 100000)
    
    @staticmethod
    def generate_security_code():
        """Generate 6-digit security code"""
        return str(secrets.randbelow(900000) + 100000)
    
    @staticmethod
    def validate_phone(phone):
        """Validate Indian phone number"""
        return len(phone) == 10 and phone.isdigit() and phone[0] in '6789'
    
    @staticmethod
    def validate_amount(amount):
        """Validate investment amount"""
        try:
            amount = float(amount)
            return amount > 0
        except:
            return False
    
    @staticmethod
    def sanitize_input(text):
        """Basic input sanitization"""
        if not text:
            return ""
        # Remove potentially dangerous characters
        dangerous_chars = [';', '"', "'", '<', '>', '&', '|']
        for char in dangerous_chars:
            text = text.replace(char, '')
        return text.strip()
    
    @staticmethod
    def hash_sensitive_data(data):
        """Hash sensitive data for additional protection"""
        if not data:
            return data
        salt = "investkar_salt_2024"
        return hashlib.sha256(f"{data}{salt}".encode()).hexdigest()
    
    @staticmethod
    def validate_encryption():
        """Test if encryption is working"""
        test_data = "test_encryption_data"
        encrypted = encryption.encrypt_string(test_data)
        decrypted = encryption.decrypt_string(encrypted)
        return test_data == decrypted