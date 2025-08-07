import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
from .handlers import admin_handlers, user_handlers, tournament_handlers
from .handlers.admin_handlers import is_admin

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text(
        'Добро пожаловать в бот для проведения турниров! Используйте /help для просмотра списка команд.'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a list of available commands, differentiating between users and admins."""
    user = update.effective_user

    user_help_text = (
        "**Доступные команды:**\n"
        "/start - Приветственное сообщение\n"
        "/help - Показать это сообщение\n"
        "/register - Начать регистрацию на турнир\n"
        "/my_status - Проверить свой статус и текущий матч\n"
        "/bracket - Показать турнирную сетку"
    )

    admin_help_text = (
        "\n\n**Команды для администраторов:**\n"
        "/broadcast <сообщение> - Отправить объявление всем участникам\n"
        "/open_registration - Открыть регистрацию\n"
        "/close_registration - Закрыть регистрацию\n"
        "/set_mode_nickname - Установить режим 'только никнейм'\n"
        "/set_mode_character - Установить режим 'никнейм и персонаж'\n"
        "/start_tournament - Начать турнир\n"
        "/reset_tournament - Сбросить турнир"
    )

    if is_admin(user.id):
        await update.message.reply_text(user_help_text + admin_help_text, parse_mode='Markdown')
    else:
        await update.message.reply_text(user_help_text, parse_mode='Markdown')

from config import TELEGRAM_TOKEN

def main():
    """Start the bot."""
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11":
        logger.error("TELEGRAM_TOKEN не настроен в файле config.py. Пожалуйста, укажите токен вашего бота.")
        return

    # Create the Application and pass it your bot's token.
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Admin commands
    application.add_handler(CommandHandler("open_registration", admin_handlers.open_registration))
    application.add_handler(CommandHandler("close_registration", admin_handlers.close_registration))
    application.add_handler(CommandHandler("set_mode_nickname", admin_handlers.set_mode_nickname))
    application.add_handler(CommandHandler("set_mode_character", admin_handlers.set_mode_character))
    application.add_handler(CommandHandler("start_tournament", tournament_handlers.start_tournament))
    application.add_handler(CommandHandler("reset_tournament", tournament_handlers.reset_tournament))
    application.add_handler(CommandHandler("broadcast", admin_handlers.broadcast))

    # User commands
    reg_handler = ConversationHandler(
        entry_points=[CommandHandler("register", user_handlers.register_start)],
        states={
            user_handlers.NICKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_handlers.received_nickname)],
            user_handlers.CHARACTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, user_handlers.received_character)],
        },
        fallbacks=[CommandHandler("cancel", user_handlers.cancel_registration)],
    )
    application.add_handler(reg_handler)
    application.add_handler(CommandHandler("my_status", user_handlers.my_status))
    application.add_handler(CommandHandler("bracket", user_handlers.display_bracket))
    application.add_handler(CallbackQueryHandler(tournament_handlers.match_management_callback, pattern='^(win|dq)_'))


    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == '__main__':
    main()
