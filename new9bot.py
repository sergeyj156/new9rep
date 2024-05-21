import logging
import sqlite3
import pandas as pd
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Создаем подключение к базе данных
conn = sqlite3.connect('users.db', check_same_thread=False)
c = conn.cursor()

def create_tables():
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        username TEXT,
        post_count INTEGER DEFAULT 0
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS user_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        text TEXT
    )
    ''')
    conn.commit()
    logging.info("Таблицы users и user_posts успешно созданы или уже существуют.")

create_tables()

def update_user_data(user_id, first_name, last_name, username):
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    if c.fetchone():
        c.execute('UPDATE users SET first_name = ?, last_name = ?, username = ? WHERE user_id = ?',
                  (first_name, last_name, username, user_id))
    else:
        c.execute('INSERT INTO users (user_id, first_name, last_name, username, post_count) VALUES (?, ?, ?, ?, 0)',
                  (user_id, first_name, last_name, username))
    conn.commit()

def increment_post_count(user_id):
    c.execute('UPDATE users SET post_count = post_count + 1 WHERE user_id = ?', (user_id,))
    conn.commit()

def export_data_to_excel():
    df = pd.read_sql_query("SELECT * FROM users", conn)
    df.to_excel('user_data.xlsx', index=False)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    update_user_data(user.id, user.first_name, user.last_name, user.username)

    keyboard = [
        [InlineKeyboardButton("Правила", callback_data='rules')],
        [InlineKeyboardButton("Призы", callback_data='prizes')],
        [InlineKeyboardButton("Зарегистрировать пост", callback_data='send_post')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f'Привет! 👋\n\nЭто бот поможет тебе зарегистрировать свои посты, чтобы принять участие в конкурсе!\n\nДля начала, проверь, чтобы по нику тебя мог найти любой пользователь, а также правильность его написания ❗️\n\nВ случае, если мы с тобой не сможем связаться, будем перевыбирать победителя!\n\nПобедителей определим 14 июня. Будем вручную выбирать самые креативные, необычные и просто те работы, над которыми постарались!\n\nЧтобы зарегистрировать свой пост, жми на кнопку ниже ⤵️',
        reply_markup=reply_markup
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'rules':
        # Удаляем предыдущие сообщения с фотографиями
        if 'photo_messages' in context.user_data:
            for msg_id in context.user_data['photo_messages']:
                try:
                    await context.bot.delete_message(chat_id=query.message.chat_id, message_id=msg_id)
                except Exception as e:
                    logging.error(f"Ошибка при удалении сообщения {msg_id}: {e}")

        # Сообщение с правилами и кнопка возврата в меню
        rules_text = (
            "Супер! Напоминаем про правила и призы 🔥\n\n"
            "Итак, чтобы стать участником конкурса, тебе нужно:\n"
            "1. Купить топовый мерч от «100балльного», если ты ещё этого не сделал. Для этого залетай по ссылке: https://100pointsmerch.ru/\n"
            "2. Сделать фото, снять видео себя в мерче (любой формат и креатив приветствуются 😉) и выложить в ЛЮБУЮ соцсеть! Это могут быть:\n"
            "— сторис;\n"
            "— посты;\n"
            "— короткие и длинные ролики;\n"
            "— статьи с фотками и видео.\n"
            "Количество публикаций не ограничено!\n"
            "3. Вставить в публикацию хэштег #100балльныйРепетитор и/или отметку нашего аккаунта ❗️\n"
            "4. Отправить свою публикацию в этого бота (скриншот + ссылка). Внимание: на скриншоте должен быть виден хэштег и / или отметка нашего аккаунта!"
        )

        await query.edit_message_text(
            text=rules_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data='back_to_menu')]])
        )

        # Отправка 8 фотографий
        photos = [
            'fotomerch/1.jpeg',
            'fotomerch/2.jpeg',
            'fotomerch/3.jpeg',
            'fotomerch/4.jpeg',
            'fotomerch/5.jpeg',
            'fotomerch/6.jpeg',
            'fotomerch/7.jpeg',
            'fotomerch/8.jpeg'
        ]

        context.user_data['photo_messages'] = []
        for photo in photos:
            try:
                msg = await context.bot.send_photo(chat_id=query.message.chat_id, photo=open(photo, 'rb'))
                context.user_data['photo_messages'].append(msg.message_id)
                await asyncio.sleep(2)  # Добавляем задержку в 2 секунды между отправкой фотографий
            except Exception as e:
                logging.error(f"Ошибка при отправке фото {photo}: {e}")

    elif query.data == 'prizes':
        # Сообщение с информацией о призах и кнопка возврата в меню
        await query.edit_message_text(
            text="Что ты сможешь выиграть?\n"
                 "— Сертификат на Ozon на 3000 рублей (5 победителей).\n"
                 "— Калькулятор casio (5 победителей).\n"
                 "— Сертификат в Буквоед на 1000 рублей (7 победителей).\n"
                 "— Подписка Wink+more.tv на 6 месяцев (10 победителей).",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data='back_to_menu')]])
        )
    elif query.data == 'send_post':
        context.user_data['awaiting_post'] = True
        await query.edit_message_text(
            text="Отправь пост, сторис или видео из любой соцсети в формате: скрин + ссылка.\n\n"
                 "❗️ Внимание: на скриншоте должен быть виден хэштег #100балльныйРепетитор и / или отметка нашего аккаунта."
        )
    elif query.data == 'back_to_menu':
        # Удаляем предыдущие сообщения с фотографиями
        if 'photo_messages' in context.user_data:
            for msg_id in context.user_data['photo_messages']:
                try:
                    await context.bot.delete_message(chat_id=query.message.chat_id, message_id=msg_id)
                except Exception as e:
                    logging.error(f"Ошибка при удалении сообщения {msg_id}: {e}")

        keyboard = [
            [InlineKeyboardButton("Правила", callback_data='rules')],
            [InlineKeyboardButton("Призы", callback_data='prizes')],
            [InlineKeyboardButton("Отправить пост", callback_data='send_post')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="Привет! 👋\n\nЭто бот поможет тебе зарегистрировать свои посты, чтобы принять участие в конкурсе!",
            reply_markup=reply_markup
        )

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    message = update.message
    user = message.from_user

    if user_data.get('awaiting_post'):
        if message.photo:
            photo = message.photo[-1]  # Берем последнее фото (наибольшее)
            caption = message.caption
        elif message.document:
            photo = message.document
            caption = message.caption
        else:
            await update.message.reply_text("Пожалуйста, отправьте фото или документ.")
            return

        info = f'Пост от пользователя @{user.username} (ID: {user.id})\нСсылка: {caption if caption else "Без ссылки"}'
        for admin_id in [679030634, 1223531770]:
            if message.photo:
                await context.bot.send_photo(chat_id=admin_id, photo=photo.file_id, caption=info)
            else:
                await context.bot.send_document(chat_id=admin_id, document=photo.file_id, caption=info)

        keyboard = [
            [InlineKeyboardButton("Назад", callback_data='back_to_menu')],
            [InlineKeyboardButton("Отправить еще один пост", callback_data='send_post')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Супер! Твой пост принят 😎\n\nНапоминаем, что количество публикаций не ограничено!\n\nЧтобы добавить ещё один пост, жми на кнопку ниже ⤵️",
            reply_markup=reply_markup
        )

        increment_post_count(user.id)
        user_data['awaiting_post'] = False

        # Запись текста в таблицу user_posts
        c.execute('INSERT INTO user_posts (username, text) VALUES (?, ?)', (user.username, caption))
        conn.commit()
    else:
        if message and not message.text.startswith('/'):
            await message.reply_text("Пожалуйста, используйте кнопки для навигации.")

async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id in [679030634, 1223531770]:
        export_data_to_excel()
        with open('user_data.xlsx', 'rb') as file:
            await context.bot.send_document(chat_id=user_id, document=file)
        await update.message.reply_text("Данные успешно экспортированы и отправлены вам.")
    else:
        await update.message.reply_text("У вас нет прав для выполнения этой команды.")

async def export_posts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id in [679030634, 1223531770]:
        # Экспорт данных из таблицы user_posts в Excel
        df = pd.read_sql_query("SELECT * FROM user_posts", conn)
        df.to_excel('user_posts.xlsx', index=False)
        with open('user_posts.xlsx', 'rb') as file:
            await context.bot.send_document(chat_id=user_id, document=file)
        await update.message.reply_text("Данные постов успешно экспортированы и отправлены вам.")
    else:
        await update.message.reply_text("У вас нет прав для выполнения этой команды.")

def main():
    TOKEN = '6708762418:AAFEgHko1kjBUrbO77Xd_nUjVC9SuTi1x6A'  # Поменяйте на ваш токен
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("export", export_command))
    application.add_handler(CommandHandler("export_posts", export_posts_command))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler((filters.PHOTO | filters.TEXT), handle_media))

    application.run_polling()

if __name__ == '__main__':
    main()
