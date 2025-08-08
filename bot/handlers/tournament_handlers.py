import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..data.database import get_db_connection
from .admin_handlers import admin_required
from config import ADMIN_IDS

async def send_management_panel(context: ContextTypes.DEFAULT_TYPE, match: dict):
    """Sends a match management panel to all admins."""
    match_id = match['id']
    p1_id = match['p1_id']
    p1_nick = match['p1_nick']
    p2_id = match['p2_id']
    p2_nick = match['p2_nick']

    text = f"Управление матчем {match_id}: {p1_nick} vs {p2_nick}"

    keyboard = [
        [
            InlineKeyboardButton(f"👑 Победил {p1_nick}", callback_data=f"win_{match_id}_{p1_id}"),
            InlineKeyboardButton(f"👑 Победил {p2_nick}", callback_data=f"win_{match_id}_{p2_id}")
        ],
        [
            InlineKeyboardButton(f"❌ ДК {p1_nick}", callback_data=f"dq_{match_id}_{p1_id}"),
            InlineKeyboardButton(f"❌ ДК {p2_nick}", callback_data=f"dq_{match_id}_{p2_id}")
        ],
        [
            InlineKeyboardButton("❌ ДК Обоим", callback_data=f"dq_{match_id}_both")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=text, reply_markup=reply_markup)
        except Exception as e:
            print(f"Failed to send management panel to admin {admin_id} for match {match_id}: {e}")


async def notify_players_of_matches(context: ContextTypes.DEFAULT_TYPE, matches: list, round_num: int):
    """Sends notifications to players about their upcoming matches."""
    for match in matches:
        match_id = match['id']
        p1_nick = match['p1_nick']
        p2_nick = match['p2_nick']
        p1_tg_id = match['p1_tg_id']
        p2_tg_id = match['p2_tg_id']

        try:
            await context.bot.send_message(chat_id=p1_tg_id, text=f"🔔 Ваш следующий матч!\n\nРаунд {round_num}\nПротивник: {p2_nick}\nID матча: {match_id}")
            await context.bot.send_message(chat_id=p2_tg_id, text=f"🔔 Ваш следующий матч!\n\nРаунд {round_num}\nПротивник: {p1_nick}\nID матча: {match_id}")
        except Exception as e:
            print(f"Failed to send match notification for match {match_id}: {e}")

@admin_required
async def start_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the tournament and generates the first round."""
    conn = get_db_connection()
    if conn is None:
        await update.message.reply_text("Не удалось подключиться к базе данных.")
        return
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as match_count FROM matches")
    if cursor.fetchone()['match_count'] > 0:
        await update.message.reply_text("Турнир уже идет. Используйте /reset_tournament чтобы начать новый.")
        cursor.close()
        conn.close()
        return

    cursor.execute("SELECT id, nickname FROM registrations")
    registrations = cursor.fetchall()

    if len(registrations) < 2:
        await update.message.reply_text("Недостаточно игроков для начала турнира.")
        cursor.close()
        conn.close()
        return

    random.shuffle(registrations)

    bye_player = None
    if len(registrations) % 2 != 0:
        bye_player = registrations.pop()
        cursor.execute(
            "INSERT INTO matches (round, player1_id, is_bye, winner_id) VALUES (1, ?, 1, ?)",
            (bye_player['id'], bye_player['id'])
        )
        conn.commit()
        await update.message.reply_text(f"Игрок {bye_player['nickname']} пропускает первый раунд.")

    round_num = 1
    for i in range(0, len(registrations), 2):
        player1 = registrations[i]
        player2 = registrations[i+1]
        cursor.execute(
            "INSERT INTO matches (round, player1_id, player2_id) VALUES (?, ?, ?)",
            (round_num, player1['id'], player2['id'])
        )
        conn.commit()

    await update.message.reply_text("Сгенерированы матчи первого раунда.")

    cursor.execute(
        "SELECT m.id, "
        "p1.id as p1_id, p1.nickname as p1_nick, u1.telegram_id as p1_tg_id, "
        "p2.id as p2_id, p2.nickname as p2_nick, u2.telegram_id as p2_tg_id "
        "FROM matches m "
        "JOIN registrations p1 ON m.player1_id = p1.id "
        "JOIN users u1 ON p1.user_id = u1.id "
        "LEFT JOIN registrations p2 ON m.player2_id = p2.id "
        "LEFT JOIN users u2 ON p2.user_id = u2.id "
        "WHERE m.round = 1 AND m.is_bye = 0"
    )
    matches = cursor.fetchall()

    match_list_text = [f"Матч {m['id']}: {m['p1_nick']} vs {m['p2_nick']}" for m in matches]
    await update.message.reply_text(f"Матчи 1 раунда:\n" + "\n".join(match_list_text))

    await notify_players_of_matches(context, matches, 1)
    for match in matches:
        await send_management_panel(context, match)

    cursor.close()
    conn.close()

async def match_management_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles button presses for match management (win/dq)."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split('_')
    action = parts[0]
    match_id = int(parts[1])

    conn = get_db_connection()
    if conn is None:
        await query.edit_message_text("Не удалось подключиться к базе данных.")
        return
    cursor = conn.cursor()

    cursor.execute("SELECT round, player1_id, player2_id FROM matches WHERE id = ?", (match_id,))
    match = cursor.fetchone()
    if not match:
        await query.edit_message_text("Матч не найден.")
        cursor.close()
        conn.close()
        return

    current_round = match['round']
    p1_id = match['player1_id']
    p2_id = match['player2_id']

    message_text = ""

    if action == 'win':
        winner_id = int(parts[2])
        cursor.execute("UPDATE matches SET winner_id = ? WHERE id = ?", (winner_id, match_id))
        conn.commit()
        cursor.execute("SELECT nickname FROM registrations WHERE id = ?", (winner_id,))
        winner_nick = cursor.fetchone()['nickname']
        message_text = f"✅ Матч {match_id}: {winner_nick} - победитель."
    elif action == 'dq':
        player_to_dq = parts[2]
        if player_to_dq == 'both':
            cursor.execute("UPDATE matches SET winner_id = -1 WHERE id = ?", (match_id,))
            message_text = f"✅ Матч {match_id}: Оба игрока дисквалифицированы."
        else:
            dq_player_id = int(player_to_dq)
            winner_id = p2_id if dq_player_id == p1_id else p1_id
            cursor.execute("UPDATE matches SET winner_id = ? WHERE id = ?", (winner_id, match_id))
            cursor.execute("SELECT nickname FROM registrations WHERE id = ?", (winner_id,))
            winner_nick = cursor.fetchone()['nickname']
            message_text = f"✅ Матч {match_id}: Игрок дисквалифицирован. {winner_nick} - победитель."
        conn.commit()

    await query.edit_message_text(message_text, reply_markup=None)

    cursor.execute(
        "SELECT COUNT(*) as remaining_matches FROM matches WHERE round = ? AND winner_id IS NULL",
        (current_round,)
    )
    if cursor.fetchone()['remaining_matches'] == 0:
        await query.message.reply_text(f"Раунд {current_round} завершен. Генерируется следующий раунд...")
        await generate_next_round(query.message, context, current_round + 1)

    cursor.close()
    conn.close()


async def generate_next_round(message, context: ContextTypes.DEFAULT_TYPE, next_round_num: int):
    """Generates the matches for the next round."""
    conn = get_db_connection()
    if conn is None:
        await message.reply_text("Не удалось подключиться к базе данных при генерации следующего раунда.")
        return
    cursor = conn.cursor()

    cursor.execute(
        "SELECT w.id, w.nickname FROM registrations w JOIN matches m ON w.id = m.winner_id WHERE m.round = ? AND m.winner_id != -1",
        (next_round_num - 1,)
    )
    winners = cursor.fetchall()

    if len(winners) == 1:
        await message.reply_text(f"Турнир окончен! Победитель: {winners[0]['nickname']}!")
        cursor.close()
        conn.close()
        return

    if not winners:
        await message.reply_text("Нет победителей для генерации следующего раунда. Турнир мог закончиться вничью.")
        cursor.close()
        conn.close()
        return

    random.shuffle(winners)

    bye_player = None
    if len(winners) % 2 != 0:
        bye_player = winners.pop()
        cursor.execute(
            "INSERT INTO matches (round, player1_id, is_bye, winner_id) VALUES (?, ?, 1, ?)",
            (next_round_num, bye_player['id'], bye_player['id'])
        )
        conn.commit()
        await message.reply_text(f"Игрок {bye_player['nickname']} пропускает раунд {next_round_num}.")

    for i in range(0, len(winners), 2):
        player1 = winners[i]
        player2 = winners[i+1]
        cursor.execute(
            "INSERT INTO matches (round, player1_id, player2_id) VALUES (?, ?, ?)",
            (next_round_num, player1['id'], player2['id'])
        )
        conn.commit()

    cursor.execute(
        "SELECT m.id, "
        "p1.id as p1_id, p1.nickname as p1_nick, u1.telegram_id as p1_tg_id, "
        "p2.id as p2_id, p2.nickname as p2_nick, u2.telegram_id as p2_tg_id "
        "FROM matches m "
        "JOIN registrations p1 ON m.player1_id = p1.id "
        "JOIN users u1 ON p1.user_id = u1.id "
        "LEFT JOIN registrations p2 ON m.player2_id = p2.id "
        "LEFT JOIN users u2 ON p2.user_id = u2.id "
        "WHERE m.round = ? AND m.is_bye = 0",
        (next_round_num,)
    )
    matches = cursor.fetchall()

    match_list_text = [f"Матч {m['id']}: {m['p1_nick']} vs {m['p2_nick']}" for m in matches]
    await message.reply_text(f"Матчи раунда {next_round_num}:\n" + "\n".join(match_list_text))

    await notify_players_of_matches(context, matches, next_round_num)
    for match in matches:
        await send_management_panel(context, match)

    cursor.close()
    conn.close()

@admin_required
async def reset_tournament(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resets the entire tournament."""
    conn = get_db_connection()
    if conn is None:
        await update.message.reply_text("Не удалось подключиться к базе данных.")
        return
    cursor = conn.cursor()

    cursor.execute("DELETE FROM matches")
    cursor.execute("DELETE FROM registrations")
    cursor.execute("DELETE FROM characters")
    cursor.execute("DELETE FROM games")
    # Reset autoincrement counters
    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('matches', 'registrations', 'characters', 'games')")
    cursor.execute("UPDATE tournament_status SET registration_open = 0, mode = 'nickname', active_game_id = NULL WHERE id = 1")

    conn.commit()
    cursor.close()
    conn.close()

    await update.message.reply_text("Турнир был сброшен. Все регистрации и матчи были удалены.")
