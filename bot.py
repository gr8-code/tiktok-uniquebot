import asyncio
import logging
import os
import random
from datetime import datetime
from io import BytesIO

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, 
    CallbackQuery, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    BufferedInputFile,
    FSInputFile
)

from uniqualizer import PhotoUniqulizer
from config import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

router = Router()

class UniqueStates(StatesGroup):
    choosing_mode = State()
    waiting_for_photo = State()
    setting_params = State()
    processing = State()

uniqualizer = PhotoUniqulizer()
user_data = {}

def get_user_default_params():
    """Дефолтные параметры"""
    return {
        'noise': False,
        'stripes': False,
        'smiles': False,
        'background': False,
        'blur_radius': 0,
        'count': 1,
        'mode': 'manual'  # manual или auto
    }

def get_auto_params():
    """Генерирует случайные параметры для авто-режима"""
    return {
        'noise': random.choice([True, False]),
        'stripes': random.choice([True, False]),
        'smiles': random.choice([True, True, False]),  # Чаще True
        'background': random.choice([True, False]),
        'blur_radius': random.randint(0, 5),
        'count': random.randint(3, 10)
    }

def get_mode_keyboard():
    """Клавиатура выбора режима"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="🎲 АВТО (рандом параметры)",
                callback_data="mode_auto"
            )
        ],
        [
            InlineKeyboardButton(
                text="⚙️ РУЧНОЙ (настроить самому)",
                callback_data="mode_manual"
            )
        ],
        [
            InlineKeyboardButton(
                text="❓ Что это?",
                callback_data="mode_help"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_auto_settings_keyboard():
    """Клавиатура для авто-режима"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="🎲 Сгенерировать параметры",
                callback_data="auto_generate"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔢 Выбрать количество",
                callback_data="auto_set_count"
            )
        ],
        [
            InlineKeyboardButton(
                text="✅ Готово! Отправь фото",
                callback_data="auto_ready"
            )
        ],
        [
            InlineKeyboardButton(
                text="◀️ Назад к выбору режима",
                callback_data="back_to_mode"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_params_keyboard(user_id: int):
    """Генерирует клавиатуру с параметрами для ручного режима"""
    params = user_data.get(user_id, get_user_default_params())
    
    keyboard = [
        [
            InlineKeyboardButton(
                text=f"🔊 Шумы: {'✅' if params['noise'] else '❌'}",
                callback_data="toggle_noise"
            ),
            InlineKeyboardButton(
                text=f"📊 Полосы: {'✅' if params['stripes'] else '❌'}",
                callback_data="toggle_stripes"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"😀 Эмодзи: {'✅' if params['smiles'] else '❌'}",
                callback_data="toggle_smiles"
            ),
            InlineKeyboardButton(
                text=f"🎨 Фон: {'✅' if params['background'] else '❌'}",
                callback_data="toggle_background"
            )
        ],
        [
            InlineKeyboardButton(
                text=f"🌫 Размытие: {params['blur_radius']}",
                callback_data="set_blur"
            ),
            InlineKeyboardButton(
                text=f"🔢 Количество: {params['count']}",
                callback_data="set_count"
            )
        ],
        [
            InlineKeyboardButton(
                text="✅ Готово! Отправь фото",
                callback_data="params_ready"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔄 Сбросить всё",
                callback_data="reset_params"
            ),
            InlineKeyboardButton(
                text="◀️ К выбору режима",
                callback_data="back_to_mode"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_blur_keyboard():
    """Клавиатура для выбора размытия"""
    keyboard = [
        [
            InlineKeyboardButton(text="0", callback_data="blur_0"),
            InlineKeyboardButton(text="1", callback_data="blur_1"),
            InlineKeyboardButton(text="2", callback_data="blur_2"),
            InlineKeyboardButton(text="3", callback_data="blur_3"),
        ],
        [
            InlineKeyboardButton(text="4", callback_data="blur_4"),
            InlineKeyboardButton(text="5", callback_data="blur_5"),
            InlineKeyboardButton(text="6", callback_data="blur_6"),
            InlineKeyboardButton(text="7", callback_data="blur_7"),
        ],
        [
            InlineKeyboardButton(text="8", callback_data="blur_8"),
            InlineKeyboardButton(text="9", callback_data="blur_9"),
            InlineKeyboardButton(text="10", callback_data="blur_10"),
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_params")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_count_keyboard():
    """Клавиатура для выбора количества"""
    keyboard = [
        [
            InlineKeyboardButton(text="1", callback_data="count_1"),
            InlineKeyboardButton(text="2", callback_data="count_2"),
            InlineKeyboardButton(text="3", callback_data="count_3"),
            InlineKeyboardButton(text="4", callback_data="count_4"),
            InlineKeyboardButton(text="5", callback_data="count_5"),
        ],
        [
            InlineKeyboardButton(text="10", callback_data="count_10"),
            InlineKeyboardButton(text="15", callback_data="count_15"),
            InlineKeyboardButton(text="20", callback_data="count_20"),
            InlineKeyboardButton(text="25", callback_data="count_25"),
            InlineKeyboardButton(text="30", callback_data="count_30"),
        ],
        [
            InlineKeyboardButton(text="40", callback_data="count_40"),
            InlineKeyboardButton(text="50", callback_data="count_50"),
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_params")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_auto_count_keyboard():
    """Клавиатура количества для авто-режима"""
    keyboard = [
        [
            InlineKeyboardButton(text="1", callback_data="auto_count_1"),
            InlineKeyboardButton(text="3", callback_data="auto_count_3"),
            InlineKeyboardButton(text="5", callback_data="auto_count_5"),
        ],
        [
            InlineKeyboardButton(text="10", callback_data="auto_count_10"),
            InlineKeyboardButton(text="15", callback_data="auto_count_15"),
            InlineKeyboardButton(text="20", callback_data="auto_count_20"),
        ],
        [
            InlineKeyboardButton(text="30", callback_data="auto_count_30"),
            InlineKeyboardButton(text="50", callback_data="auto_count_50"),
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_auto")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    if user_id not in user_data:
        user_data[user_id] = get_user_default_params()
    
    await message.answer(
        f"🔥 <b>Привет, {message.from_user.first_name}!</b>\n\n"
        f"Я бот для уникализации фото 📸\n\n"
        f"<b>Что я умею:</b>\n"
        f"• Добавлять шумы 🔊\n"
        f"• Рисовать полосы 📊\n"
        f"• Накладывать эмодзи 😀\n"
        f"• Менять фон 🎨\n"
        f"• Применять размытие 🌫\n\n"
        f"<b>🎲 АВТО режим</b> - бот сам выбирает параметры\n"
        f"<b>⚙️ РУЧНОЙ режим</b> - настраиваешь сам\n\n"
        f"<b>Команды:</b>\n"
        f"/unique - Уникализировать фото\n"
        f"/help - Помощь\n\n"
        f"Используй /unique чтобы начать! 🚀",
        parse_mode="HTML"
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Помощь"""
    await message.answer(
        "<b>📖 Инструкция:</b>\n\n"
        "1️⃣ Используй /unique\n"
        "2️⃣ Выбери режим:\n"
        "   • 🎲 АВТО - бот сам генерирует параметры\n"
        "   • ⚙️ РУЧНОЙ - настраиваешь всё сам\n"
        "3️⃣ Отправь фото\n"
        "4️⃣ Получи уникализированные версии!\n\n"
        "<b>🎲 Авто-режим:</b>\n"
        "Бот случайно выбирает какие эффекты применить.\n"
        "Каждое фото будет уникальным!\n\n"
        "<b>⚙️ Ручной режим:</b>\n"
        "Сам выбираешь какие параметры использовать.\n"
        "Больше контроля над результатом!\n\n"
        "<b>💡 Совет:</b> Используй АВТО для быстрого результата,\n"
        "РУЧНОЙ - если нужен конкретный эффект!\n\n"
        f"<b>⚠️ Ограничения:</b>\n"
        f"• Максимум {config.MAX_UNIQUALIZATIONS} уникализаций\n"
        f"• Размер файла до {config.MAX_FILE_SIZE // 1024 // 1024}MB",
        parse_mode="HTML"
    )

@router.message(Command("unique"))
async def cmd_unique(message: Message, state: FSMContext):
    """Начало уникализации"""
    user_id = message.from_user.id
    
    if user_id not in user_data:
        user_data[user_id] = get_user_default_params()
    
    await state.set_state(UniqueStates.choosing_mode)
    
    await message.answer(
        "🎯 <b>Выбери режим работы:</b>\n\n"
        "🎲 <b>АВТО</b> - бот сам рандомно выберет параметры\n"
        "   (быстро и просто!)\n\n"
        "⚙️ <b>РУЧНОЙ</b> - настрой всё под себя\n"
        "   (полный контроль!)\n\n"
        "Какой выбираешь?",
        reply_markup=get_mode_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "mode_help")
async def mode_help(callback: CallbackQuery):
    """Помощь по режимам"""
    await callback.answer(
        "🎲 АВТО: бот генерирует случайные параметры для каждого фото\n"
        "⚙️ РУЧНОЙ: сам настраиваешь все эффекты",
        show_alert=True
    )

@router.callback_query(F.data == "mode_auto")
async def mode_auto(callback: CallbackQuery, state: FSMContext):
    """Выбран авто-режим"""
    user_id = callback.from_user.id
    user_data[user_id]['mode'] = 'auto'
    
    # Генерируем начальные параметры
    auto_params = get_auto_params()
    user_data[user_id].update(auto_params)
    
    await state.set_state(UniqueStates.setting_params)
    
    params_text = "🎲 <b>АВТО РЕЖИМ</b>\n\n"
    params_text += "Сгенерированные параметры:\n\n"
    params_text += f"🔊 Шумы: {'✅' if auto_params['noise'] else '❌'}\n"
    params_text += f"📊 Полосы: {'✅' if auto_params['stripes'] else '❌'}\n"
    params_text += f"😀 Эмодзи: {'✅' if auto_params['smiles'] else '❌'}\n"
    params_text += f"🎨 Фон: {'✅' if auto_params['background'] else '❌'}\n"
    params_text += f"🌫 Размытие: {auto_params['blur_radius']}\n"
    params_text += f"🔢 Количество: {auto_params['count']}\n\n"
    params_text += "Можешь сгенерировать заново или отправить фото!"
    
    await callback.message.edit_text(
        params_text,
        reply_markup=get_auto_settings_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "auto_generate")
async def auto_generate(callback: CallbackQuery):
    """Перегенерация параметров в авто-режиме"""
    user_id = callback.from_user.id
    
    auto_params = get_auto_params()
    user_data[user_id].update(auto_params)
    
    params_text = "🎲 <b>АВТО РЕЖИМ</b>\n\n"
    params_text += "Новые параметры сгенерированы! 🎰\n\n"
    params_text += f"🔊 Шумы: {'✅' if auto_params['noise'] else '❌'}\n"
    params_text += f"📊 Полосы: {'✅' if auto_params['stripes'] else '❌'}\n"
    params_text += f"😀 Эмодзи: {'✅' if auto_params['smiles'] else '❌'}\n"
    params_text += f"🎨 Фон: {'✅' if auto_params['background'] else '❌'}\n"
    params_text += f"🌫 Размытие: {auto_params['blur_radius']}\n"
    params_text += f"🔢 Количество: {auto_params['count']}\n\n"
    params_text += "Можешь сгенерировать ещё раз или отправить фото!"
    
    await callback.message.edit_text(
        params_text,
        reply_markup=get_auto_settings_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer("🎲 Параметры обновлены!")

@router.callback_query(F.data == "auto_set_count")
async def auto_set_count(callback: CallbackQuery):
    """Выбор количества в авто-режиме"""
    await callback.message.edit_text(
        "🔢 <b>Выбери количество уникализаций:</b>",
        reply_markup=get_auto_count_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("auto_count_"))
async def auto_count_selected(callback: CallbackQuery):
    """Количество выбрано в авто-режиме"""
    user_id = callback.from_user.id
    count_value = int(callback.data.split("_")[2])
    
    user_data[user_id]['count'] = count_value
    
    params = user_data[user_id]
    params_text = "🎲 <b>АВТО РЕЖИМ</b>\n\n"
    params_text += f"🔊 Шумы: {'✅' if params['noise'] else '❌'}\n"
    params_text += f"📊 Полосы: {'✅' if params['stripes'] else '❌'}\n"
    params_text += f"😀 Эмодзи: {'✅' if params['smiles'] else '❌'}\n"
    params_text += f"🎨 Фон: {'✅' if params['background'] else '❌'}\n"
    params_text += f"🌫 Размытие: {params['blur_radius']}\n"
    params_text += f"🔢 Количество: {params['count']}\n\n"
    params_text += "Можешь сгенерировать заново или отправить фото!"
    
    await callback.message.edit_text(
        params_text,
        reply_markup=get_auto_settings_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer(f"🔢 Установлено: {count_value}")

@router.callback_query(F.data == "back_to_auto")
async def back_to_auto(callback: CallbackQuery):
    """Возврат к авто-настройкам"""
    user_id = callback.from_user.id
    params = user_data[user_id]
    
    params_text = "🎲 <b>АВТО РЕЖИМ</b>\n\n"
    params_text += f"🔊 Шумы: {'✅' if params['noise'] else '❌'}\n"
    params_text += f"📊 Полосы: {'✅' if params['stripes'] else '❌'}\n"
    params_text += f"😀 Эмодзи: {'✅' if params['smiles'] else '❌'}\n"
    params_text += f"🎨 Фон: {'✅' if params['background'] else '❌'}\n"
    params_text += f"🌫 Размытие: {params['blur_radius']}\n"
    params_text += f"🔢 Количество: {params['count']}\n\n"
    
    await callback.message.edit_text(
        params_text,
        reply_markup=get_auto_settings_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "auto_ready")
async def auto_ready(callback: CallbackQuery, state: FSMContext):
    """Авто-режим готов, ждём фото"""
    await state.set_state(UniqueStates.waiting_for_photo)
    
    user_id = callback.from_user.id
    params = user_data[user_id]
    
    params_text = "🎲 <b>АВТО РЕЖИМ АКТИВИРОВАН!</b>\n\n"
    params_text += "Текущие параметры:\n"
    params_text += f"🔊 Шумы: {'✅' if params['noise'] else '❌'}\n"
    params_text += f"📊 Полосы: {'✅' if params['stripes'] else '❌'}\n"
    params_text += f"😀 Эмодзи: {'✅' if params['smiles'] else '❌'}\n"
    params_text += f"🎨 Фон: {'✅' if params['background'] else '❌'}\n"
    params_text += f"🌫 Размытие: {params['blur_radius']}\n"
    params_text += f"🔢 Количество: {params['count']}\n\n"
    params_text += "📸 <b>Отправь фото!</b>"
    
    await callback.message.edit_text(params_text, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "mode_manual")
async def mode_manual(callback: CallbackQuery, state: FSMContext):
    """Выбран ручной режим"""
    user_id = callback.from_user.id
    user_data[user_id]['mode'] = 'manual'
    
    await state.set_state(UniqueStates.setting_params)
    
    await callback.message.edit_text(
        "⚙️ <b>РУЧНОЙ РЕЖИМ</b>\n\n"
        "Настрой параметры кнопками ниже 👇",
        reply_markup=get_params_keyboard(user_id),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_mode")
async def back_to_mode(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору режима"""
    await state.set_state(UniqueStates.choosing_mode)
    
    await callback.message.edit_text(
        "🎯 <b>Выбери режим работы:</b>\n\n"
        "🎲 <b>АВТО</b> - бот сам рандомно выберет параметры\n"
        "⚙️ <b>РУЧНОЙ</b> - настрой всё под себя\n\n"
        "Какой выбираешь?",
        reply_markup=get_mode_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

# Все остальные хэндлеры для ручного режима (toggle_noise, toggle_stripes и тд)
# Оставляю как в предыдущей версии...

@router.callback_query(F.data == "toggle_noise")
async def toggle_noise(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data[user_id]['noise'] = not user_data[user_id]['noise']
    await callback.message.edit_reply_markup(reply_markup=get_params_keyboard(user_id))
    await callback.answer("🔊 Шумы переключены!")

@router.callback_query(F.data == "toggle_stripes")
async def toggle_stripes(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data[user_id]['stripes'] = not user_data[user_id]['stripes']
    await callback.message.edit_reply_markup(reply_markup=get_params_keyboard(user_id))
    await callback.answer("📊 Полосы переключены!")

@router.callback_query(F.data == "toggle_smiles")
async def toggle_smiles(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data[user_id]['smiles'] = not user_data[user_id]['smiles']
    await callback.message.edit_reply_markup(reply_markup=get_params_keyboard(user_id))
    await callback.answer("😀 Эмодзи переключены!")

@router.callback_query(F.data == "toggle_background")
async def toggle_background(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data[user_id]['background'] = not user_data[user_id]['background']
    await callback.message.edit_reply_markup(reply_markup=get_params_keyboard(user_id))
    await callback.answer("🎨 Фон переключен!")

@router.callback_query(F.data == "set_blur")
async def set_blur(callback: CallbackQuery):
    await callback.message.edit_text(
        "🌫 <b>Выбери силу размытия (0-10):</b>",
        reply_markup=get_blur_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("blur_"))
async def blur_selected(callback: CallbackQuery):
    user_id = callback.from_user.id
    blur_value = int(callback.data.split("_")[1])
    user_data[user_id]['blur_radius'] = blur_value
    
    await callback.message.edit_text(
        "⚙️ <b>РУЧНОЙ РЕЖИМ</b>\n\nНастрой параметры кнопками ниже 👇",
        reply_markup=get_params_keyboard(user_id),
        parse_mode="HTML"
    )
    await callback.answer(f"🌫 Размытие: {blur_value}")

@router.callback_query(F.data == "set_count")
async def set_count(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔢 <b>Выбери количество:</b>",
        reply_markup=get_count_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("count_"))
async def count_selected(callback: CallbackQuery):
    user_id = callback.from_user.id
    count_value = int(callback.data.split("_")[1])
    
    if count_value > config.MAX_UNIQUALIZATIONS:
        await callback.answer(f"❌ Максимум {config.MAX_UNIQUALIZATIONS}!", show_alert=True)
        return
    
    user_data[user_id]['count'] = count_value
    
    await callback.message.edit_text(
        "⚙️ <b>РУЧНОЙ РЕЖИМ</b>\n\nНастрой параметры кнопками ниже 👇",
        reply_markup=get_params_keyboard(user_id),
        parse_mode="HTML"
    )
    await callback.answer(f"🔢 Количество: {count_value}")

@router.callback_query(F.data == "reset_params")
async def reset_params(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data[user_id] = get_user_default_params()
    user_data[user_id]['mode'] = 'manual'
    
    await callback.message.edit_reply_markup(reply_markup=get_params_keyboard(user_id))
    await callback.answer("🔄 Параметры сброшены!")

@router.callback_query(F.data == "back_to_params")
async def back_to_params(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    await callback.message.edit_text(
        "⚙️ <b>РУЧНОЙ РЕЖИМ</b>\n\nНастрой параметры кнопками ниже 👇",
        reply_markup=get_params_keyboard(user_id),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "params_ready")
async def params_ready(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UniqueStates.waiting_for_photo)
    
    user_id = callback.from_user.id
    params = user_data[user_id]
    
    params_text = "⚙️ <b>РУЧНОЙ РЕЖИМ</b>\n\n"
    params_text += "Выбранные параметры:\n\n"
    params_text += f"🔊 Шумы: {'✅' if params['noise'] else '❌'}\n"
    params_text += f"📊 Полосы: {'✅' if params['stripes'] else '❌'}\n"
    params_text += f"😀 Эмодзи: {'✅' if params['smiles'] else '❌'}\n"
    params_text += f"🎨 Фон: {'✅' if params['background'] else '❌'}\n"
    params_text += f"🌫 Размытие: {params['blur_radius']}\n"
    params_text += f"🔢 Количество: {params['count']}\n\n"
    params_text += "📸 <b>Отправь фото!</b>"
    
    await callback.message.edit_text(params_text, parse_mode="HTML")
    await callback.answer()

@router.message(StateFilter(UniqueStates.waiting_for_photo), F.photo)
async def process_photo(message: Message, state: FSMContext, bot: Bot):
    """Обработка фото"""
    user_id = message.from_user.id
    params = user_data.get(user_id, get_user_default_params())
    
    await state.set_state(UniqueStates.processing)
    
    photo = message.photo[-1]
    
    if photo.file_size > config.MAX_FILE_SIZE:
        await message.answer(
            f"❌ Файл слишком большой!\nМаксимум: {config.MAX_FILE_SIZE // 1024 // 1024}MB"
        )
        await state.set_state(UniqueStates.waiting_for_photo)
        return
    
    mode_emoji = "🎲" if params.get('mode') == 'auto' else "⚙️"
    status_msg = await message.answer(
        f"{mode_emoji} <b>Обработка...</b>\n"
        f"Создаю {params['count']} версий 🔄",
        parse_mode="HTML"
    )
    
    try:
        file = await bot.get_file(photo.file_id)
        photo_bytes = await bot.download_file(file.file_path)
        image_data = photo_bytes.read()
        
        results = []
        for i in range(params['count']):
            try:
                # Если авто-режим - генерируем новые параметры для КАЖДОГО фото!
                if params.get('mode') == 'auto':
                    current_params = {
                        'noise': random.choice([True, False]),
                        'stripes': random.choice([True, False]),
                        'smiles': random.choice([True, True, False]),
                        'background': random.choice([True, False]),
                        'blur_radius': random.randint(0, 5)
                    }
                else:
                    current_params = params
                
                unique_image = uniqualizer.uniqualize(image_data, current_params)
                results.append(unique_image)
                
                if (i + 1) % 5 == 0:
                    await status_msg.edit_text(
                        f"{mode_emoji} <b>Обработка...</b>\n"
                        f"Готово: {i + 1}/{params['count']} 📊",
                        parse_mode="HTML"
                    )
            except Exception as e:
                logger.error(f"Error processing image {i}: {e}")
                continue
        
        await status_msg.edit_text(
            f"📤 <b>Отправка...</b>\nВсего: {len(results)} фото",
            parse_mode="HTML"
        )
        
        # Отправка результатов
        if len(results) <= 10:
            for idx, img_bytes in enumerate(results, 1):
                input_file = BufferedInputFile(img_bytes, filename=f"unique_{idx}.jpg")
                await message.answer_photo(
                    photo=input_file,
                    caption=f"{mode_emoji} Уникализация #{idx}"
                )
                await asyncio.sleep(0.3)
        else:
            from aiogram.types import InputMediaPhoto
            
            for i in range(0, len(results), 10):
                batch = results[i:i+10]
                media_group = []
                
                for idx, img_bytes in enumerate(batch, i+1):
                    input_file = BufferedInputFile(img_bytes, filename=f"unique_{idx}.jpg")
                    media = InputMediaPhoto(
                        media=input_file,
                        caption=f"{mode_emoji} #{idx}" if idx == i+1 else None
                    )
                    media_group.append(media)
                
                await message.answer_media_group(media=media_group)
                await asyncio.sleep(0.5)
        
        await status_msg.delete()
        
        mode_text = "🎲 АВТО" if params.get('mode') == 'auto' else "⚙️ РУЧНОЙ"
        await message.answer(
            f"✅ <b>Готово!</b>\n\n"
            f"Режим: {mode_text}\n"
            f"Создано: {len(results)} версий 🎉\n\n"
            f"Ещё? → /unique",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit_text(
            f"❌ <b>Ошибка!</b>\n\nПопробуй /unique",
            parse_mode="HTML"
        )
    
    await state.clear()

@router.message(StateFilter(UniqueStates.waiting_for_photo))
async def wrong_content_type(message: Message):
    await message.answer(
        "❌ Отправь <b>фото</b>!\n\nДокументы не поддерживаются.",
        parse_mode="HTML"
    )

async def main():
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    
    logger.info("🚀 Бот запущен!")
    
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
