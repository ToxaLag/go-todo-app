from telegram import Update
from telegram.ext import ContextTypes
from .admin_handlers import admin_required
from ..data.database import get_db_connection

@admin_required
async def add_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adds a new game to the database."""
    game_name = " ".join(context.args)
    if not game_name:
        await update.message.reply_text("Использование: /add_game <название_игры>")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO games (name) VALUES (?)", (game_name,))
        conn.commit()
        await update.message.reply_text(f"Игра '{game_name}' успешно добавлена.")
    except conn.IntegrityError:
        await update.message.reply_text(f"Игра с названием '{game_name}' уже существует.")
    finally:
        cursor.close()
        conn.close()

@admin_required
async def remove_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Removes a game and its characters from the database."""
    game_name = " ".join(context.args)
    if not game_name:
        await update.message.reply_text("Использование: /remove_game <название_игры>")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM games WHERE name = ?", (game_name,))
    conn.commit()

    if cursor.rowcount > 0:
        await update.message.reply_text(f"Игра '{game_name}' и все связанные с ней персонажи были удалены.")
    else:
        await update.message.reply_text(f"Игра '{game_name}' не найдена.")

    cursor.close()
    conn.close()

@admin_required
async def list_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists all available games."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM games ORDER BY name")
    games = cursor.fetchall()
    cursor.close()
    conn.close()

    if not games:
        await update.message.reply_text("В базе данных нет ни одной игры.")
        return

    game_list = "Доступные игры:\n" + "\n".join([f"- {game['name']}" for game in games])
    await update.message.reply_text(game_list)


@admin_required
async def set_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sets the active game for the tournament."""
    game_name = " ".join(context.args)
    if not game_name:
        await update.message.reply_text("Использование: /set_game <название_игры>")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM games WHERE name = ?", (game_name,))
    game = cursor.fetchone()

    if not game:
        await update.message.reply_text(f"Игра '{game_name}' не найдена. Сначала добавьте ее с помощью /add_game.")
        cursor.close()
        conn.close()
        return

    game_id = game['id']
    cursor.execute("UPDATE tournament_status SET active_game_id = ? WHERE id = 1", (game_id,))
    conn.commit()
    await update.message.reply_text(f"Активная игра для турнира установлена: '{game_name}'.")

    cursor.close()
    conn.close()

@admin_required
async def add_chars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Adds characters to a game."""
    args = " ".join(context.args).split(';')
    if len(args) != 2:
        await update.message.reply_text("Использование: /add_chars <название_игры>; <персонаж1>, <персонаж2>, ...")
        return

    game_name = args[0].strip()
    char_names_str = args[1]
    char_names = [name.strip() for name in char_names_str.split(',')]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM games WHERE name = ?", (game_name,))
    game = cursor.fetchone()

    if not game:
        await update.message.reply_text(f"Игра '{game_name}' не найдена.")
        cursor.close()
        conn.close()
        return

    game_id = game['id']
    added_count = 0
    failed_count = 0

    for char_name in char_names:
        if not char_name: continue
        try:
            cursor.execute("INSERT INTO characters (name, game_id) VALUES (?, ?)", (char_name, game_id))
            added_count += 1
        except conn.IntegrityError:
            failed_count += 1 # Character likely already exists for this game

    conn.commit()
    await update.message.reply_text(f"Результат для '{game_name}':\n- Добавлено: {added_count}\n- Не удалось (возможно, дубликаты): {failed_count}")

    cursor.close()
    conn.close()

@admin_required
async def remove_chars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Removes characters from a game."""
    args = " ".join(context.args).split(';')
    if len(args) != 2:
        await update.message.reply_text("Использование: /remove_chars <название_игры>; <персонаж1>, <персонаж2>, ...")
        return

    game_name = args[0].strip()
    char_names_str = args[1]
    char_names_to_remove = [name.strip() for name in char_names_str.split(',')]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM games WHERE name = ?", (game_name,))
    game = cursor.fetchone()

    if not game:
        await update.message.reply_text(f"Игра '{game_name}' не найдена.")
        cursor.close()
        conn.close()
        return

    game_id = game['id']
    deleted_count = 0

    for char_name in char_names_to_remove:
        if not char_name: continue
        cursor.execute("DELETE FROM characters WHERE name = ? AND game_id = ?", (char_name, game_id))
        if cursor.rowcount > 0:
            deleted_count += 1

    conn.commit()
    await update.message.reply_text(f"Результат для '{game_name}':\n- Удалено персонажей: {deleted_count}")

    cursor.close()
    conn.close()


@admin_required
async def list_chars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists all characters for a specific game."""
    game_name = " ".join(context.args)
    if not game_name:
        await update.message.reply_text("Использование: /list_chars <название_игры>")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT c.name FROM characters c JOIN games g ON c.game_id = g.id WHERE g.name = ? ORDER BY c.name",
        (game_name,)
    )
    chars = cursor.fetchall()
    cursor.close()
    conn.close()

    if not chars:
        await update.message.reply_text(f"Для игры '{game_name}' не найдено персонажей или сама игра не существует.")
        return

    char_list = f"Персонажи для '{game_name}':\n" + "\n".join([f"- {char['name']}" for char in chars])
    await update.message.reply_text(char_list)
