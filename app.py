from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
import random
import os
import uuid
import requests
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-this'

# ============ Email Service ============
class EmailService:
    def __init__(self):
        self.api_key = "re_QFEQRkrB_KkSUju5HT3cao7aYMzd24wa6"
        self.sender = "مراد بنك <onboarding@resend.dev>"
        self.api_url = "https://api.resend.com/emails"
    
    def send(self, to_email, subject, html_body):
        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": self.sender,
                    "to": to_email,
                    "subject": subject,
                    "html": html_body
                }
            )
            if response.status_code == 200:
                print(f"✅ تم الإرسال إلى {to_email}")
                return True
            else:
                print(f"❌ خطأ: {response.json()}")
                return False
        except Exception as e:
            print(f"❌ خطأ: {e}")
            return False

email_service = EmailService()

# ============ Database Functions ============
def load_data():
    try:
        with open("users.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_data(users):
    with open("users.json", "w") as file:
        json.dump(users, file, indent=4)

# ============ Decorators ============
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('غير مصرح لك بالدخول', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'account_number' not in session:
            flash('يجب تسجيل الدخول أولاً', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ============ Routes ============
@app.route('/')
def index():
    if 'account_number' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        email = request.form.get('email', '')
        phone = request.form.get('phone', '---')
        
        if len(password) < 6:
            flash('كلمة المرور يجب أن تكون 6 أحرف على الأقل', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('كلمات المرور غير متطابقة', 'error')
            return render_template('register.html')
        
        users = load_data()
        
        while True:
            account_number = str(random.randint(1000000, 9999999))
            if account_number not in users:
                break
        
        users[account_number] = {
            "username": username,
            "password": password,
            "email": email,
            "phone": phone,
            "role": "user",
            "balance": 0,
            "history": []
        }
        
        save_data(users)
        
        if email:
            try:
                email_service.send(
                    email,
                    "🏦 مرحباً بك في مراد بنك",
                    f"""
                    <div style="font-family: 'Cairo', sans-serif; max-width: 500px; margin: auto; border-radius: 16px; overflow: hidden; border: 1px solid #eee;">
                        <div style="background: #d50000; color: white; padding: 24px; text-align: center;">
                            <h1 style="margin: 0;">🏦 مراد بنك</h1>
                            <p style="margin: 8px 0 0;">مرحباً بك!</p>
                        </div>
                        <div style="padding: 24px; background: white;">
                            <p>عزيزي <strong>{username}</strong>،</p>
                            <p>تم إنشاء حسابك بنجاح.</p>
                            <div style="background: #f5f5f5; padding: 16px; border-radius: 12px; margin: 16px 0;">
                                <p style="margin: 8px 0;">🔢 <strong>رقم الحساب:</strong> {account_number}</p>
                                <p style="margin: 8px 0;">💰 <strong>الرصيد:</strong> 0 ج.م</p>
                            </div>
                        </div>
                    </div>
                    """
                )
            except:
                pass
        
        flash(f'تم إنشاء الحساب بنجاح! رقم حسابك هو: {account_number}', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        account_number = request.form['account_number']
        password = request.form['password']
        
        users = load_data()
        
        if account_number not in users:
            flash('رقم الحساب غير موجود', 'error')
            return render_template('login.html')
        
        if users[account_number]['password'] != password:
            flash('كلمة المرور خاطئة', 'error')
            return render_template('login.html')
        
        session['account_number'] = account_number
        session['username'] = users[account_number]['username']
        session['role'] = users[account_number].get('role', 'user')
        
        flash(f'مرحباً {users[account_number]["username"]}!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    users = load_data()
    account_number = session['account_number']
    user_data = users[account_number]
    
    return render_template('dashboard.html', 
                         username=user_data['username'],
                         account_number=account_number,
                         balance=user_data['balance'],
                         role=user_data.get('role', 'user'))

@app.route('/deposit', methods=['GET', 'POST'])
@login_required
def deposit():
    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
        except ValueError:
            flash('الرجاء إدخال مبلغ صحيح', 'error')
            return render_template('deposit.html')
        
        if amount <= 0:
            flash('المبلغ يجب أن يكون أكبر من صفر', 'error')
            return render_template('deposit.html')
        
        users = load_data()
        account_number = session['account_number']
        
        users[account_number]['balance'] += amount
        users[account_number]['history'].append(f"إيداع: +{amount} جنيه")
        
        save_data(users)
        
        user_email = users[account_number].get('email')
        if user_email:
            try:
                email_service.send(
                    user_email,
                    f"✅ تم إيداع {amount} ج.م",
                    f"""
                    <div style="font-family: 'Cairo', sans-serif; max-width: 500px; margin: auto; border-radius: 16px; overflow: hidden; border: 1px solid #eee;">
                        <div style="background: #00c853; color: white; padding: 24px; text-align: center;">
                            <h1 style="margin: 0;">🏦 مراد بنك</h1>
                            <p style="margin: 8px 0 0;">✅ تم الإيداع بنجاح</p>
                        </div>
                        <div style="padding: 24px; background: white;">
                            <p>عزيزي <strong>{users[account_number]['username']}</strong>،</p>
                            <div style="background: #f5f5f5; padding: 16px; border-radius: 12px; margin: 16px 0;">
                                <p style="margin: 8px 0;">💰 <strong>المبلغ:</strong> {amount} ج.م</p>
                                <p style="margin: 8px 0;">💳 <strong>الرصيد:</strong> {users[account_number]['balance']} ج.م</p>
                            </div>
                        </div>
                    </div>
                    """
                )
            except:
                pass
        
        flash(f'تم إيداع {amount} جنيه بنجاح!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('deposit.html')

@app.route('/transfer', methods=['GET', 'POST'])
@login_required
def transfer():
    if request.method == 'POST':
        receiver = request.form['receiver']
        
        try:
            amount = float(request.form['amount'])
        except ValueError:
            flash('الرجاء إدخال مبلغ صحيح', 'error')
            return render_template('transfer.html')
        
        if amount <= 0:
            flash('المبلغ يجب أن يكون أكبر من صفر', 'error')
            return render_template('transfer.html')
        
        users = load_data()
        sender = session['account_number']
        
        if receiver not in users:
            flash('رقم حساب المستلم غير موجود', 'error')
            return render_template('transfer.html')
        
        if receiver == sender:
            flash('لا يمكنك التحويل لنفسك', 'error')
            return render_template('transfer.html')
        
        if amount > users[sender]['balance']:
            flash('رصيدك غير كافي', 'error')
            return render_template('transfer.html')
        
        users[sender]['balance'] -= amount
        users[receiver]['balance'] += amount
        
        comment = request.form.get('comment', 'تحويل')
        
        users[sender]['history'].append(
            f"تحويل إلى {users[receiver]['username']}: -{amount} جنيه"
        )
        users[receiver]['history'].append(
            f"استلام من {users[sender]['username']}: +{amount} جنيه"
        )
        
        save_data(users)
        
        transaction_id = str(uuid.uuid4())[:8].upper()
        session['last_transaction_id'] = f"TRX{transaction_id}"
        session['last_transaction_date'] = datetime.now().strftime('%Y-%m-%d %H:%M')
        session['last_receiver'] = receiver
        session['last_receiver_name'] = users[receiver]['username']
        session['last_receiver_phone'] = users[receiver].get('phone', '---')
        session['last_amount'] = amount
        session['last_comment'] = comment
        
        sender_email = users[sender].get('email')
        if sender_email:
            try:
                email_service.send(
                    sender_email,
                    f"✅ تم تحويل {amount} ج.م",
                    f"""
                    <div style="font-family: 'Cairo', sans-serif; max-width: 500px; margin: auto; border-radius: 16px; overflow: hidden; border: 1px solid #eee;">
                        <div style="background: #d50000; color: white; padding: 24px; text-align: center;">
                            <h1 style="margin: 0;">🏦 مراد بنك</h1>
                            <p style="margin: 8px 0 0;">✅ تم التحويل بنجاح</p>
                        </div>
                        <div style="padding: 24px; background: white;">
                            <p>عزيزي <strong>{users[sender]['username']}</strong>،</p>
                            <div style="background: #f5f5f5; padding: 16px; border-radius: 12px; margin: 16px 0;">
                                <p style="margin: 8px 0;">💰 <strong>المبلغ:</strong> {amount} ج.م</p>
                                <p style="margin: 8px 0;">👤 <strong>المستلم:</strong> {users[receiver]['username']}</p>
                                <p style="margin: 8px 0;">💳 <strong>رصيدك:</strong> {users[sender]['balance']} ج.م</p>
                            </div>
                        </div>
                    </div>
                    """
                )
            except:
                pass
        
        receiver_email = users[receiver].get('email')
        if receiver_email:
            try:
                email_service.send(
                    receiver_email,
                    f"📥 تم استلام {amount} ج.م",
                    f"""
                    <div style="font-family: 'Cairo', sans-serif; max-width: 500px; margin: auto; border-radius: 16px; overflow: hidden; border: 1px solid #eee;">
                        <div style="background: #00c853; color: white; padding: 24px; text-align: center;">
                            <h1 style="margin: 0;">🏦 مراد بنك</h1>
                            <p style="margin: 8px 0 0;">📥 تم استلام حوالة</p>
                        </div>
                        <div style="padding: 24px; background: white;">
                            <p>عزيزي <strong>{users[receiver]['username']}</strong>،</p>
                            <div style="background: #f5f5f5; padding: 16px; border-radius: 12px; margin: 16px 0;">
                                <p style="margin: 8px 0;">💰 <strong>المبلغ:</strong> {amount} ج.م</p>
                                <p style="margin: 8px 0;">👤 <strong>المرسل:</strong> {users[sender]['username']}</p>
                                <p style="margin: 8px 0;">💳 <strong>رصيدك:</strong> {users[receiver]['balance']} ج.م</p>
                            </div>
                        </div>
                    </div>
                    """
                )
            except:
                pass
        
        return redirect(url_for('transfer_success'))
    
    return render_template('transfer.html')

@app.route('/transfer/success')
@login_required
def transfer_success():
    return render_template('transfer_success.html',
        transaction_id=session.get('last_transaction_id', 'TRX000000'),
        transaction_date=session.get('last_transaction_date', datetime.now().strftime('%Y-%m-%d %H:%M')),
        sender_account=session.get('account_number', '0000000'),
        receiver_account=session.get('last_receiver', '0000000'),
        receiver_name=session.get('last_receiver_name', '---'),
        receiver_phone=session.get('last_receiver_phone', '---'),
        amount=session.get('last_amount', 0),
        comment=session.get('last_comment', 'تحويل')
    )

@app.route('/history')
@login_required
def history():
    users = load_data()
    account_number = session['account_number']
    user_history = users[account_number]['history']
    
    return render_template('history.html', history=user_history[::-1])

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_password = request.form['old_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        if len(new_password) < 6:
            flash('كلمة المرور الجديدة يجب أن تكون 6 أحرف على الأقل', 'error')
            return render_template('change_password.html')
        
        if new_password != confirm_password:
            flash('كلمات المرور غير متطابقة', 'error')
            return render_template('change_password.html')
        
        users = load_data()
        account_number = session['account_number']
        
        if users[account_number]['password'] != old_password:
            flash('كلمة المرور القديمة خاطئة', 'error')
            return render_template('change_password.html')
        
        users[account_number]['password'] = new_password
        save_data(users)
        
        flash('تم تغيير كلمة المرور بنجاح!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('change_password.html')

@app.route('/create-admin')
def create_admin():
    users = load_data()
    
    users['0000001'] = {
        "username": "مدير النظام",
        "password": "admin123",
        "email": "admin@muradbank.com",
        "phone": "---",
        "role": "admin",
        "balance": 0,
        "history": []
    }
    
    save_data(users)
    return '✅ تم إنشاء حساب المدير - رقم الحساب: 0000001 - كلمة المرور: admin123'

@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    users = load_data()
    
    total_users = len(users)
    total_balance = sum(u['balance'] for u in users.values())
    total_transactions = sum(len(u.get('history', [])) for u in users.values())
    
    users_list = []
    for acc, data in users.items():
        users_list.append({
            'account': acc,
            'username': data['username'],
            'balance': data['balance'],
            'transactions': len(data.get('history', [])),
            'role': data.get('role', 'user')
        })
    
    users_list.sort(key=lambda x: x['balance'], reverse=True)
    
    return render_template('admin.html',
        total_users=total_users,
        total_balance=total_balance,
        total_transactions=total_transactions,
        users=users_list[:20]
    )

@app.route('/admin/delete/<account>')
@login_required
@admin_required
def admin_delete_user(account):
    users = load_data()
    
    if account in users and users[account].get('role') != 'admin':
        del users[account]
        save_data(users)
        flash(f'تم حذف الحساب {account}', 'success')
    else:
        flash('لا يمكن حذف هذا الحساب', 'error')
    
    return redirect(url_for('admin_panel'))

@app.route('/logout')
def logout():
    session.clear()
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)