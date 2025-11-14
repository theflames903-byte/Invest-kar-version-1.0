from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.modalview import ModalView
import sqlite3
from kivy.logger import Logger

def show_popup(title, message):
    """Show a simple popup message using Kivy's Popup widget."""
    # The content of a Popup is a single widget.
    # We create a layout to hold our message and button.
    content = BoxLayout(orientation='vertical', padding=10, spacing=10)
    
    # Add the message label and a button to close the popup.
    content.add_widget(Label(text=message, halign='center'))
    close_btn = Button(text='Close', size_hint_y=None, height=44)
    
    popup = Popup(
        title=title,
        content=content,
        size_hint=(0.8, 0.4)
    )
    close_btn.bind(on_press=popup.dismiss)
    content.add_widget(close_btn)
    popup.open()

def show_loading(message="Loading..."):
    """Shows a non-dismissible loading popup. Returns the popup instance."""
    loading_popup = ModalView(size_hint=(0.6, 0.2), auto_dismiss=False)
    layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
    layout.add_widget(Label(text=message, font_size='16sp'))
    loading_popup.add_widget(layout)
    loading_popup.open()
    return loading_popup

def hide_loading(popup_instance):
    """Dismisses a given popup instance."""
    if popup_instance:
        popup_instance.dismiss()

def validate_database(db_path="investkar_data.db"):
    """Checks if all required database tables exist."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check all tables exist
        tables = ['users', 'investments', 'transactions', 'withdrawal_requests', 'payment_intents', 'otp_store']
        all_ok = True
        for table in tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not cursor.fetchone():
                Logger.error(f"Database Validation: Missing table: {table}")
                all_ok = False
        
        if all_ok:
            Logger.info("Database Validation: All tables are present.")
        
        conn.close()
        return all_ok
    except Exception as e:
        Logger.error(f"Database Validation: Failed to connect or validate - {e}")
        return False

def optimize_app(db_path="investkar_data.db"):
    """Adds database indexes for performance optimization."""
    try:
        # 1. Add database indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone)",
            "CREATE INDEX IF NOT EXISTS idx_investments_user ON investments(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_payment_intents_txn ON payment_intents(transaction_id)"
        ]
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        for index in indexes:
            cursor.execute(index)
        conn.commit()
        conn.close()
        Logger.info("Database Optimization: Indexes applied successfully.")
    except Exception as e:
        Logger.error(f"Database Optimization: Failed to apply indexes - {e}")

def show_support():
    """Displays a popup with customer support information."""
    support_text = """[b]📞 Customer Support[/b]

Phone: 9308691451
Email: support@investkar.com
Hours: 10 AM - 6 PM

[b]For payment issues:[/b]
1. Share transaction screenshot
2. Include transaction ID
3. Mention your phone number"""
    show_popup('Support', support_text)