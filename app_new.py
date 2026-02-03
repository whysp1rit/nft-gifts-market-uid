#!/usr/bin/env python3
"""
Новый запуск бота с прямым токеном
"""

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# Прямое указание токена
TOKEN = "8512489092:AAFghx4VAurEYdi8gDZVUJ71pqGRnC8-n4M"

bot = Bot(token=TOKEN, parse_mode=types.ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    await message.answer(
        text="<b>🎁 Добро пожаловать в NFT Gifts Market!</b>\n\n"
             "Привет! 👋\n\n"
             "Бот успешно запущен с новым токеном!",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="🔐 Верификация аккаунта",
                        callback_data="verify"
                    )
                ]
            ]
        )
    )

@dp.callback_query_handler(text="verify")
async def verify_callback(call: types.CallbackQuery):
    await call.answer()
    await call.message.edit_text(
        text="<b>🔐 Верификация аккаунта</b>\n\n"
             "Система верификации готова!\n"
             "Все модули загружены и работают.",
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

@dp.callback_query_handler(text="main_menu")
async def main_menu_callback(call: types.CallbackQuery):
    await call.answer()
    await call.message.edit_text(
        text="<b>🎁 Добро пожаловать в NFT Gifts Market!</b>\n\n"
             "Привет! 👋\n\n"
             "Бот успешно запущен с новым токеном!",
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text="🔐 Верификация аккаунта",
                        callback_data="verify"
                    )
                ]
            ]
        )
    )

if __name__ == '__main__':
    print("🚀 Запускаем бота с новым токеном...")
    print(f"🤖 Токен: {TOKEN[:20]}...")
    executor.start_polling(dp, skip_updates=True)