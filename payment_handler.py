import time
from datetime import datetime
import webbrowser
from kivy.clock import Clock

class SmartPaymentSystem:
    def __init__(self, upi_id, phone_number):
        self.upi_id = upi_id
        self.phone_number = phone_number
        self.pending_payments = {}
        
    def generate_investment_payment(self, amount, user_phone, method):
        """Generate payment for investment"""
        transaction_id = f"INV{int(time.time())}{user_phone[-4:]}"
        
        if method == "phonepe":
            payment_url = f"phonepe://pay?pa={self.upi_id}&am={amount}&pn=Investkaro&tn=Investment"
        elif method == "googlepay":
            payment_url = f"tez://upi/pay?pa={self.upi_id}&am={amount}&pn=Investkaro&tn=Investment"
        else:
            payment_url = f"upi://pay?pa={self.upi_id}&am={amount}&pn=Investkaro"
        
        # Store pending payment
        self.pending_payments[transaction_id] = {
            'type': 'investment',
            'amount': amount,
            'user_phone': user_phone,
            'timestamp': datetime.now(),
            'status': 'pending'
        }
        
        return {
            'success': True,
            'payment_url': payment_url,
            'transaction_id': transaction_id,
            'message': f'Pay ₹{amount} to {self.upi_id} for investment'
        }
    
    def generate_withdrawal_payment(self, amount, user_phone, method):
        """Generate payment for withdrawal"""
        transaction_id = f"WD{int(time.time())}{user_phone[-4:]}"
        
        if method == "phonepe":
            payment_url = f"phonepe://pay?pa={self.upi_id}&am={amount}&pn=Investkaro&tn=Withdrawal"
        elif method == "googlepay":
            payment_url = f"tez://upi/pay?pa={self.upi_id}&am={amount}&pn=Investkaro&tn=Withdrawal"
        else:
            payment_url = f"upi://pay?pa={self.upi_id}&am={amount}&pn=Investkaro&tn=Withdrawal"
        
        # Store pending payment
        self.pending_payments[transaction_id] = {
            'type': 'withdrawal',
            'amount': amount,
            'user_phone': user_phone,
            'timestamp': datetime.now(),
            'status': 'pending'
        }
        
        return {
            'success': True,
            'payment_url': payment_url,
            'transaction_id': transaction_id,
            'message': f'Pay ₹{amount} to {self.upi_id} to complete withdrawal'
        }
    
# Initialize with YOUR details
payment_system = SmartPaymentSystem(
    upi_id="your-upi-id@provider",  # ⚠️ CHANGE THIS to your actual UPI ID
    phone_number="your-phone-number"     # ⚠️ CHANGE THIS to your actual phone number
)