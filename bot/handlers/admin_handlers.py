import asyncio
from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..data.database import get_db_connection
from config import ADMIN_IDS

def is_admin(telegram_id: int) -> bool:
    """Checks if a user is an admin by checking against the ADMIN_IDS list in config.py."""
    return telegram_id in ADMIN_IDS

def admin_required(func):
    """Decorator to restrict access to admins."""
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not is_admin(user.id):
            await update.message.reply_text("У вас нет прав для использования этой команды.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

@admin_required
async def open_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Opens tournament registration."""
    conn = get_db_connection()
    if conn is None:
        await update.message.reply_text("Не удалось подключиться к базе данных.")
        return
    cursor = conn.cursor()
    cursor.execute("UPDATE tournament_status SET registration_open = 1 WHERE id = 1")
    conn.commit()
    cursor.close()
    conn.close()
    await update.message.reply_text("Регистрация на турнир открыта.")

@admin_required
async def close_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Closes tournament registration."""
    conn = get_db_connection()
    if conn is None:
        await update.message.reply_text("Не удалось подключиться к базе данных.")
        return
    cursor = conn.cursor()
    cursor.execute("UPDATE tournament_status SET registration_open = 0 WHERE id = 1")
    conn.commit()
    cursor.close()
    conn.close()
    await update.message.reply_text("Регистрация на турнир закрыта.")

@admin_required
async def set_mode_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sets the registration mode to nickname only."""
    conn = get_db_connection()
    if conn is None:
        await update.message.reply_text("Не удалось подключиться к базе данных.")
        return
    cursor = conn.cursor()
    cursor.execute("UPDATE tournament_status SET mode = 'nickname' WHERE id = 1")
    conn.commit()
    cursor.close()
    conn.close()
    await update.message.reply_text("Режим регистрации изменен: только никнейм.")

@admin_required
async def set_mode_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sets the registration mode to nickname and character."""
    conn = get_db_connection()
    if conn is None:
        await update.message.reply_text("Не удалось подключиться к базе данных.")
        return
    cursor = conn.cursor()
    cursor.execute("UPDATE tournament_status SET mode = 'character' WHERE id = 1")
    conn.commit()
    cursor.close()
    conn.close()
    await update.message.reply_text("Режим регистрации изменен: никнейм и персонаж.")

@admin_required
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a message to all registered participants."""
    message_text = " ".join(context.args)
    if not message_text:
        await update.message.reply_text("Использование: /broadcast <сообщение>")
        return

    conn = get_db_connection()
    if conn is None:
        await update.message.reply_text("Не удалось подключиться к базе данных.")
        return
    cursor = conn.cursor()

    cursor.execute("SELECT u.telegram_id FROM users u JOIN registrations r ON u.id = r.user_id")
    user_ids = [row['telegram_id'] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    if not user_ids:
        await update.message.reply_text("Нет зарегистрированных участников для отправки сообщения.")
        return

    sent_count = 0
    failed_count = 0
    for user_id in user_ids:
        try:
            await context.bot.send_message(chat_id=user_id, text=f"📢 Объявление от администратора:\n\n{message_text}")
            sent_count += 1
        except Exception as e:
            failed_count += 1
            print(f"Failed to send message to {user_id}: {e}")
        await asyncio.sleep(0.1)  # Avoid hitting rate limits

    await update.message.reply_text(f"Сообщение отправлено.\nУспешно: {sent_count}\nНе удалось: {failed_count}")
