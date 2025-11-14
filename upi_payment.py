# upi_payment.py
import webbrowser
from urllib.parse import quote
from kivy.logger import Logger
from datetime import datetime

class SimpleUPIPayment:
    def __init__(self):
        # YOUR PhonePe UPI ID
        self.upi_id = "9308691451@ybl"  # ✅ Your actual UPI ID (from context)
        self.merchant_name = "Invest Kar"
        self.support_phone = "9308691451"  # Your phone for support (from context)
    
    def generate_upi_payment_link(self, amount, transaction_id, description):
        """Generate UPI payment link for any UPI app"""
        try:
            # URL encode parameters
            encoded_name = quote(self.merchant_name)
            encoded_desc = quote(description)
            
            # Create UPI payment link
            upi_link = f"upi://pay?pa={self.upi_id}&pn={encoded_name}&am={amount}&tn={encoded_desc}&tr={transaction_id}&cu=INR"
            
            Logger.info(f"UPI Payment Link Generated: {upi_link}")
            return upi_link
            
        except Exception as e:
            Logger.error(f"UPI Link Generation Error: {str(e)}")
            return None
    
    def generate_investment_payment(self, amount, user_phone, method, user_id, plan_id):
        """Generate UPI payment for investment"""
        try:
            # Generate transaction ID
            transaction_id = f"INV{int(datetime.now().timestamp())}{user_id}"
            
            description = f"Investment in Plan {plan_id} - User {user_id}"
            
            upi_link = self.generate_upi_payment_link(
                amount=amount,
                transaction_id=transaction_id,
                description=description
            )
            
            if upi_link:
                return {
                    'success': True,
                    'payment_url': upi_link,
                    'transaction_id': transaction_id,
                    'upi_id': self.upi_id,
                    'message': f'Pay ₹{amount} to {self.upi_id} for investment'
                }
            else:
                return {'success': False, 'message': 'Failed to generate payment link'}
            
        except Exception as e:
            Logger.error(f"Investment UPI Error: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    def generate_withdrawal_payment(self, amount, user_phone, method, user_id):
        """Generate UPI payment for withdrawal fee"""
        try:
            withdrawal_fee = 10  # ₹10 withdrawal fee
            
            transaction_id = f"WD{int(datetime.now().timestamp())}{user_id}"
            description = f"Withdrawal fee - User {user_id}"
            
            upi_link = self.generate_upi_payment_link(
                amount=withdrawal_fee,
                transaction_id=transaction_id,
                description=description
            )
            
            if upi_link:
                return {
                    'success': True,
                    'payment_url': upi_link,
                    'transaction_id': transaction_id,
                    'upi_id': self.upi_id,
                    'message': f'Pay ₹{withdrawal_fee} withdrawal fee to {self.upi_id}'
                }
            else:
                return {'success': False, 'message': 'Failed to generate payment link'}
            
        except Exception as e:
            Logger.error(f"Withdrawal UPI Error: {str(e)}")
            return {'success': False, 'message': str(e)}

# Global instance
upi_payment = SimpleUPIPayment()