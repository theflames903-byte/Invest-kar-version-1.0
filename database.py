import sqlite3
import hashlib
import secrets
from datetime import datetime
import json
from kivy.logger import Logger
from security import rate_limit
from encryption import encryption

class Database:
    def __init__(self, db_path):
        # Use the provided path to connect to the database
        self.plans = {}
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()
        self.migrate_encryption()  # Encrypt existing data
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE NOT NULL,
                security_code_hash TEXT NOT NULL,
                phone_encrypted TEXT,
                salt TEXT NOT NULL,
                wallet_balance REAL DEFAULT 0,
                referral_code TEXT UNIQUE,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Investments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS investments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                plan_id INTEGER,
                amount REAL,
                daily_return REAL,
                total_days INTEGER,
                days_remaining INTEGER,
                total_profit REAL DEFAULT 0,
                status TEXT DEFAULT 'active',
                payment_method TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,  -- investment, withdrawal, return, referral, withdrawal_payment
                amount REAL,
                description TEXT,
                status TEXT DEFAULT 'completed',
                bank_details_encrypted TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # OTP storage table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS otp_store (
                phone TEXT PRIMARY KEY,
                otp TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Withdrawal requests table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdrawal_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                bank_details_encrypted TEXT,
                status TEXT DEFAULT 'pending',  -- pending, paid, completed, cancelled
                payment_transaction_id TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Log for daily return processing to prevent multiple runs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_run_log (
                run_date TEXT PRIMARY KEY,
                run_timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def migrate_encryption(self):
        """Migrate existing data to encrypted format"""
        cursor = self.conn.cursor()
        try:
            # Check if we need to migrate
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            if not cursor.fetchone():
                return
            
            # Check if encryption is already applied
            cursor.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'phone_encrypted' not in columns:
                # Add encrypted columns
                cursor.execute('ALTER TABLE users ADD COLUMN phone_encrypted TEXT;')
                cursor.execute('ALTER TABLE transactions ADD COLUMN bank_details_encrypted TEXT;')
                cursor.execute('ALTER TABLE withdrawal_requests ADD COLUMN bank_details_encrypted TEXT;')
                
                # Migrate existing phone numbers
                cursor.execute("SELECT id, phone FROM users")
                users = cursor.fetchall()
                for user_id, phone in users:
                    encrypted_phone = encryption.encrypt_string(phone)
                    cursor.execute(
                        "UPDATE users SET phone_encrypted = ? WHERE id = ?",
                        (encrypted_phone, user_id)
                    )
                
                # Migrate bank details in transactions
                cursor.execute("SELECT id, bank_details FROM transactions WHERE bank_details IS NOT NULL")
                transactions = cursor.fetchall()
                for txn_id, bank_details in transactions:
                    if bank_details:
                        encrypted_bank = encryption.encrypt_json(bank_details)
                        cursor.execute(
                            "UPDATE transactions SET bank_details_encrypted = ? WHERE id = ?",
                            (encrypted_bank, txn_id)
                        )
                
                self.conn.commit()
                Logger.info("Database: Encryption migration completed")
                
        except Exception as e:
            Logger.error(f"Database: Migration failed - {e}")
            self.conn.rollback()
    
    def initialize_plans(self, plans_data):
        self.plans = plans_data

    def hash_security_code(self, code, salt):
        """Hashes the security code with a salt using PBKDF2."""
        # The salt should be bytes. If it's a hex string from the DB, convert it.
        salt_bytes = bytes.fromhex(salt) if isinstance(salt, str) else salt
        # Use PBKDF2 for key derivation, which is more secure than simple hashing.
        dk = hashlib.pbkdf2_hmac('sha256', code.encode('utf-8'), salt_bytes, 100000)
        return dk.hex()
    
    def store_otp(self, phone, otp):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO otp_store (phone, otp, created_at)
            VALUES (?, ?, ?)
        ''', (phone, otp, datetime.now().isoformat()))
        self.conn.commit()
    
    @rate_limit(max_attempts=5, timeout=600) # 5 attempts per 10 minutes
    def verify_otp(self, phone, otp):
        cursor = self.conn.cursor()
        cursor.execute('SELECT otp, created_at FROM otp_store WHERE phone = ?', (phone,))
        result = cursor.fetchone()
        
        if not result:
            return False, "No OTP found for this number."

        stored_otp, created_at = result
        # OTP expires after 10 minutes
        if (datetime.now() - datetime.fromisoformat(created_at)).seconds > 600:
            return False

        return stored_otp == otp, "OTP verified" # Return tuple for consistency
    
    def register_user(self, phone, security_code, referral_code=None):
        cursor = self.conn.cursor()
        
        # ✅ Encrypt phone number before storing
        encrypted_phone = encryption.encrypt_string(phone)
        
        # Check if user exists
        cursor.execute('SELECT id FROM users WHERE phone_encrypted = ?', (encrypted_phone,))
        if cursor.fetchone():
            return False, "Phone already registered"
        
        # Generate a new salt for the user
        salt = secrets.token_hex(16)
        security_hash = self.hash_security_code(security_code, salt)
        ref_code = phone[-6:]  # Use original phone for referral code
        
        try:
            cursor.execute('''
                INSERT INTO users (phone, phone_encrypted, security_code_hash, salt, referral_code)
                VALUES (?, ?, ?, ?, ?)
            ''', (phone, encrypted_phone, security_hash, salt, ref_code))  # Keep plain phone for SMS
            
            # Handle referral
            if referral_code:
                referrer = self.get_user_by_referral(referral_code)
                if referrer:
                    # Give ₹50 referral bonus
                    self.update_wallet(referrer[0], 50)
                    self.add_transaction(referrer[0], 'referral', 50, f'Referral bonus from {phone}')
            
            self.conn.commit()
            return True, "Registration successful"
        except Exception as e:
            return False, str(e)
    
    @rate_limit(max_attempts=10, timeout=1800) # 10 attempts per 30 minutes
    def login_user(self, phone, security_code):
        cursor = self.conn.cursor()
        # --- SECURITY FIX: Always use encrypted phone for lookup ---
        encrypted_phone = encryption.encrypt_string(phone)
        cursor.execute('SELECT id, security_code_hash, salt FROM users WHERE phone_encrypted = ?', (encrypted_phone,))
        result = cursor.fetchone()
        
        if not result:
            return False, "User not found"
        
        user_id, stored_hash, salt = result
        if self.hash_security_code(security_code, salt) == stored_hash:
            return True, user_id
        else:
            return False, "Invalid security code"
    
    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        
        if user:
            # Return user with decrypted phone
            decrypted_phone = encryption.decrypt_string(user[3]) if user[3] else user[1]
            return (user[0], decrypted_phone, user[2], user[3], user[4], user[5], user[6])
        return None
    
    def get_user_by_referral(self, referral_code):
        cursor = self.conn.cursor()
        cursor.execute('SELECT id FROM users WHERE referral_code = ?', (referral_code,))
        return cursor.fetchone()
    
    def update_wallet(self, user_id, amount):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE users SET wallet_balance = wallet_balance + ? WHERE id = ?', (amount, user_id))
        self.conn.commit()
    
    def get_wallet_balance(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT wallet_balance FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 0
    
    def add_investment(self, user_id, plan_id, amount, payment_method):
        plan = self.plans.get(plan_id)
        if not plan:
            return False
        
        daily_return = amount * (plan['return_rate'] / 100.0)
        
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO investments (user_id, plan_id, amount, daily_return, total_days, days_remaining, payment_method)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, plan_id, amount, daily_return, plan['days'], plan['days'], payment_method))
        
        self.add_transaction(user_id, 'investment', amount, f'Invested in Plan {plan_id}')
        
        # Add first day return immediately
        self.update_wallet(user_id, daily_return)
        self.add_transaction(user_id, 'return', daily_return, f'First day return from Plan {plan_id}')
        
        self.conn.commit()
        return True
    
    def get_active_investments(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM investments 
            WHERE user_id = ? AND status = 'active' 
            ORDER BY created_at DESC
        ''', (user_id,))
        return cursor.fetchall()
    
    def add_transaction(self, user_id, type, amount, description, bank_details=None):
        cursor = self.conn.cursor()
        
        # ✅ Encrypt bank details
        encrypted_bank = encryption.encrypt_json(bank_details) if bank_details else None
        
        cursor.execute('''
            INSERT INTO transactions (user_id, type, amount, description, bank_details_encrypted)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, type, amount, description, encrypted_bank))
        
        self.conn.commit()
    
    def get_transactions(self, user_id, limit=20):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, user_id, type, amount, description, status, created_at, 
                   bank_details_encrypted
            FROM transactions 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (user_id, limit))
        
        transactions = []
        for txn in cursor.fetchall():
            txn_id, user_id, type, amount, desc, status, created_at, bank_encrypted = txn
            
            # Use encrypted bank details if available
            bank_details = None
            if bank_encrypted:
                bank_details = encryption.decrypt_json(bank_encrypted)
            
            transactions.append((txn_id, user_id, type, amount, desc, status, bank_details, created_at))
        return transactions
    
    def create_withdrawal_request(self, user_id, amount, bank_details):
        """Create withdrawal request with encrypted bank details"""
        cursor = self.conn.cursor()
        
        current_balance = self.get_wallet_balance(user_id)
        
        if amount < 100:
            return False, "Minimum withdrawal is ₹100"
        
        if amount > current_balance:
            return False, "Insufficient balance"
        
        # ✅ Encrypt bank details
        encrypted_bank = encryption.encrypt_json(bank_details)
        
        cursor.execute('''
            INSERT INTO withdrawal_requests (user_id, amount, bank_details_encrypted, status)
            VALUES (?, ?, ?, 'pending')
        ''', (user_id, amount, encrypted_bank))
        
        self.conn.commit()
        return True, "Withdrawal request created"
    
    def complete_withdrawal_after_payment(self, user_id, amount, transaction_id):
        """Complete withdrawal after user makes payment"""
        cursor = self.conn.cursor()
        
        # Find pending withdrawal
        cursor.execute('''
            SELECT id FROM withdrawal_requests 
            WHERE user_id = ? AND amount = ? AND status = 'pending'
            ORDER BY created_at DESC LIMIT 1
        ''', (user_id, amount))
        
        result = cursor.fetchone()
        if not result:
            return False, "No pending withdrawal found"
        
        withdrawal_id = result[0]
        
        # Deduct from wallet
        self.update_wallet(user_id, -amount)
        
        # Update withdrawal status
        cursor.execute('''
            UPDATE withdrawal_requests 
            SET status = 'completed', payment_transaction_id = ?
            WHERE id = ?
        ''', (transaction_id, withdrawal_id))
        
        # Add transaction record
        self.add_transaction(user_id, 'withdrawal', amount, 'Withdrawal completed', {})
        
        self.conn.commit()
        return True, "Withdrawal completed successfully"
    
    def get_pending_withdrawals(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM withdrawal_requests 
            WHERE user_id = ? AND status = 'pending'
            ORDER BY created_at DESC
        ''', (user_id,))
        return cursor.fetchall()
    
    def get_all_pending_withdrawals(self):
        """Get all pending withdrawal requests for admin view"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT w.id, w.user_id, w.amount, w.bank_details_encrypted, w.created_at, u.phone
            FROM withdrawal_requests w
            JOIN users u ON w.user_id = u.id
            WHERE w.status = 'pending'
            ORDER BY w.created_at ASC
        ''')
        return cursor.fetchall()

    def admin_approve_withdrawal(self, request_id):
        """Admin: Approve a withdrawal request, deduct from wallet, and log transaction."""
        cursor = self.conn.cursor()
        try:
            # Get request details
            cursor.execute('''
                SELECT user_id, amount, status FROM withdrawal_requests WHERE id = ?
            ''', (request_id,))
            result = cursor.fetchone()

            if not result:
                return False, "Withdrawal request not found."

            user_id, amount, status = result
            if status != 'pending':
                return False, f"Request is already '{status}', cannot approve."

            # 1. Deduct from user's wallet
            self.update_wallet(user_id, -amount)

            # 2. Update withdrawal request status to 'completed'
            cursor.execute("UPDATE withdrawal_requests SET status = 'completed' WHERE id = ?", (request_id,))

            # 3. Add a transaction log for the withdrawal
            self.add_transaction(user_id, 'withdrawal', amount, f'Admin approved withdrawal of ₹{amount:.2f}')

            self.conn.commit()
            Logger.info(f"Admin approved withdrawal request {request_id} for user {user_id}.")
            return True, "Withdrawal approved successfully. Funds deducted from user wallet."

        except Exception as e:
            self.conn.rollback()
            Logger.error(f"Database: Failed to approve withdrawal {request_id} - {e}")
            return False, f"An error occurred: {e}"

    def admin_cancel_withdrawal(self, request_id):
        """Admin: Cancel a pending withdrawal request."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT status FROM withdrawal_requests WHERE id = ?", (request_id,))
            result = cursor.fetchone()

            if not result:
                return False, "Withdrawal request not found."

            if result[0] != 'pending':
                return False, f"Request is already '{result[0]}', cannot cancel."

            cursor.execute("UPDATE withdrawal_requests SET status = 'cancelled' WHERE id = ?", (request_id,))
            self.conn.commit()
            Logger.info(f"Admin cancelled withdrawal request {request_id}.")
            return True, "Withdrawal request has been cancelled."
        except Exception as e:
            self.conn.rollback()
            Logger.error(f"Database: Failed to cancel withdrawal {request_id} - {e}")
            return False, f"An error occurred: {e}"

    def calculate_daily_returns(self):
        """Calculate and credit daily returns for all active investments"""
        cursor = self.conn.cursor()

        # --- SECURITY FIX: Ensure this runs only once per day ---
        today_str = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('SELECT run_date FROM daily_run_log WHERE run_date = ?', (today_str,))
        if cursor.fetchone():
            Logger.info("Daily returns have already been processed today.")
            return # Already ran today, do nothing.
        
        # Log that we are running for today
        cursor.execute('INSERT INTO daily_run_log (run_date) VALUES (?)', (today_str,))
        
        # Get all active investments
        cursor.execute('SELECT * FROM investments WHERE status = "active"')
        investments = cursor.fetchall()
        
        for inv in investments:
            inv_id, user_id, plan_id, amount, daily_return, total_days, days_remaining, total_profit, status, payment_method, created_at = inv
            
            if days_remaining > 0:
                # Credit daily return
                self.update_wallet(user_id, daily_return)
                
                # Update investment
                cursor.execute('''
                    UPDATE investments 
                    SET days_remaining = days_remaining - 1, 
                        total_profit = total_profit + ?
                    WHERE id = ?
                ''', (daily_return, inv_id))
                
                # Add transaction
                self.add_transaction(user_id, 'return', daily_return, f'Daily return from Plan {plan_id}')
                
                # Mark as completed if no days remaining
                if days_remaining - 1 == 0:
                    cursor.execute('UPDATE investments SET status = "completed" WHERE id = ?', (inv_id,))
        
        self.conn.commit()
    
    def get_all_users(self):
        """Get all users for admin view"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, phone, wallet_balance, referral_code, created_at 
            FROM users ORDER BY created_at DESC
        ''')
        return cursor.fetchall()
    
    def get_all_investments(self):
        """Get all investments for admin view"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT i.*, u.phone 
            FROM investments i 
            JOIN users u ON i.user_id = u.id 
            ORDER BY i.created_at DESC
        ''')
        return cursor.fetchall()
    
    def get_all_transactions(self, limit=100):
        """Get all transactions for admin view"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT t.*, u.phone 
            FROM transactions t 
            JOIN users u ON t.user_id = u.id 
            ORDER BY t.created_at DESC 
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()
    
    def get_platform_stats(self):
        """Get platform statistics for admin dashboard"""
        cursor = self.conn.cursor()
        
        stats = {
            'total_users': cursor.execute('SELECT COUNT(*) FROM users').fetchone()[0],
            'total_investments': cursor.execute('SELECT COUNT(*) FROM investments').fetchone()[0],
            'active_investments': cursor.execute('SELECT COUNT(*) FROM investments WHERE status = "active"').fetchone()[0],
            'total_investment_amount': cursor.execute('SELECT SUM(amount) FROM investments').fetchone()[0] or 0,
            'total_returns_paid': cursor.execute('SELECT SUM(amount) FROM transactions WHERE type = "return"').fetchone()[0] or 0,
            'total_withdrawals': cursor.execute('SELECT SUM(amount) FROM transactions WHERE type = "withdrawal"').fetchone()[0] or 0,
            'total_wallet_balance': cursor.execute('SELECT SUM(wallet_balance) FROM users').fetchone()[0] or 0,
        }
        
        return stats
    
    def update_user_wallet(self, user_id, amount, reason=""):
        """Admin: Update user wallet balance"""
        cursor = self.conn.cursor()
        cursor.execute('UPDATE users SET wallet_balance = wallet_balance + ? WHERE id = ?', (amount, user_id))
        
        # Add transaction record
        self.add_transaction(user_id, 'admin_adjustment', amount, f'Admin adjustment: {reason}')
        
        self.conn.commit()
        return True
    
    def delete_user(self, user_id):
        """Admin: Delete user and all their data"""
        cursor = self.conn.cursor()
        
        try:
            # Delete user's data from all tables
            cursor.execute('DELETE FROM transactions WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM investments WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM withdrawal_requests WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            
            self.conn.commit()
            return True, "User deleted successfully"
        except Exception as e:
            self.conn.rollback()
            return False, str(e)
    
    def get_user_detailed_info(self, user_id):
        """Get detailed user information"""
        cursor = self.conn.cursor()
        
        # User basic info
        user = cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            return None
        
        # User investments
        investments = cursor.execute('SELECT * FROM investments WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()
        
        # User transactions (last 20)
        transactions = cursor.execute('''
            SELECT * FROM transactions WHERE user_id = ? 
            ORDER BY created_at DESC LIMIT 20
        ''', (user_id,)).fetchall()
        
        return {
            'user_info': user,
            'investments': investments,
            'transactions': transactions
        }

# Global database instance
db = None