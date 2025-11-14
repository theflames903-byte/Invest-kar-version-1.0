from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.modalview import ModalView
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
import webbrowser
import os
from kivy.lang import Builder

from utils import show_popup, validate_database, optimize_app, show_support
from database import Database
from security import Security
from sms_service import sms_service
from auto_payment import auto_payment
from admin import AdminScreen
from upi_payment import upi_payment
from legal import show_terms_and_conditions, show_privacy_policy

# Set mobile-friendly window size
Window.size = (360, 640)

# Global database instance to be initialized in the App class
db = None

# Centralize plan definitions
INVESTMENT_PLANS = {
    1: {'name': 'Starter Plan', 'amounts': [599, 1099], 'return_rate': 4, 'days': 80, 'color': '#3b82f6'},
    2: {'name': 'Growth Plan', 'amounts': [1799, 3050], 'return_rate': 4, 'days': 110, 'color': '#8b5cf6'},
    3: {'name': 'Premium Plan', 'amounts': [10000, 20000], 'return_rate': 5, 'days': 150, 'color': '#ef4444'},
}

# Load the KV file. Although Kivy does this automatically,
# it's good practice to do it explicitly for clarity.
Builder.load_file('investkarapp.kv')


class AuthScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Check if user is already logged in
        if hasattr(App.get_running_app(), 'user_id'):
            App.get_running_app().root.current = 'home'
        else:
            self.show_login()
    def show_login(self):
        """Clears the screen and shows the login UI."""
        self.clear_widgets()
        self.current_view = Builder.load_string('<LoginView>:')
        self.add_widget(self.current_view)
    
    def show_register(self):
        """Clears the screen and shows the registration UI."""
        self.clear_widgets()
        self.current_view = Builder.load_string('<RegisterView>:')
        
        # Add legal buttons dynamically
        legal_layout = self.current_view.ids.legal_buttons
        terms_btn = Button(text='Terms & Conditions', size_hint_y=None, height=40, background_color=(0,0,0,0), underline=True, color=(0.5,0.5,1,1))
        terms_btn.bind(on_press=lambda x: show_terms_and_conditions())
        
        privacy_btn = Button(text='Privacy Policy', size_hint_y=None, height=40, background_color=(0,0,0,0), underline=True, color=(0.5,0.5,1,1))
        privacy_btn.bind(on_press=lambda x: show_privacy_policy())
        legal_layout.add_widget(terms_btn)
        legal_layout.add_widget(privacy_btn)
        self.add_widget(self.current_view)
    
    def send_otp(self, instance):
        phone = self.current_view.reg_phone.text.strip()
        
        if not Security.validate_phone(phone):
            show_popup('Error', 'Please enter valid 10-digit phone number')
            return
        
        # Generate OTP and security code
        otp = Security.generate_otp()
        security_code = Security.generate_security_code()
        
        # Store only OTP in database (not security code)
        db.store_otp(phone, otp)
        
        # Send SMS
        result = sms_service.send_otp(phone, otp, security_code)
        
        if result.get('return'):
            # Store security code temporarily for registration
            self.temp_security_code = security_code
            
            self.current_view.otp_section.disabled = False
            self.current_view.otp_section.opacity = 1
            
            if result.get('demo'):
                # Show demo popup with codes
                demo_msg = f'''
📱 DEMO MODE - No real SMS sent

📞 Phone: +91 {phone}
🔢 OTP: {otp}  
🔐 Security Code: {security_code}

✅ OTP Valid for 10 minutes

In production, this would be sent via SMS
'''
                show_popup('Demo OTP', demo_msg)
            else:
                show_popup('Success', 'OTP sent to your mobile number')
        else:
            show_popup('Error', f'Failed to send OTP: {result.get("message")}')
    def register(self, instance):
        phone = self.current_view.reg_phone.text.strip()
        otp = self.current_view.otp_input.text.strip()
        referral_code = self.current_view.referral_input.text.strip().upper()
        
        # Use the security code from temp storage, not from user input
        security_code = getattr(self, 'temp_security_code', None)
        
        if not Security.validate_phone(phone):
            show_popup('Error', 'Invalid phone number')
            return

        otp_verified, otp_message = db.verify_otp(phone, otp)
        if not otp_verified:
            # This will now show rate-limit errors as well
            show_popup('Error', 'Invalid or expired OTP')
            return
        
        if not security_code or len(security_code) != 6:
            show_popup('Error', 'Security code must be 6 digits')
            return
        
        success, message = db.register_user(phone, security_code, referral_code)
        
        if success:
            # ✅ AUTO-LOGIN AFTER REGISTRATION
            login_success, user_id = db.login_user(phone, security_code)
            if login_success:
                app = App.get_running_app()
                app.user_id = user_id
                app.root.current = 'home'
                show_popup('Success', 'Registration successful! Welcome!')
                
                # Clear temp security code
                if hasattr(self, 'temp_security_code'):
                    delattr(self, 'temp_security_code')
            else:
                show_popup('Error', 'Registration failed - please login manually')
                self.show_login()
        else:
            show_popup('Error', message)
    def login(self, instance):
        phone = self.current_view.phone_input.text.strip()
        security_code = self.current_view.security_input.text.strip()
        
        if not Security.validate_phone(phone):
            show_popup('Error', 'Please enter valid 10-digit phone number')
            return
        
        if len(security_code) != 6:
            show_popup('Error', 'Security code must be 6 digits')
            return
        
        success, result = db.login_user(phone, security_code)
        
        if success:
            app = App.get_running_app()
            app.user_id = result
            app.root.current = 'home'
            show_popup('Success', 'Login successful!')
        else:
            show_popup('Error', result)

    def go_to_admin(self):
        """Navigate to admin screen"""
        app = App.get_running_app()
        app.root.current = 'admin'

class HomeScreen(Screen):
    def on_enter(self):
        self.refresh_ui()
    
    def refresh_ui(self):
        # The main layout is now in the KV file. We just need to populate the dynamic part.
        plans_layout = self.ids.plans_layout
        plans_layout.clear_widgets()
        
        # Create plan cards from the centralized dictionary
        for plan_id, plan_details in INVESTMENT_PLANS.items():
            plan_card = self.create_plan_card(plan_id, **plan_details)
            plans_layout.add_widget(plan_card)
        
        # Customer Care
        care_card = Button(text='📞 Customer Support',
                           size_hint_y=None,
                           height=70,
                           background_color=(0.3, 0.3, 0.3, 1),
                           on_press=self.show_support_popup)

        plans_layout.add_widget(care_card)
    
    def create_plan_card(self, plan_id, name, amounts, return_rate, days, color, **kwargs):
        card = BoxLayout(orientation='vertical', size_hint_y=None, height=300, spacing=10)
        
        # Header
        header = Button(
            text=f'{name}\n{return_rate}% Daily Return • {days} Days',
            size_hint_y=None,
            height=80,
            background_color=self.hex_to_rgb(color),
            color=(1, 1, 1, 1)
        )
        header.disabled = True
        card.add_widget(header)
        
        # Amount options
        for amount in amounts:
            daily_return = amount * return_rate / 100
            total_return = amount + (daily_return * days)
            
            amount_btn = Button(
                text=f'₹{amount}\nDaily: ₹{daily_return:.2f} • Total: ₹{total_return:.0f}',
                size_hint_y=None,
                height=70,
                background_color=(0.9, 0.9, 0.9, 1)
            )
            amount_btn.bind(on_press=lambda x, p=plan_id, a=amount: self.invest(p, a))
            card.add_widget(amount_btn)
        
        return card
    
    def hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16)/255 for i in (0, 2, 4)) + (1,)

    def show_loading(self, text='Loading...'):
        """Shows a loading popup."""
        if not hasattr(self, 'loading_popup'):
            content = BoxLayout(orientation='vertical', padding=30, spacing=10)
            content.add_widget(Label(text=text, font_size='18sp'))
            self.loading_popup = ModalView(size_hint=(0.7, 0.3), auto_dismiss=False)
            self.loading_popup.add_widget(content)
        
        # Update text if needed
        self.loading_popup.children[0].children[0].text = text
        self.loading_popup.open()

    def hide_loading(self):
        """Hides the loading popup."""
        if hasattr(self, 'loading_popup') and self.loading_popup.parent:
            self.loading_popup.dismiss()

    def invest(self, plan_id, amount):
        app = App.get_running_app()
        if not hasattr(app, 'user_id'):
            show_popup('Error', 'Please login first')
            return
        
        try:
            # Show loading state
            self.show_loading('Preparing payment...')
            
            # Start automated payment
            payment_result = auto_payment.initiate_auto_payment(
                user_id=app.user_id,
                plan_id,
                amount
            )
            
            if payment_result['success']:
                self.hide_loading() # Hide before showing next screen
                self.show_payment_instructions(payment_result)
                
                # Start automatic verification
                auto_payment.start_payment_verification(
                    payment_result['transaction_id'],
                    app.user_id,
                    plan_id,
                    amount
                )
            else:
                show_popup('Payment Error', payment_result['message'])
        except Exception as e:
            show_popup('System Error', f'An unexpected error occurred: {e}\nPlease try again later.')
        finally:
            self.hide_loading()

    def show_payment_options(self, plan_id, amount):
        popup = ModalView(size_hint=(0.9, 0.5))
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        layout.add_widget(Label(
            text=f'Invest ₹{amount}',
            font_size='20sp',
            bold=True
        ))
        
        phonepe_btn = Button(
            text='Pay with PhonePe',
            size_hint_y=None,
            height=50,
            background_color=(0.5, 0.2, 0.8, 1)
        )
        phonepe_btn.bind(on_press=lambda x: self.initiate_investment_payment(plan_id, amount, 'phonepe', popup))
        layout.add_widget(phonepe_btn)
        
        cancel_btn = Button(
            text='Cancel',
            size_hint_y=None,
            height=50
        )
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        layout.add_widget(cancel_btn)
        popup.add_widget(layout)
        popup.open()
    
    def show_payment_instructions(self, payment_result):
        """Show payment instructions"""
        from kivy.uix.modalview import ModalView
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label
        from kivy.uix.button import Button
        
        popup = ModalView(size_hint=(0.9, 0.7))
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        instructions = f"""
💰 AUTOMATED PAYMENT

1. UPI app will open with **FIXED** amount
2. Complete payment with your UPI PIN
3. Return to app - **AUTO ACTIVATION**
4. First return added to wallet immediately

📊 Details:
• Amount: ₹{payment_result['amount']}
• Plan: {payment_result['plan_id']}
• Transaction: {payment_result['transaction_id']}

⏳ Waiting for payment verification...
"""
        
        layout.add_widget(Label(
            text=instructions,
            font_size='16sp',
            text_size=(300, None)
        ))
        
        # Open UPI app button
        upi_btn = Button(
            text='📱 Open UPI App & Pay',
            size_hint_y=None,
            height=60,
            background_color=(0.2, 0.8, 0.2, 1)
        )
        upi_btn.bind(on_press=lambda x: self.open_upi_and_pay(payment_result['payment_url'], popup))
        layout.add_widget(upi_btn)
        
        popup.add_widget(layout)
        popup.open()

    def open_upi_and_pay(self, upi_link, popup):
        """Open UPI app with fixed amount"""
        webbrowser.open(upi_link)
        popup.dismiss()
        show_popup('Info', 'Complete payment in UPI app. Return here for auto-activation!')
    
    def show_verification_popup(self, *args, **kwargs):
        """Delegates showing the verification popup to the main app instance."""
        App.get_running_app().show_verification_popup(*args, **kwargs)

class InvestScreen(Screen):
    def on_enter(self):
        self.refresh_investments()
    
    def refresh_investments(self):
        self.clear_widgets()
        
        # The ScrollView is defined in the KV file now.
        scroll = self.ids.scroll_view
        scroll.clear_widgets()

        app = App.get_running_app()
        investments = db.get_active_investments(app.user_id)
        
        layout = BoxLayout(orientation='vertical', spacing=10, padding=20, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        if not investments:
            # No investments
            layout.add_widget(Label(text='No Active Investments', font_size='20sp', bold=True))
            layout.add_widget(Label(text='Start investing to see your active plans', font_size='14sp'))
            scroll.add_widget(layout)
            self.add_widget(scroll) # Add the scrollview back
            return
        
        for inv in investments:
            inv_id, user_id, plan_id, amount, daily_return, total_days, days_remaining, total_profit, status, method, created_at = inv
            
            card = BoxLayout(orientation='vertical', size_hint_y=None, height=200, padding=15, spacing=10)
            
            # Header
            header = BoxLayout(size_hint_y=None, height=30)
            header.add_widget(Label(
                text=f'Plan {plan_id} • ₹{amount}',
                font_size='16sp',
                bold=True
            ))
            header.add_widget(Label(
                text=f'{days_remaining}/{total_days} Days',
                font_size='14sp'
            ))
            card.add_widget(header)
            
            # Details
            card.add_widget(Label(
                text=f'Daily Return: ₹{daily_return:.2f}',
                font_size='14sp'
            ))
            card.add_widget(Label(
                text=f'Total Profit: ₹{total_profit:.2f}',
                font_size='14sp'
            ))
            card.add_widget(Label(
                text=f'Payment: {method}',
                font_size='12sp'
            ))
            
            # Progress
            progress = ProgressBar(max=total_days, value=total_days-days_remaining, size_hint_y=None, height=20)
            card.add_widget(progress)
            
            layout.add_widget(card)
        
        scroll.add_widget(layout)
        self.add_widget(scroll) # Add the scrollview back

class ProfileScreen(Screen):
    def on_enter(self):
        self.refresh_profile()
    
    def refresh_profile(self):
        app = App.get_running_app()
        user = db.get_user(app.user_id)
        balance = db.get_wallet_balance(app.user_id)
        
        if not user: return # Not logged in

        # Update labels defined in the KV file
        self.ids.phone_label.text = f'📱 +91 {user[1]}'
        self.ids.referral_label.text = f'Referral Code: {user[4]}'
        self.ids.balance_label.text = f'₹{balance:.2f}'
        
        # Transactions
        transactions_list = self.ids.transactions_list
        transactions_list.clear_widgets()
        transactions = db.get_transactions(app.user_id, 10)

        if transactions:
            self.ids.recent_transactions_title.opacity = 1 # Show title
            
            for txn in transactions:
                txn_id, user_id, type, amount, desc, status, bank_details, created_at = txn
                
                txn_card = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, padding=10)
                txn_card.add_widget(Label(text=desc, font_size='12sp'))
                txn_card.add_widget(Label(text=f'₹{amount}', font_size='14sp', bold=True, size_hint_x=0.4))
                transactions_list.add_widget(txn_card)
        else:
            self.ids.recent_transactions_title.opacity = 0 # Hide title
    
    def show_withdrawal(self):
        popup = ModalView(size_hint=(0.9, 0.8), auto_dismiss=False)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        layout.add_widget(Label(
            text='Withdraw Funds',
            font_size='20sp',
            bold=True
        ))
        
        app = App.get_running_app()
        balance = db.get_wallet_balance(app.user_id)
        
        layout.add_widget(Label(
            text=f'Available: ₹{balance:.2f}',
            font_size='16sp'
        ))
        
        self.withdraw_amount = TextInput(
            hint_text='Amount (Min: ₹100)',
            input_filter='float',
            multiline=False,
            size_hint_y=None,
            height=50
        )
        layout.add_widget(self.withdraw_amount)
        
        self.account_holder = TextInput(
            hint_text='Account Holder Name',
            multiline=False,
            size_hint_y=None,
            height=50
        )
        layout.add_widget(self.account_holder)
        
        self.account_number = TextInput(
            hint_text='Bank Account Number',
            input_filter='int',
            multiline=False,
            size_hint_y=None,
            height=50
        )
        layout.add_widget(self.account_number)
        
        self.ifsc_code = TextInput(
            hint_text='IFSC Code',
            multiline=False,
            size_hint_y=None,
            height=50
        )
        layout.add_widget(self.ifsc_code)
        
        # Payment method selection
        payment_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
        
        phonepe_btn = Button(text='Pay Fee (PhonePe)', size_hint_x=0.5)
        phonepe_btn.bind(on_press=lambda x: self.process_withdrawal(
            popup, 'phonepe'
        ))
        
        gpay_btn = Button(text='Pay with Google Pay', size_hint_x=0.5)
        gpay_btn.bind(on_press=lambda x: self.process_withdrawal(
            popup, 'googlepay'
        ))
        
        payment_layout.add_widget(phonepe_btn)
        payment_layout.add_widget(gpay_btn)
        layout.add_widget(payment_layout)
        
        # Add a label for the payment buttons
        info_label = Label(text='Select a method to pay the withdrawal fee', size_hint_y=None, height=30, font_size='12sp')
        layout.add_widget(info_label)
        
        cancel_btn = Button(
            text='Cancel',
            size_hint_y=None,
            height=50
        )
        cancel_btn.bind(on_press=lambda x: popup.dismiss())
        layout.add_widget(cancel_btn)
        
        popup.add_widget(layout)
        popup.open()
    
    def process_withdrawal(self, popup, method):
        amount = float(self.withdraw_amount.text or 0)
        
        bank_details = {
            'account_holder': Security.sanitize_input(self.account_holder.text),
            'account_number': Security.sanitize_input(self.account_number.text),
            'ifsc_code': Security.sanitize_input(self.ifsc_code.text)
        }
        
        if not all(bank_details.values()):
            show_popup('Error', 'All bank detail fields are required.')
            return
            
        app = App.get_running_app()
        app.process_withdrawal_payment(amount, bank_details, method, popup)
    
    def logout(self, instance):
        app = App.get_running_app()
        if hasattr(app, 'user_id'):
            delattr(app, 'user_id')
        app.root.current = 'auth'
        show_popup('Info', 'Logged out successfully')

    def show_support_popup(self, instance):
        """Shows the customer support popup."""
        show_support()

class InvestKarApp(App):  # ✅ Changed from InvestmentApp
    def build(self):
        self.title = 'Invest Kar - Grow Your Money'  # ✅ Updated
        self.user_id = None

        # Initialize the database in the correct user data directory
        global db
        db_path = self.user_data_dir + '/investkar_data.db'  # ✅ Updated DB name
        
        # Ensure the user data directory exists
        os.makedirs(self.user_data_dir, exist_ok=True)
        
        # Run database validation and optimization on startup
        validate_database(db_path)
        optimize_app(db_path)
        
        db = Database(db_path)
        db.initialize_plans(INVESTMENT_PLANS)
        # Calculate any missed daily returns on app start
        db.calculate_daily_returns()
        
        self.sm = ScreenManager()
        
        # Add screens
        self.auth_screen = AuthScreen(name='auth')
        self.home_screen = HomeScreen(name='home')
        self.invest_screen = InvestScreen(name='invest')
        self.profile_screen = ProfileScreen(name='profile')
        self.admin_screen = AdminScreen(name='admin')
        
        self.sm.add_widget(self.auth_screen)
        self.sm.add_widget(self.home_screen)
        self.sm.add_widget(self.invest_screen)
        self.sm.add_widget(self.profile_screen)
        self.sm.add_widget(self.admin_screen)

        return self.sm
    
    def show_verification_popup(self, payment_type, plan_id, amount, method, transaction_id, user_phone):
        popup = ModalView(size_hint=(0.8, 0.6), auto_dismiss=False)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        
        if payment_type == 'investment':
            title = '🔄 Verifying Investment'
            message = 'Payment initiated. Your investment will be activated once confirmed. This may take a few minutes.'
        else:
            title = '🔄 Verifying Withdrawal'
            message = 'Fee payment initiated. Your withdrawal will be processed once confirmed.'
        
        layout.add_widget(Label(text=title, font_size='18sp', bold=True))
        
        layout.add_widget(Label(text=message, font_size='14sp', halign='center'))
        
        # IMPORTANT: The actual database update (e.g., db.add_investment)
        # must now be triggered by a secure, server-side webhook from your payment gateway.
        # The client no longer handles verification.
        
        close_btn = Button(text='OK', size_hint_y=None, height=50)
        close_btn.bind(on_press=popup.dismiss)
        layout.add_widget(close_btn)
        
        popup.add_widget(layout)
        popup.open()
        
    def process_withdrawal_payment(self, amount, bank_details, method, popup):
        # This method is now part of the App class
        user = db.get_user(self.user_id)
        success, message = db.create_withdrawal_request(self.user_id, amount, bank_details)
        if not success:
            show_popup('Error', message)
            return
        
        # Generate payment link for the withdrawal fee
        payment_result = upi_payment.generate_withdrawal_payment(
            amount=10, # Fixed withdrawal fee
            user_phone=user[1],
            method=method,
            user_id=self.user_id
        )
        if payment_result['success']:
            webbrowser.open(payment_result['payment_url'])
            popup.dismiss()
            self.show_verification_popup(
                'withdrawal', None, amount, method,
                payment_result['transaction_id'], user[1]
            )

if __name__ == '__main__':
    InvestKarApp().run()  # ✅ Updated