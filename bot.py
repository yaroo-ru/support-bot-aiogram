import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio

API_TOKEN = ''
ADMIN_ID = 1

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

welcome_message = "Привет! Это бот поддержки. Напиши мне, если у тебя есть вопросы."

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎲 Бросить кубик")]
    ],
    resize_keyboard=True
)

class WelcomeMessageState(StatesGroup):
    waiting_for_message = State()

class PostState(StatesGroup):
    waiting_for_post = State()

def init_db():
    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY,
                        full_name TEXT
                    )''')
    conn.commit()
    conn.close()

def add_user(user_id, full_name):
    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (id, full_name) VALUES (?, ?)', (user_id, full_name))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users')
    users = cursor.fetchall()
    conn.close()
    return users

def get_user_count():
    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    conn.close()
    return count

@dp.message(CommandStart())
async def send_welcome(message: Message):
    add_user(message.from_user.id, message.from_user.full_name)
    await message.answer(welcome_message, reply_markup=keyboard)

@dp.message(Command(commands=['setwelcome']))
async def set_welcome_message(message: Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Пожалуйста, напишите новое приветственное сообщение.")
        await state.set_state(WelcomeMessageState.waiting_for_message)
    else:
        await message.answer("У вас нет прав для изменения приветственного сообщения.")

@dp.message(WelcomeMessageState.waiting_for_message)
async def process_new_welcome_message(message: Message, state: FSMContext):
    global welcome_message
    if message.from_user.id == ADMIN_ID:
        welcome_message = message.text
        await message.answer("Приветственное сообщение обновлено.")
        await state.clear()
    else:
        await message.answer("У вас нет прав для изменения приветственного сообщения.")

@dp.message(lambda message: message.text == "🎲 Бросить кубик")
async def roll_dice(message: Message):
    await message.answer_dice(emoji="🎲")

@dp.message(Command(commands=['post']))
async def post_message(message: Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Введите сообщение или отправьте медиа для рассылки.")
        await state.set_state(PostState.waiting_for_post)
    else:
        await message.answer("У вас нет прав для рассылки сообщений.")

@dp.message(PostState.waiting_for_post)
async def process_post_message(message: Message, state: FSMContext):
    if message.from_user.id == ADMIN_ID:
        users = get_all_users()

        if message.text:
            for user in users:
                try:
                    await bot.send_message(user[0], message.text)
                except Exception as e:
                    print(f"Не удалось отправить сообщение пользователю {user[0]}: {e}")
        elif message.photo:
            photo = message.photo[-1].file_id
            caption = message.caption or ""
            for user in users:
                try:
                    await bot.send_photo(user[0], photo, caption=caption)
                except Exception as e:
                    print(f"Не удалось отправить фото пользователю {user[0]}: {e}")

        await message.answer(f"Сообщение успешно отправлено {len(users)} пользователям.")
        await state.clear()

@dp.message()
async def forward_to_admin(message: Message):
    user_link = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.full_name}</a>'
    admin_message = f"Новое сообщение от {user_link}:\n{message.text}"
    await bot.send_message(ADMIN_ID, admin_message, parse_mode="HTML")
    await message.answer("Ваше сообщение отправлено поддержке.", reply_markup=keyboard)

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())