import os
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.modalview import ModalView
from kivy.uix.gridlayout import GridLayout

from utils import show_popup
from database import db
from admin_verify import admin_verifier
import json

class AdminScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.show_admin_login()
    
    def show_admin_login(self):
        """Admin login screen"""
        self.clear_widgets()
        
        layout = BoxLayout(orientation='vertical', padding=50, spacing=20)
        
        layout.add_widget(Label(
            text='🔐 Admin Login',
            font_size='24sp',
            bold=True,
            size_hint_y=None,
            height=50
        ))
        
        self.admin_password = TextInput(
            hint_text='Admin Password',
            password=True,
            multiline=False,
            size_hint_y=None,
            height=50
        )
        layout.add_widget(self.admin_password)
        
        login_btn = Button(
            text='Login',
            size_hint_y=None,
            height=50,
            background_color=(0.8, 0.2, 0.2, 1)
        )
        login_btn.bind(on_press=self.admin_login)
        layout.add_widget(login_btn)
        
        back_btn = Button(
            text='← Back to User App',
            size_hint_y=None,
            height=40
        )
        back_btn.bind(on_press=self.back_to_user)
        layout.add_widget(back_btn)
        
        self.add_widget(layout)
    
    def admin_login(self, instance):
        """Simple admin authentication"""
        # ⚠️ IMPORTANT: Avoid hardcoding passwords.
        # Load password from an environment variable for better security.
        admin_password = os.environ.get('ADMIN_PASSWORD', 'temp_beta_password_123')
        
        if self.admin_password.text == admin_password:
            self.show_admin_dashboard()
        else:
            show_popup('Error', 'Invalid admin password')
    
    def back_to_user(self, instance):
        """Return to user app"""
        app = App.get_running_app()
        app.root.current = 'auth'
    
    def show_admin_dashboard(self):
        """Admin main dashboard"""
        self.clear_widgets()
        
        scroll = ScrollView()
        layout = BoxLayout(orientation='vertical', spacing=10, padding=20, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        
        # Header
        header = Label(
            text='👑 Admin Dashboard',
            font_size='20sp',
            bold=True,
            size_hint_y=None,
            height=40
        )
        layout.add_widget(header)
        
        # Platform Stats
        stats = db.get_platform_stats()
        stats_layout = GridLayout(cols=2, size_hint_y=None, height=200, spacing=10)
        
        stats_data = [
            ('👥 Total Users', stats['total_users']),
            ('💰 Total Investment', f'₹{stats["total_investment_amount"]:,.2f}'),
            ('📈 Active Investments', stats['active_investments']),
            ('💸 Returns Paid', f'₹{stats["total_returns_paid"]:,.2f}'),
            ('🏦 Total Withdrawals', f'₹{stats["total_withdrawals"]:,.2f}'),
            ('💳 Wallet Balance', f'₹{stats["total_wallet_balance"]:,.2f}')
        ]
        
        for label, value in stats_data:
            stats_layout.add_widget(Label(
                text=label,
                font_size='14sp',
                bold=True
            ))
            stats_layout.add_widget(Label(
                text=str(value),
                font_size='14sp'
            ))
        
        layout.add_widget(stats_layout)
        
        # Admin Actions
        actions_layout = GridLayout(cols=2, size_hint_y=None, height=300, spacing=10)
        
        actions = [
            ('👥 Manage Users', self.show_users_list),
            ('💸 Pending Withdrawals', self.show_pending_withdrawals),
            ('💰 Verify Payments', self.show_payment_verification),
            ('🧾 View Transactions', self.show_transactions_list),
            ('⚙️ Admin Tools', self.show_admin_tools)
        ]
        
        for text, callback in actions:
            btn = Button(text=text, size_hint_y=None, height=70)
            btn.bind(on_press=callback)
            actions_layout.add_widget(btn)
        
        layout.add_widget(actions_layout)
        
        # Logout
        logout_btn = Button(
            text='Logout',
            size_hint_y=None,
            height=50,
            background_color=(0.5, 0.5, 0.5, 1)
        )
        logout_btn.bind(on_press=lambda x: self.show_admin_login())
        layout.add_widget(logout_btn)
        
        scroll.add_widget(layout)
        self.add_widget(scroll)
    
    def show_users_list(self, instance):
        """Show list of all users"""
        self.clear_widgets()
        
        scroll = ScrollView()
        layout = BoxLayout(orientation='vertical', spacing=10, padding=20, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        
        # Header
        header = BoxLayout(size_hint_y=None, height=50)
        header.add_widget(Label(
            text='👥 All Users',
            font_size='18sp',
            bold=True
        ))
        back_btn = Button(
            text='← Back',
            size_hint_x=None,
            width=100
        )
        back_btn.bind(on_press=lambda x: self.show_admin_dashboard())
        header.add_widget(back_btn)
        layout.add_widget(header)
        
        # Users list
        users = db.get_all_users()
        
        if not users:
            layout.add_widget(Label(text='No users found', font_size='16sp'))
        else:
            for user in users:
                user_id, phone, wallet, referral, created_at = user
                
                user_card = BoxLayout(
                    orientation='horizontal', 
                    size_hint_y=None, 
                    height=80,
                    padding=10
                )
                
                user_info = BoxLayout(orientation='vertical')
                user_info.add_widget(Label(
                    text=f'📱 {phone}',
                    font_size='14sp',
                    bold=True
                ))
                user_info.add_widget(Label(
                    text=f'💰 ₹{wallet:.2f} | 🎯 {referral}',
                    font_size='12sp'
                ))
                user_info.add_widget(Label(
                    text=f'Joined: {created_at[:10]}',
                    font_size='10sp'
                ))
                
                actions = BoxLayout(orientation='horizontal', size_hint_x=None, width=200)
                
                view_btn = Button(text='View', size_hint_x=None, width=60)
                view_btn.bind(on_press=lambda x, uid=user_id: self.view_user_details(uid))
                
                adjust_btn = Button(text='Adjust', size_hint_x=None, width=60)
                adjust_btn.bind(on_press=lambda x, uid=user_id: self.adjust_user_wallet(uid))
                
                delete_btn = Button(text='Delete', size_hint_x=None, width=60)
                delete_btn.bind(on_press=lambda x, uid=user_id: self.delete_user(uid))
                
                actions.add_widget(view_btn)
                actions.add_widget(adjust_btn)
                actions.add_widget(delete_btn)
                
                user_card.add_widget(user_info)
                user_card.add_widget(actions)
                layout.add_widget(user_card)
        
        scroll.add_widget(layout)
        self.add_widget(scroll)
    
    def view_user_details(self, user_id):
        """Show detailed user information"""
        user_data = db.get_user_detailed_info(user_id)
        if not user_data:
            show_popup('Error', 'User not found')
            return
        
        user_info = user_data['user_info']
        investments = user_data['investments']
        transactions = user_data['transactions']
        
        popup = ModalView(size_hint=(0.9, 0.8))
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # User info
        layout.add_widget(Label(
            text=f'📱 User Details: {user_info[1]}',
            font_size='18sp',
            bold=True
        ))
        
        info_text = f'''
        User ID: {user_info[0]}
        Phone: {user_info[1]}
        Wallet: ₹{user_info[3]:.2f}
        Referral: {user_info[4]}
        Joined: {user_info[5]}
        '''
        
        layout.add_widget(Label(text=info_text, font_size='12sp'))
        
        # Investments
        layout.add_widget(Label(
            text=f'📊 Investments ({len(investments)})',
            font_size='14sp',
            bold=True,
            size_hint_y=None,
            height=30
        ))
        
        if investments:
            for inv in investments:
                inv_text = f'Plan {inv[2]}: ₹{inv[3]} | Days: {inv[7]}/{inv[6]} | Profit: ₹{inv[8]:.2f}'
                layout.add_widget(Label(text=inv_text, font_size='10sp'))
        else:
            layout.add_widget(Label(text='No investments', font_size='12sp'))
        
        close_btn = Button(text='Close', size_hint_y=None, height=50)
        close_btn.bind(on_press=lambda x: popup.dismiss())
        layout.add_widget(close_btn)
        
        popup.add_widget(layout)
        popup.open()
    
    def adjust_user_wallet(self, user_id):
        """Adjust user wallet balance"""
        popup = ModalView(size_hint=(0.8, 0.6))
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        layout.add_widget(Label(
            text='💳 Adjust Wallet Balance',
            font_size='18sp',
            bold=True
        ))
        
        self.adjust_amount = TextInput(
            hint_text='Amount (positive to add, negative to deduct)',
            input_filter='float',
            multiline=False,
            size_hint_y=None,
            height=50
        )
        layout.add_widget(self.adjust_amount)
        
        self.adjust_reason = TextInput(
            hint_text='Reason for adjustment',
            multiline=False,
            size_hint_y=None,
            height=50
        )
        layout.add_widget(self.adjust_reason)
        
        apply_btn = Button(
            text='Apply Adjustment',
            size_hint_y=None,
            height=50,
            background_color=(0.2, 0.8, 0.2, 1)
        )
        apply_btn.bind(on_press=lambda x: self.apply_wallet_adjustment(user_id, popup))
        layout.add_widget(apply_btn)
        
        cancel_btn = Button(
            text='Cancel',
            size_hint_y=None,
            height=50
        )
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        layout.add_widget(cancel_btn)
        
        popup.add_widget(layout)
        popup.open()
    
    def apply_wallet_adjustment(self, user_id, popup):
        """Apply wallet adjustment"""
        try:
            amount = float(self.adjust_amount.text)
            reason = self.adjust_reason.text or "Admin adjustment"
            
            if amount == 0:
                show_popup('Error', 'Amount cannot be zero')
                return
            
            success = db.update_user_wallet(user_id, amount, reason)
            
            if success:
                popup.dismiss()
                show_popup('Success', f'Wallet adjusted by ₹{amount:.2f}')
                self.show_users_list(None)  # Refresh list
            else:
                show_popup('Error', 'Failed to adjust wallet')
                
        except ValueError:
            show_popup('Error', 'Invalid amount')
    
    def delete_user(self, user_id):
        """Delete user confirmation"""
        popup = ModalView(size_hint=(0.8, 0.4))
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        layout.add_widget(Label(
            text='⚠️ Delete User',
            font_size='18sp',
            bold=True
        ))
        
        layout.add_widget(Label(
            text='This will permanently delete the user and all their data!',
            font_size='14sp'
        ))
        
        confirm_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        
        yes_btn = Button(text='Delete', background_color=(0.8, 0.2, 0.2, 1))
        yes_btn.bind(on_press=lambda x: self.confirm_delete_user(user_id, popup))
        
        no_btn = Button(text='Cancel')
        no_btn.bind(on_press=lambda x: popup.dismiss())
        
        confirm_layout.add_widget(yes_btn)
        confirm_layout.add_widget(no_btn)
        layout.add_widget(confirm_layout)
        
        popup.add_widget(layout)
        popup.open()
    
    def confirm_delete_user(self, user_id, popup):
        """Confirm and delete user"""
        success, message = db.delete_user(user_id)
        popup.dismiss()
        
        if success:
            show_popup('Success', 'User deleted successfully')
            self.show_users_list(None)  # Refresh list
        else:
            show_popup('Error', message)
    
    def show_pending_withdrawals(self, instance):
        """Show list of all pending withdrawal requests"""
        self.clear_widgets()

        scroll = ScrollView()
        layout = BoxLayout(orientation='vertical', spacing=10, padding=20, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        # Header
        header = BoxLayout(size_hint_y=None, height=50)
        header.add_widget(Label(
            text='💸 Pending Withdrawals',
            font_size='18sp',
            bold=True
        ))
        back_btn = Button(text='← Back', size_hint_x=None, width=100)
        back_btn.bind(on_press=lambda x: self.show_admin_dashboard())
        header.add_widget(back_btn)
        layout.add_widget(header)

        # Pending withdrawals list
        requests = db.get_all_pending_withdrawals()

        if not requests:
            layout.add_widget(Label(text='No pending withdrawal requests.', font_size='16sp'))
        else:
            for req in requests:
                req_id, user_id, amount, bank_details_json, created_at, phone = req
                bank_details = json.loads(bank_details_json)

                card = BoxLayout(orientation='vertical', size_hint_y=None, height=180, padding=10, spacing=5)
                
                info_text = f"User: {phone} | Amount: ₹{amount:.2f}"
                card.add_widget(Label(text=info_text, font_size='14sp', bold=True))

                bank_text = f"Acc. Holder: {bank_details.get('account_holder', 'N/A')}\n" \
                            f"Acc. Number: {bank_details.get('account_number', 'N/A')}\n" \
                            f"IFSC: {bank_details.get('ifsc_code', 'N/A')}"
                card.add_widget(Label(text=bank_text, font_size='12sp'))

                card.add_widget(Label(text=f"Requested on: {created_at[:16]}", font_size='10sp'))

                # Action buttons
                actions = BoxLayout(size_hint_y=None, height=40, spacing=10)
                approve_btn = Button(text='Approve', background_color=(0.2, 0.8, 0.2, 1))
                approve_btn.bind(on_press=lambda x, r_id=req_id: self.approve_withdrawal(r_id))

                cancel_btn = Button(text='Cancel', background_color=(0.8, 0.2, 0.2, 1))
                cancel_btn.bind(on_press=lambda x, r_id=req_id: self.cancel_withdrawal(r_id))

                actions.add_widget(approve_btn)
                actions.add_widget(cancel_btn)
                card.add_widget(actions)

                layout.add_widget(card)

        scroll.add_widget(layout)
        self.add_widget(scroll)

    def approve_withdrawal(self, request_id):
        show_popup('Info', f'Approving request {request_id}...\n(Logic not yet implemented)')

    def cancel_withdrawal(self, request_id):
        show_popup('Info', f'Cancelling request {request_id}...\n(Logic not yet implemented)')

    def show_auto_verify_screen(self, instance):
        """Show screen to manually verify auto-payments"""
        self.clear_widgets()

        scroll = ScrollView()
        layout = BoxLayout(orientation='vertical', spacing=10, padding=20, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        # Header
        header = BoxLayout(size_hint_y=None, height=50)
        header.add_widget(Label(
            text='✅ Auto-Verify Payments',
            font_size='18sp',
            bold=True
        ))
        back_btn = Button(text='← Back', size_hint_x=None, width=100)
        back_btn.bind(on_press=lambda x: self.show_admin_dashboard())
        header.add_widget(back_btn)
        layout.add_widget(header)

        # Pending payments list
        pending_payments = admin_verifier.get_pending_payments()

        if not pending_payments:
            layout.add_widget(Label(text='No pending payments to verify.', font_size='16sp'))
        else:
            for payment in pending_payments:
                txn_id, user_id, plan_id, amount, phone, created_at = payment

                card = BoxLayout(orientation='vertical', size_hint_y=None, height=120, padding=10, spacing=5)
                
                card.add_widget(Label(text=f"User: {phone} | Plan: {plan_id} | Amount: ₹{amount}", font_size='14sp', bold=True))
                card.add_widget(Label(text=f"Transaction ID: {txn_id}", font_size='12sp'))
                card.add_widget(Label(text=f"Created: {created_at}", font_size='10sp'))

                verify_btn = Button(text='Mark as Verified', background_color=(0.2, 0.8, 0.2, 1), size_hint_y=None, height=40)
                verify_btn.bind(on_press=lambda x, t=txn_id: self.mark_as_verified(t))
                card.add_widget(verify_btn)

                layout.add_widget(card)

        scroll.add_widget(layout)
        self.add_widget(scroll)

    def mark_as_verified(self, transaction_id):
        success, message = admin_verifier.verify_payment(transaction_id)
        show_popup('Verification', message)
        self.show_auto_verify_screen(None) # Refresh the screen
    
    def show_payment_verification(self, instance):
        """Show pending payments for admin verification"""
        pending_payments = admin_verifier.get_pending_payments()
        
        popup = ModalView(size_hint=(0.95, 0.9))
        
        # Main layout with a ScrollView
        main_layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        scroll = ScrollView()
        layout = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        main_layout.add_widget(Label(
            text='💰 Pending Payment Verification',
            font_size='20sp',
            bold=True,
            size_hint_y=None,
            height=40
        ))
        
        if not pending_payments:
            layout.add_widget(Label(text='No pending payments', font_size='16sp'))
        else:
            for payment in pending_payments:
                txn_id, user_id, plan_id, amount, phone, created = payment
                
                payment_card = BoxLayout(orientation='horizontal', size_hint_y=None, height=80, padding=5)
                
                info = Label(
                    text=f'User: {phone}\nAmount: ₹{amount:.2f} | Plan: {plan_id}\nID: {txn_id}',
                    font_size='12sp',
                    halign='left',
                    valign='middle'
                )
                info.text_size = (info.width, None) # for text alignment
                
                verify_btn = Button(
                    text='Verify Paid',
                    size_hint_x=None,
                    width=120,
                    background_color=(0.2, 0.8, 0.2, 1)
                )
                verify_btn.bind(on_press=lambda x, txn=txn_id, p=popup: self.verify_single_payment(txn, p))
                
                payment_card.add_widget(info)
                payment_card.add_widget(verify_btn)
                layout.add_widget(payment_card)
        
        scroll.add_widget(layout)
        main_layout.add_widget(scroll)
        
        close_btn = Button(text='Close', size_hint_y=None, height=50)
        close_btn.bind(on_press=lambda x: popup.dismiss())
        main_layout.add_widget(close_btn)
        
        popup.add_widget(main_layout)
        popup.open()

    def verify_single_payment(self, transaction_id, popup):
        """Verify a single payment"""
        popup.dismiss() # Dismiss the current popup first
        success, message = admin_verifier.verify_payment(transaction_id)
        if success:
            show_popup('Success', 'Payment verified! Investment activated.')
            # Refresh the view by opening a new, updated popup
            self.show_payment_verification(None)
        else:
            show_popup('Error', message)
            # Re-open the verification window so the admin can try again or see other payments
            self.show_payment_verification(None)
    
    def show_transactions_list(self, instance):
        """Show all transactions"""
        self.clear_widgets()

        scroll = ScrollView()
        layout = BoxLayout(orientation='vertical', spacing=10, padding=20, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        # Header
        header = BoxLayout(size_hint_y=None, height=50)
        header.add_widget(Label(
            text='🧾 All Transactions',
            font_size='18sp',
            bold=True
        ))
        back_btn = Button(text='← Back', size_hint_x=None, width=100)
        back_btn.bind(on_press=lambda x: self.show_admin_dashboard())
        header.add_widget(back_btn)
        layout.add_widget(header)

        # Transactions list
        transactions = db.get_all_transactions(limit=200)

        if not transactions:
            layout.add_widget(Label(text='No transactions found.', font_size='16sp'))
        else:
            for txn in transactions:
                txn_id, user_id, txn_type, amount, desc, status, bank_details, created_at, phone = txn

                card = BoxLayout(orientation='vertical', size_hint_y=None, height=100, padding=10, spacing=5)
                
                # Top row: User and Date
                top_row = BoxLayout(size_hint_y=None, height=20)
                top_row.add_widget(Label(text=f"User: {phone}", font_size='12sp', halign='left'))
                top_row.add_widget(Label(text=f"{created_at[:16]}", font_size='10sp', halign='right'))
                card.add_widget(top_row)

                # Middle row: Type and Amount
                middle_row = BoxLayout(size_hint_y=None, height=30)
                middle_row.add_widget(Label(text=f"Type: {txn_type.capitalize()}", font_size='14sp', bold=True, halign='left'))
                middle_row.add_widget(Label(text=f"₹{amount:,.2f}", font_size='14sp', bold=True, halign='right'))
                card.add_widget(middle_row)

                card.add_widget(Label(text=f"Desc: {desc}", font_size='12sp', halign='left'))
                layout.add_widget(card)

        scroll.add_widget(layout)
        self.add_widget(scroll)
    
    def show_admin_tools(self, instance):
        """Show admin tools"""
        popup = ModalView(size_hint=(0.8, 0.6))
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        layout.add_widget(Label(
            text='⚙️ Admin Tools',
            font_size='18sp',
            bold=True
        ))
        
        tools = [
            ('🔄 Process Daily Returns', self.process_daily_returns),
            ('📊 Export Data', self.export_data),
            ('🛠️ System Info', self.system_info)
        ]
        
        for text, callback in tools:
            btn = Button(text=text, size_hint_y=None, height=50)
            btn.bind(on_press=callback)
            layout.add_widget(btn)
        
        close_btn = Button(text='Close', size_hint_y=None, height=50)
        close_btn.bind(on_press=lambda x: popup.dismiss())
        layout.add_widget(close_btn)
        
        popup.add_widget(layout)
        popup.open()
    
    def process_daily_returns(self, instance):
        """Manually process daily returns"""
        db.calculate_daily_returns()
        show_popup('Success', 'Daily returns processed successfully')
    
    def export_data(self, instance):
        """Export database data"""
        # Implement data export functionality
        show_popup('Info', 'Export feature coming soon')
    
    def system_info(self, instance):
        """Show system information"""
        import platform
        info = f'''
        Python: {platform.python_version()}
        Platform: {platform.platform()}
        Database: SQLite
        Total Users: {db.get_platform_stats()["total_users"]}
        '''
        show_popup('System Info', info)