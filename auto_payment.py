# auto_payment.py
import webbrowser
from urllib.parse import quote
import sqlite3
from kivy.logger import Logger
from kivy.clock import Clock
import time
from datetime import datetime

class AutomatedPayment:
    def __init__(self):
        self.upi_id = "9308691451@ybl"
        self.merchant_name = "Invest Kar"
        self.payment_timeout = 300  # 5 minutes
        
    def generate_upi_deep_link(self, amount, transaction_id, description):
        """Generate UPI deep link with FIXED amount"""
        try:
            encoded_name = quote(self.merchant_name)
            encoded_desc = quote(description)
            
            # UPI deep link with FIXED amount - user CANNOT change
            upi_link = f"upi://pay?pa={self.upi_id}&pn={encoded_name}&am={amount}&tn={encoded_desc}&tr={transaction_id}&cu=INR"
            
            Logger.info(f"UPI Deep Link: {upi_link}")
            return upi_link
            
        except Exception as e:
            Logger.error(f"UPI Deep Link Error: {str(e)}")
            return None
    
    def initiate_auto_payment(self, user_id, plan_id, amount):
        """Start automated payment process"""
        try:
            transaction_id = f"INV{int(time.time())}{user_id}"
            description = f"InvestKar-Plan{plan_id}-User{user_id}"
            
            upi_link = self.generate_upi_deep_link(amount, transaction_id, description)
            
            if upi_link:
                # Store payment intent
                self.store_payment_intent(transaction_id, user_id, plan_id, amount)
                
                return {
                    'success': True,
                    'payment_url': upi_link,
                    'transaction_id': transaction_id,
                    'amount': amount,
                    'user_id': user_id,
                    'plan_id': plan_id
                }
            else:
                return {'success': False, 'message': 'Payment failed to initialize'}
                
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def store_payment_intent(self, transaction_id, user_id, plan_id, amount):
        """Store payment intent for verification"""
        conn = sqlite3.connect("investkar_data.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_intents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT UNIQUE,
                user_id INTEGER,
                plan_id INTEGER,
                amount REAL,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                verified_at TEXT,
                verification_attempts INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        cursor.execute('''
            INSERT OR REPLACE INTO payment_intents 
            (transaction_id, user_id, plan_id, amount, status)
            VALUES (?, ?, ?, ?, 'pending')
        ''', (transaction_id, user_id, plan_id, amount))
        
        conn.commit()
        conn.close()
    
    def start_payment_verification(self, transaction_id, user_id, plan_id, amount):
        """Start automatic payment verification"""
        Logger.info(f"Starting payment verification: {transaction_id}")
        
        def check_payment(dt):
            success = self.verify_payment_automated(transaction_id, user_id, plan_id, amount)
            if success:
                return False  # Stop checking
            return True  # Continue checking
        
        # Check every 10 seconds for 5 minutes
        Clock.schedule_interval(check_payment, 10)
        
        # Auto-stop after 5 minutes
        Clock.schedule_once(lambda dt: self.cleanup_pending_payment(transaction_id), self.payment_timeout)
    
    def verify_payment_automated(self, transaction_id, user_id, plan_id, amount):
        """Automatically verify payment and activate investment"""
        try:
            conn = sqlite3.connect("investkar_data.db")
            cursor = conn.cursor()
            
            # Check if payment is already processed
            cursor.execute('SELECT status FROM payment_intents WHERE transaction_id = ?', (transaction_id,))
            result = cursor.fetchone()
            
            if result and result[0] == 'completed':
                conn.close()
                return True
            
            # In REAL system, you would:
            # 1. Check your bank statement via API
            # 2. Verify UPI transaction via bank webhook
            # 3. Use payment gateway callbacks
            
            # Since we can't automatically detect UPI payments, we'll simulate
            # For now, we'll use a manual trigger that YOU control
            
            # Check if admin has verified this payment
            cursor.execute('''
                SELECT id FROM payment_intents 
                WHERE transaction_id = ? AND status = 'verified'
            ''', (transaction_id,))
            
            verified_result = cursor.fetchone()
            
            if verified_result:
                # PAYMENT VERIFIED - ACTIVATE INVESTMENT
                self.activate_investment(user_id, plan_id, amount, transaction_id)
                
                # Update payment status
                cursor.execute('''
                    UPDATE payment_intents 
                    SET status = 'completed', verified_at = ?
                    WHERE transaction_id = ?
                ''', (datetime.now().isoformat(), transaction_id))
                
                conn.commit()
                conn.close()
                
                Logger.info(f"Payment verified and investment activated: {transaction_id}")
                return True
            
            # Increment verification attempts
            cursor.execute('''
                UPDATE payment_intents 
                SET verification_attempts = verification_attempts + 1 
                WHERE transaction_id = ?
            ''', (transaction_id,))
            
            conn.commit()
            conn.close()
            return False
            
        except Exception as e:
            Logger.error(f"Payment verification error: {str(e)}")
            return False
    
    def activate_investment(self, user_id, plan_id, amount, transaction_id):
        """Activate investment and add first day return"""
        try:
            conn = sqlite3.connect("investkar_data.db")
            cursor = conn.cursor()
            
            # Calculate returns based on plan
            plan_returns = {1: 0.04, 2: 0.04, 3: 0.05}  # 4%, 4%, 5%
            daily_return_rate = plan_returns.get(plan_id, 0.04)
            daily_return = amount * daily_return_rate
            
            plan_days = {1: 80, 2: 110, 3: 150}
            total_days = plan_days.get(plan_id, 80)
            
            # Add investment
            cursor.execute('''
                INSERT INTO investments 
                (user_id, plan_id, amount, daily_return, total_days, days_remaining, payment_method, status)
                VALUES (?, ?, ?, ?, ?, ?, 'upi_auto', 'active')
            ''', (user_id, plan_id, amount, daily_return, total_days, total_days))
            
            # Add first day return to wallet IMMEDIATELY
            cursor.execute('''
                UPDATE users SET wallet_balance = wallet_balance + ? 
                WHERE id = ?
            ''', (daily_return, user_id))
            
            # Record transactions
            cursor.execute('''
                INSERT INTO transactions (user_id, type, amount, description, status)
                VALUES (?, 'investment', ?, 'Auto UPI Investment', 'completed')
            ''', (user_id, amount))
            
            cursor.execute('''
                INSERT INTO transactions (user_id, type, amount, description, status)
                VALUES (?, 'return', ?, 'First day return - Auto', 'completed')
            ''', (user_id, daily_return))
            
            conn.commit()
            conn.close()
            
            Logger.info(f"Investment activated: User {user_id}, Plan {plan_id}, Return ₹{daily_return}")
            
            # Show success notification
            self.show_success_notification(user_id, amount, daily_return)
            
        except Exception as e:
            Logger.error(f"Investment activation error: {str(e)}")
    
    def show_success_notification(self, user_id, amount, daily_return):
        """Show payment success notification"""
        from utils import show_popup
        
        # This would trigger a popup in the UI
        success_msg = f"""
🎉 PAYMENT SUCCESSFUL! 

✅ Investment: ₹{amount}
✅ First Return: ₹{daily_return:.2f}
✅ Added to Wallet

Your investment is now active!
"""
        show_popup('Payment Success', success_msg)
    
    def cleanup_pending_payment(self, transaction_id):
        """Clean up pending payments after timeout"""
        conn = sqlite3.connect("investkar_data.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE payment_intents 
            SET status = 'timeout' 
            WHERE transaction_id = ? AND status = 'pending'
        ''', (transaction_id,))
        
        conn.commit()
        conn.close()
        
        Logger.info(f"Payment timeout: {transaction_id}")

# Global instance
auto_payment = AutomatedPayment()