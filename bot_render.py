import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from datetime import datetime
from flask import Flask
from threading import Thread

# ======== FLASK ДЛЯ ПИНГОВ (ЧТОБЫ НЕ ЗАСЫПАЛ) ========
app = Flask(__name__)

@app.route('/')
def home():
    return f"🤖 Бот работает! Время: {datetime.now().strftime('%H:%M %d.%m.%Y')}"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

keep_alive()
# ======== КОНЕЦ FLASK КОДА ========

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем данные из переменных окружения
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID'))

print("=" * 50)
print("🤖 БОТ ЗАПУЩЕН НА RENDER.COM!")
print(f"⏰ Время запуска: {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}")
print("=" * 50)

async def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start"""
    user = update.effective_user
    
    if user.id == ADMIN_ID:
        await update.message.reply_text(
            f"👑 Привет, создатель!\n\n"
            "Я работаю на Render.com 24/7! ⚡\n"
            "Статус: ✅ Онлайн\n\n"
            "Теперь ты будешь получать все анонимные сообщения!"
        )
    else:
        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n\n"
            "Я бот для анонимных сообщений. Отправь мне любое сообщение "
            "и я перешлю его создателю анонимно! ✨"
        )

async def handle_message(update: Update, context: CallbackContext) -> None:
    """Обработчик всех входящих сообщений"""
    user = update.effective_user
    message = update.message
    
    if user.id == ADMIN_ID:
        return
    
    current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    
    admin_message = f"📨 *НОВОЕ СООБЩЕНИЕ*\n"
    admin_message += f"*Время:* {current_time}\n"
    admin_message += f"*От:* {user.first_name}"
    if user.last_name:
        admin_message += f" {user.last_name}"
    admin_message += f"\n*Username:* @{user.username}" if user.username else "\n*Username:* не указан"
    admin_message += f"\n*ID:* `{user.id}`"
    
    if message.text:
        admin_message += f"\n*Текст:* {message.text}"
    
    keyboard = [
        [InlineKeyboardButton("💌 Ответить", callback_data=f"reply_{user.id}")],
        [InlineKeyboardButton("👤 Инфо", callback_data=f"info_{user.id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if message.text:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            forwarded_msg = await message.forward(chat_id=ADMIN_ID)
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_message,
                parse_mode='Markdown',
                reply_markup=reply_markup,
                reply_to_message_id=forwarded_msg.message_id
            )
        
        await message.reply_text("✅ Сообщение доставлено создателю!")
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.reply_text("❌ Ошибка при отправке. Попробуйте позже.")

async def button_handler(update: Update, context: CallbackContext) -> None:
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != ADMIN_ID:
        return
        
    data = query.data
    action, user_id = data.split('_')
    user_id = int(user_id)
    
    if action == "reply":
        await query.message.reply_text(
            f"💌 Для ответа пользователю {user_id} используй команду:\n"
            f"`/reply {user_id} ваш_текст`",
            parse_mode='Markdown'
        )
            
    elif action == "info":
        try:
            user_info = await context.bot.get_chat(user_id)
            info_text = f"👤 *Информация об отправителе:*\n"
            info_text += f"*Имя:* {user_info.first_name}"
            if user_info.last_name:
                info_text += f" {user_info.last_name}"
            info_text += f"\n*Username:* @{user_info.username}" if user_info.username else "\n*Username:* не указан"
            info_text += f"\n*ID:* `{user_info.id}`"
            
            await query.message.reply_text(info_text, parse_mode='Markdown')
        except Exception as e:
            await query.message.reply_text(f"❌ Ошибка получения информации: {e}")

async def reply_command(update: Update, context: CallbackContext) -> None:
    """Команда для ответа конкретному пользователю"""
    if update.effective_user.id != ADMIN_ID:
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Использование:\n"
            "`/reply <user_id> <сообщение>`\n\n"
            "Пример:\n"
            "`/reply 123456789 Привет! Как дела?`",
            parse_mode='Markdown'
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        message_text = ' '.join(context.args[1:])
        
        await context.bot.send_message(
            chat_id=target_user_id,
            text=f"💌 Сообщение от администратора:\n\n{message_text}"
        )
        await update.message.reply_text("✅ Ответ отправлен анонимно!")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при отправке: {e}")

def main():
    """Запуск бота"""
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("reply", reply_command))
        application.add_handler(MessageHandler(filters.ALL & ~filters.User(ADMIN_ID), handle_message))
        application.add_handler(CallbackQueryHandler(button_handler))
        
        logger.info("🚀 Бот запущен и работает...")
        print("✅ Бот успешно запущен!")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        raise

if __name__ == '__main__':
    main()
