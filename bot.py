import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from datetime import datetime

# تنظیمات
BOT_TOKEN = "8198774412:AAHphDh2Wo9Nzgomlk9xq9y3aeETsVpkXr0"
ADMIN_ID = 327855654  # آیدی عددی ادمین

# تنظیم لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# دیتابیس
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('users.db', check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # جدول کاربران
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TEXT
            )
        ''')
        
        # جدول پیام‌ها
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message_text TEXT,
                message_type TEXT,
                admin_id INTEGER,
                admin_reply TEXT,
                status TEXT,
                created_at TEXT,
                replied_at TEXT
            )
        ''')
        
        self.conn.commit()
    
    def add_user(self, user_id, username, first_name, last_name):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users 
            (user_id, username, first_name, last_name, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, datetime.now().isoformat()))
        self.conn.commit()
    
    def add_message(self, user_id, message_text, message_type="user"):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO messages 
            (user_id, message_text, message_type, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, message_text, message_type, "pending", datetime.now().isoformat()))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_pending_messages(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT m.*, u.username, u.first_name, u.last_name 
            FROM messages m
            JOIN users u ON m.user_id = u.user_id
            WHERE m.status = 'pending' AND m.message_type = 'user'
            ORDER BY m.created_at
        ''')
        return cursor.fetchall()
    
    def get_user_messages(self, user_id, limit=10):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM messages 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (user_id, limit))
        return cursor.fetchall()
    
    def update_message_status(self, message_id, status, admin_id=None, admin_reply=None):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE messages 
            SET status = ?, admin_id = ?, admin_reply = ?, replied_at = ?
            WHERE id = ?
        ''', (status, admin_id, admin_reply, datetime.now().isoformat(), message_id))
        self.conn.commit()
    
    def get_all_users(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT u.*, 
                   (SELECT COUNT(*) FROM messages WHERE user_id = u.user_id AND message_type = 'user') as message_count,
                   (SELECT COUNT(*) FROM messages WHERE user_id = u.user_id AND status = 'pending') as pending_count
            FROM users u
            ORDER BY u.created_at DESC
        ''')
        return cursor.fetchall()

db = Database()

# دستورات ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name, user.last_name)
    
    welcome_text = """
👋 به ربات پشتیبانی خوش آمدید!

هر پیامی دارید می‌توانید همینجا ارسال کنید.
پشتیبان‌ها به زودی پاسخ شما را می‌دهند.
    """
    
    await update.message.reply_text(welcome_text)

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message_text = update.message.text
    
    # ذخیره کاربر
    db.add_user(user.id, user.username, user.first_name, user.last_name)
    
    # ذخیره پیام
    message_id = db.add_message(user.id, message_text)
    
    # اطلاع به ادمین
    await notify_admin(context, user, message_text, message_id)
    
    await update.message.reply_text("✅ پیام شما دریافت شد و در صف پاسخ قرار گرفت.")

async def notify_admin(context, user, message_text, message_id):
    admin_text = f"""
📩 پیام جدید از کاربر:

👤 کاربر: {user.first_name} {f'({user.username})' if user.username else ''}
🆔 آیدی: {user.id}
💬 پیام: {message_text}

برای پاسخ دادن از دستور /reply استفاده کنید.
    """
    
    keyboard = [
        [InlineKeyboardButton("📋 مشاهده لیست کاربران", callback_data="show_users")],
        [InlineKeyboardButton("📥 پیام‌های در انتظار", callback_data="pending_messages")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_text,
        reply_markup=reply_markup
    )

# دستورات ادمین
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ دسترسی denied.")
        return
    
    users_count = len(db.get_all_users())
    pending_messages = len(db.get_pending_messages())
    
    panel_text = f"""
🛠️ پنل مدیریت

📊 آمار:
👥 تعداد کاربران: {users_count}
📨 پیام‌های در انتظار: {pending_messages}

دستورات موجود:
/users - مشاهده لیست کاربران
/pending - پیام‌های در انتظار پاسخ
/reply - پاسخ به کاربر
    """
    
    await update.message.reply_text(panel_text)

async def show_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ دسترسی denied.")
        return
    
    users = db.get_all_users()
    
    if not users:
        await update.message.reply_text("📭 هیچ کاربری وجود ندارد.")
        return
    
    users_text = "👥 لیست کاربران:\n\n"
    
    for user in users:
        user_id, username, first_name, last_name, created_at, message_count, pending_count = user
        users_text += f"""
👤 {first_name} {last_name or ''}
🆔 آیدی: {user_id}
📧 @{username or 'ندارد'}
📨 پیام‌ها: {message_count} (⏳ {pending_count})
⏰ عضویت: {created_at[:10]}
────────────────────
        """
    
    # اگر متن خیلی طولانی شد، آن را تقسیم می‌کنیم
    if len(users_text) > 4000:
        chunks = [users_text[i:i+4000] for i in range(0, len(users_text), 4000)]
        for chunk in chunks:
            await update.message.reply_text(chunk)
    else:
        await update.message.reply_text(users_text)

async def pending_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ دسترسی denied.")
        return
    
    messages = db.get_pending_messages()
    
    if not messages:
        await update.message.reply_text("✅ هیچ پیام در انتظاری وجود ندارد.")
        return
    
    for msg in messages:
        msg_id, user_id, message_text, msg_type, admin_id, admin_reply, status, created_at, replied_at = msg
        username, first_name, last_name = msg[8], msg[9], msg[10]
        
        message_info = f"""
📨 پیام در انتظار (ID: {msg_id})

👤 کاربر: {first_name} {last_name or ''}
🆔 آیدی: {user_id}
📧 @{username or 'ندارد'}
💬 پیام: {message_text}
⏰ زمان: {created_at[:16]}

برای پاسخ:
/reply_{msg_id} متن پاسخ
        """
        
        keyboard = [
            [
                InlineKeyboardButton("✅ پاسخ", callback_data=f"reply_{msg_id}"),
                InlineKeyboardButton("❌ رد", callback_data=f"reject_{msg_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message_info, reply_markup=reply_markup)

async def reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ دسترسی denied.")
        return
    
    if not context.args:
        await update.message.reply_text("""
❌ فرمت دستور:
/reply_123456 متن پاسخ

یا
/reply
123456
متن پاسخ
        """)
        return
    
    # پردازش دستور
    command_text = ' '.join(context.args)
    
    if '_' in context.args[0]:
        # فرمت: /reply_123456 متن پاسخ
        try:
            message_id = int(context.args[0].split('_')[1])
            reply_text = ' '.join(context.args[1:])
        except:
            await update.message.reply_text("❌ فرمت اشتباه")
            return
    else:
        # فرمت: /reply سپس آیدی و متن
        if len(context.args) < 2:
            await update.message.reply_text("❌ لطفاً آیدی پیام و متن پاسخ را وارد کنید")
            return
        
        try:
            message_id = int(context.args[0])
            reply_text = ' '.join(context.args[1:])
        except:
            await update.message.reply_text("❌ آیدی پیام باید عدد باشد")
            return
    
    # پیدا کردن پیام
    messages = db.get_pending_messages()
    target_message = None
    
    for msg in messages:
        if msg[0] == message_id:
            target_message = msg
            break
    
    if not target_message:
        await update.message.reply_text("❌ پیام مورد نظر یافت نشد")
        return
    
    # ارسال پاسخ به کاربر
    try:
        user_id = target_message[1]
        response_text = f"""
📨 پاسخ پشتیبان:

{reply_text}

────────────────
💬 پیام شما: {target_message[2]}
        """
        
        await context.bot.send_message(chat_id=user_id, text=response_text)
        
        # آپدیت وضعیت در دیتابیس
        db.update_message_status(
            message_id=message_id,
            status="replied",
            admin_id=ADMIN_ID,
            admin_reply=reply_text
        )
        
        await update.message.reply_text("✅ پاسخ با موفقیت ارسال شد")
        
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ارسال پاسخ: {str(e)}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "show_users":
        await show_users(update, context)
    
    elif query.data == "pending_messages":
        await pending_messages(update, context)
    
    elif query.data.startswith("reply_"):
        message_id = int(query.data.split("_")[1])
        await query.edit_message_text(
            f"📨 برای پاسخ به پیام {message_id} از دستور زیر استفاده کنید:\n\n"
            f"/reply_{message_id} متن پاسخ شما"
        )
    
    elif query.data.startswith("reject_"):
        message_id = int(query.data.split("_")[1])
        
        # پیدا کردن پیام
        messages = db.get_pending_messages()
        target_message = None
        
        for msg in messages:
            if msg[0] == message_id:
                target_message = msg
                break
        
        if target_message:
            # آپدیت وضعیت
            db.update_message_status(
                message_id=message_id,
                status="rejected",
                admin_id=ADMIN_ID,
                admin_reply="پیام به دلیل عدم پرداخت رد شد"
            )
            
            # ارسال پیام به کاربر
            try:
                user_id = target_message[1]
                await context.bot.send_message(
                    chat_id=user_id,
                    text="❌ پیام شما به دلیل عدم پرداخت توسط سیستم رد شد."
                )
            except:
                pass
            
            await query.edit_message_text("✅ پیام کاربر رد شد")

def main():
    # ساخت اپلیکیشن
    application = Application.builder().token(BOT_TOKEN).build()
    
    # هندلرهای کاربران
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))
    
    # هندلرهای ادمین
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("users", show_users))
    application.add_handler(CommandHandler("pending", pending_messages))
    application.add_handler(CommandHandler("reply", reply_to_user))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # اجرای ربات
    application.run_polling()
    print("🤖 ربات فعال شد...")

if __name__ == '__main__':
    main()
