from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from ..data.database import get_db_connection
from config import CHARACTERS

# States for conversation
NICKNAME, CHARACTER = range(2)

async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the registration conversation."""
    user = update.effective_user

    conn = get_db_connection()
    if conn is None:
        await update.message.reply_text("Не удалось подключиться к базе данных.")
        return ConversationHandler.END
    cursor = conn.cursor()

    # Check if registration is open
    cursor.execute("SELECT registration_open, mode FROM tournament_status WHERE id = 1")
    status = cursor.fetchone()
    if not status or not status['registration_open']:
        await update.message.reply_text("Регистрация в данный момент закрыта.")
        cursor.close()
        conn.close()
        return ConversationHandler.END

    # Check if user is already registered
    cursor.execute("SELECT u.id FROM users u JOIN registrations r ON u.id = r.user_id WHERE u.telegram_id = ?", (user.id,))
    if cursor.fetchone():
        await update.message.reply_text("Вы уже зарегистрированы на турнир.")
        cursor.close()
        conn.close()
        return ConversationHandler.END

    # Ensure user is in the users table
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (user.id,))
    db_user = cursor.fetchone()
    if not db_user:
        cursor.execute("INSERT INTO users (telegram_id, username) VALUES (?, ?)", (user.id, user.username))
        conn.commit()
        cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (user.id,))
        db_user = cursor.fetchone()

    context.user_data['user_db_id'] = db_user['id']

    await update.message.reply_text("Пожалуйста, введите ваш игровой никнейм.")

    cursor.close()
    conn.close()
    return NICKNAME

async def received_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives and validates the nickname."""
    nickname = update.message.text

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if nickname is taken
    cursor.execute("SELECT id FROM registrations WHERE nickname = ?", (nickname,))
    if cursor.fetchone():
        await update.message.reply_text("Этот никнейм уже занят. Пожалуйста, выберите другой.")
        return NICKNAME

    context.user_data['nickname'] = nickname

    cursor.execute("SELECT mode FROM tournament_status WHERE id = 1")
    status = cursor.fetchone()
    registration_mode = status['mode']

    if registration_mode == 'nickname':
        user_db_id = context.user_data['user_db_id']
        cursor.execute("INSERT INTO registrations (user_id, nickname) VALUES (?, ?)", (user_db_id, nickname))
        conn.commit()
        await update.message.reply_text(f"Вы успешно зарегистрированы с никнеймом: {nickname}")
        cursor.close()
        conn.close()
        return ConversationHandler.END

    # Mode is 'character'
    if not CHARACTERS:
        await update.message.reply_text("Список персонажей не настроен в файле config.py. Обратитесь к администратору.")
        cursor.close()
        conn.close()
        return ConversationHandler.END

    master_char_list = CHARACTERS

    cursor.execute("SELECT character_name FROM registrations WHERE character_name IS NOT NULL")
    taken_chars = [row['character_name'] for row in cursor.fetchall()]

    available_chars = [char for char in master_char_list if char not in taken_chars]

    if not available_chars:
        await update.message.reply_text("Свободных персонажей не осталось. Обратитесь к администратору.")
        cursor.close()
        conn.close()
        return ConversationHandler.END

    context.user_data['available_chars'] = available_chars

    response_text = "Теперь выберите персонажа из списка, отправив его номер:\n\n"
    for i, char in enumerate(available_chars, 1):
        response_text += f"{i}. {char}\n"

    await update.message.reply_text(response_text)

    cursor.close()
    conn.close()
    return CHARACTER

async def received_character(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receives and validates the character choice."""
    choice = update.message.text
    available_chars = context.user_data.get('available_chars')

    try:
        choice_index = int(choice) - 1
        if 0 <= choice_index < len(available_chars):
            selected_char = available_chars[choice_index]

            conn = get_db_connection()
            cursor = conn.cursor()

            # Double-check if character was taken in the meantime
            cursor.execute("SELECT id FROM registrations WHERE character_name = ?", (selected_char,))
            if cursor.fetchone():
                await update.message.reply_text("Этот персонаж был выбран кем-то другим, пока вы думали. Пожалуйста, попробуйте снова.")
                # Resend the list
                cursor.execute("SELECT character_name FROM registrations WHERE character_name IS NOT NULL")
                taken_chars = [row['character_name'] for row in cursor.fetchall()]
                current_available = [char for char in CHARACTERS if char not in taken_chars]
                context.user_data['available_chars'] = current_available
                response_text = "Выберите персонажа из обновленного списка:\n\n"
                for i, char in enumerate(current_available, 1):
                    response_text += f"{i}. {char}\n"
                await update.message.reply_text(response_text)
                cursor.close()
                conn.close()
                return CHARACTER

            user_db_id = context.user_data['user_db_id']
            nickname = context.user_data['nickname']

            cursor.execute("INSERT INTO registrations (user_id, nickname, character_name) VALUES (?, ?, ?)",
                           (user_db_id, nickname, selected_char))
            conn.commit()

            await update.message.reply_text(f"Вы успешно зарегистрированы с никнеймом '{nickname}' и персонажем '{selected_char}'.")

            cursor.close()
            conn.close()
            return ConversationHandler.END
        else:
            await update.message.reply_text("Неверный номер. Пожалуйста, выберите номер из списка.")
            return CHARACTER
    except ValueError:
        await update.message.reply_text("Пожалуйста, отправьте число.")
        return CHARACTER

async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text('Регистрация отменена.')
    return ConversationHandler.END

async def my_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the user their registration status and current match."""
    user = update.effective_user
    conn = get_db_connection()
    if conn is None:
        await update.message.reply_text("Не удалось подключиться к базе данных.")
        return
    cursor = conn.cursor()

    cursor.execute(
        "SELECT r.nickname, r.character_name "
        "FROM registrations r "
        "JOIN users u ON r.user_id = u.id "
        "WHERE u.telegram_id = ?",
        (user.id,)
    )
    registration = cursor.fetchone()

    if not registration:
        await update.message.reply_text("Вы не зарегистрированы на турнир.")
        cursor.close()
        conn.close()
        return

    nickname = registration['nickname']
    character_name = registration['character_name'] if registration['character_name'] else 'N/A'

    cursor.execute(
        "SELECT m.id, p1.nickname as p1_nick, p2.nickname as p2_nick, m.is_bye "
        "FROM matches m "
        "JOIN registrations r ON r.nickname = ? "
        "LEFT JOIN registrations p1 ON m.player1_id = p1.id "
        "LEFT JOIN registrations p2 ON m.player2_id = p2.id "
        "WHERE (m.player1_id = r.id OR m.player2_id = r.id) AND m.winner_id IS NULL",
        (nickname,)
    )
    match = cursor.fetchone()

    status_text = f"Никнейм: {nickname}\nПерсонаж: {character_name}\n"

    if match:
        if match['is_bye']:
            status_text += "Текущий матч: У вас нет матча в этом раунде."
        else:
            opponent = match['p2_nick'] if match['p1_nick'] == nickname else match['p1_nick']
            status_text += f"Текущий матч: против {opponent} (ID матча: {match['id']})"
    else:
        status_text += "Текущий матч: Нет активного матча."

    await update.message.reply_text(status_text)

    cursor.close()
    conn.close()

async def display_bracket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the current tournament bracket."""
    conn = get_db_connection()
    if conn is None:
        await update.message.reply_text("Не удалось подключиться к базе данных.")
        return
    cursor = conn.cursor()

    cursor.execute("SELECT MAX(round) as max_round FROM matches")
    max_round_row = cursor.fetchone()
    if not max_round_row or not max_round_row['max_round']:
        await update.message.reply_text("Турнир еще не начался. Сетка пуста.")
        cursor.close()
        conn.close()
        return

    max_round = max_round_row['max_round']
    bracket_text = "🏆 **Турнирная сетка** 🏆\n"

    for i in range(1, max_round + 1):
        bracket_text += f"\n--- **Раунд {i}** ---\n"
        cursor.execute(
            "SELECT m.id, m.winner_id, p1.nickname as p1_nick, p2.nickname as p2_nick, w.nickname as winner_nick, m.is_bye "
            "FROM matches m "
            "LEFT JOIN registrations p1 ON m.player1_id = p1.id "
            "LEFT JOIN registrations p2 ON m.player2_id = p2.id "
            "LEFT JOIN registrations w ON m.winner_id = w.id "
            "WHERE m.round = ? "
            "ORDER BY m.id",
            (i,)
        )
        matches = cursor.fetchall()

        if not matches:
            bracket_text += "_Матчи еще не сгенерированы._\n"
            continue

        for match in matches:
            if match['is_bye']:
                bracket_text += f"Матч {match['id']}: {match['p1_nick']} получает техническую победу.\n"
                continue

            p1 = match['p1_nick'] if match['p1_nick'] else '?'
            p2 = match['p2_nick'] if match['p2_nick'] else '?'

            if match['winner_nick']:
                winner = match['winner_nick']
                if winner == p1:
                    bracket_text += f"Матч {match['id']}: **{p1}** vs {p2} -> 👑 {winner}\n"
                else:
                    bracket_text += f"Матч {match['id']}: {p1} vs **{p2}** -> 👑 {winner}\n"
            elif match['winner_id'] == -1: # Both DQ'd
                 bracket_text += f"Матч {match['id']}: ~~{p1} vs {p2}~~ (Оба дисквалифицированы)\n"
            else:
                bracket_text += f"Матч {match['id']}: {p1} vs {p2} (В процессе)\n"

    await update.message.reply_text(bracket_text)

    cursor.close()
    conn.close()
