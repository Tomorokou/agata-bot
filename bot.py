import asyncio
import re
import logging
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiohttp import web

# ===== ТОКЕН =====
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("❌ Добавь TELEGRAM_TOKEN в Environment Variables!")

# ===== НАСТРОЙКИ =====
ADMIN_ID = 7921434166
GROUP_CHAT_ID = -1004392428996
DEFAULT_THREAD_ID = 84

CHAT_THREADS = {
    'канал': 84,
    'чат': 78,
}

MODERATORS = {ADMIN_ID}
PENDING_REPORTS = {}
PENDING_CONFIRMATIONS = {}  # 👈 НОВОЕ: для подтверждения отправки
SELECTED_THREADS = {ADMIN_ID: DEFAULT_THREAD_ID}

# ===== ТРИГГЕРЫ =====
TRIGGER_ROOTS = [
    "педофил", "педофили", "педоф", "педик", "педовк",
    "pdo", "pedofil", "pedof", "ped0", "p3do",
    "секс", "sex", "с3кс", "секc",
    "наркот", "наркоман", "травк", "гашиш", "ширк", "ширев",
    "мефедрон", "меф", "кокаин", "кокс", "героин", "герыч",
    "марихуан", "амфетамин", "спайс", "соль",
    "убью", "убийств", "убить", "замоч", "грохн", "взорв",
    "взрывчатк", "расчлен", "зареж", "приконч",
    "урод", "мразь", "тварь", "сук", "бляд", "шлюх", "гандон",
    "ублюдок", "дебил", "идиот",
]

EXACT_TRIGGERS = [
    "смерть", "сдохни", "сдохнуть", "издохни",
    "трах", "трахать", "трахаться", "трахнуть",
    "ебля", "ебать", "ебал", "ебут", "ебли",
    "дроч", "отсос", "минет",
]

CHAR_REPLACEMENTS = {
    '@': 'а', 'ф': 'а', '0': 'о', '3': 'е',
    '1': 'и', '|': 'и', '$': 'с', 'c': 'с',
    '4': 'ч', '6': 'б', '8': 'в', '9': 'д',
    'p': 'р', 'x': 'х', 'y': 'у', 'k': 'к',
    'm': 'м', 'n': 'н', 't': 'т',
}

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ===== ФУНКЦИИ =====
def normalize_text(text: str) -> str:
    text = text.lower()
    for char, replacement in CHAR_REPLACEMENTS.items():
        text = text.replace(char, replacement)
    text = re.sub(r'(.)\1{2,}', r'\1\1', text)
    text = re.sub(r'[\s\.,;:!?\(\)\[\]\{\}]+', '', text)
    return text

def check_triggers(text: str):
    normalized_text = normalize_text(text)
    for word in EXACT_TRIGGERS:
        if word in normalized_text:
            return word
    for root in TRIGGER_ROOTS:
        if root in normalized_text:
            return root
    return None

def get_moderator_keyboard(report_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{report_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{report_id}")
        ],
        [
            InlineKeyboardButton(text="🔨 Бан", callback_data=f"ban_{report_id}"),
            InlineKeyboardButton(text="🔇 Мут", callback_data=f"mute_{report_id}")
        ],
        [
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_{report_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_thread_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    current = SELECTED_THREADS.get(ADMIN_ID, DEFAULT_THREAD_ID)
    for thread_name, thread_id in CHAT_THREADS.items():
        display_name = f"✅ {thread_name}" if thread_id == current else thread_name
        buttons.append([
            InlineKeyboardButton(
                text=display_name, 
                callback_data=f"thread_{thread_id}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_confirm_keyboard() -> InlineKeyboardMarkup:  # 👈 НОВОЕ
    buttons = [
        [
            InlineKeyboardButton(text="✅ Да, отправить", callback_data="confirm_send"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_send")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def send_report_to_moderators(message: types.Message, trigger_word: str):
    report_id = message.message_id
    PENDING_REPORTS[report_id] = {
        'chat_id': message.chat.id,
        'message_id': message.message_id,
        'user_id': message.from_user.id,
        'user_name': message.from_user.full_name,
        'username': message.from_user.username or 'нет username',
        'text': message.text,
        'trigger': trigger_word,
        'timestamp': datetime.now()
    }
    
    report_text = (
        f"🚨 Агата на посту! Обнаружено нарушение!\n\n"
        f"📍 Чат: {message.chat.title}\n"
        f"👤 Нарушитель: {message.from_user.full_name}"
        f" (@{message.from_user.username or 'нет username'})\n"
        f"🆔 ID: {message.from_user.id}\n"
        f"⚠️ Триггер: {trigger_word}\n"
        f"💬 Сообщение: {message.text[:500]}\n\n"
        f"🔗 Ссылка: {message.get_url()}"
    )
    
    for moderator_id in MODERATORS:
        try:
            await bot.send_message(
                chat_id=moderator_id,
                text=report_text,
                reply_markup=get_moderator_keyboard(report_id)
            )
        except Exception as e:
            logging.error(f"Ошибка отправки модератору {moderator_id}: {e}")

# ===== КОМАНДЫ =====
@dp.message(CommandStart())
async def start_command(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "🐱 Агата на связи.\n\n"
            "Команды:\n"
            "/add_moderator - добавить модератора\n"
            "/remove_moderator - уволить модератора\n"
            "/list_moderators - список модераторов\n"
            "/stats - статистика\n"
            "/threads - выбрать тему\n\n"
            "Просто напиши текст → я спрошу подтверждение → отправлю в группу."
        )
    else:
        await message.answer("Доступ запрещен.")

@dp.message(Command("threads"))
async def cmd_threads(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Только админ.")
        return
    await message.answer(
        "Выберите тему:",
        reply_markup=get_thread_keyboard()
    )

@dp.message(Command("add_moderator"))
async def cmd_add_moderator(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Только админ.")
        return
    if message.reply_to_message:
        new_moderator_id = message.reply_to_message.from_user.id
        new_moderator_name = message.reply_to_message.from_user.full_name
    else:
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("Ответь на сообщение человека или укажи ID.")
            return
        try:
            new_moderator_id = int(parts[1])
            new_moderator_name = f"User {new_moderator_id}"
        except ValueError:
            await message.answer("Это не ID.")
            return
    MODERATORS.add(new_moderator_id)
    await message.answer(f"✅ {new_moderator_name} теперь модератор.")

@dp.message(Command("remove_moderator"))
async def cmd_remove_moderator(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Только админ.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Укажи ID модератора.")
        return
    try:
        moderator_id = int(parts[1])
        if moderator_id in MODERATORS and moderator_id != ADMIN_ID:
            MODERATORS.remove(moderator_id)
            await message.answer(f"❌ Модератор {moderator_id} уволен.")
        else:
            await message.answer("Такого модератора нет.")
    except ValueError:
        await message.answer("Это не ID.")

@dp.message(Command("list_moderators"))
async def cmd_list_moderators(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Только админ.")
        return
    moderators_list = "\n".join([f"• {mod_id}" for mod_id in MODERATORS])
    await message.answer(f"Модераторы:\n{moderators_list}")

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Только админ.")
        return
    await message.answer(
        f"📊 Статистика:\n"
        f"• Активных репортов: {len(PENDING_REPORTS)}\n"
        f"• Модераторов: {len(MODERATORS)}\n"
        f"• Тем: {len(CHAT_THREADS)}"
    )

# ===== ОБРАБОТЧИКИ КНОПОК =====
@dp.callback_query(lambda c: c.data.startswith('thread_'))
async def process_thread_selection(callback_query: CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("Только админ.")
        return
    thread_id = int(callback_query.data.split('_')[1])
    SELECTED_THREADS[callback_query.from_user.id] = thread_id
    thread_name = "неизвестная"
    for name, tid in CHAT_THREADS.items():
        if tid == thread_id:
            thread_name = name
            break
    await callback_query.answer(f"Тема: {thread_name}")
    await callback_query.message.edit_text(
        f"✅ Тема: {thread_name}",
        reply_markup=get_thread_keyboard()
    )

@dp.callback_query(lambda c: c.data.startswith(('confirm_', 'reject_', 'ban_', 'mute_', 'delete_')))
async def process_callback(callback_query: CallbackQuery):
    if callback_query.from_user.id not in MODERATORS:
        await callback_query.answer("Нет прав.")
        return
    data = callback_query.data
    parts = data.split('_')
    if len(parts) < 2:
        return
    action = parts[0]
    report_id = int(parts[1])
    report_info = PENDING_REPORTS.get(report_id)
    if not report_info:
        await callback_query.answer("Репорт уже обработан.")
        return
    chat_id = report_info['chat_id']
    message_id = report_info['message_id']
    user_id = report_info['user_id']
    user_name = report_info['user_name']
    moderator_name = callback_query.from_user.full_name
    
    try:
        if action == "confirm":
            await callback_query.answer("Подтверждено.")
            new_text = f"✅ {moderator_name} подтвердил(а)"
        elif action == "reject":
            await callback_query.answer("Отклонено.")
            new_text = f"❌ {moderator_name} отклонил(а)"
        elif action == "ban":
            try:
                await bot.ban_chat_member(chat_id=chat_id, user_id=user_id, revoke_messages=True)
                await callback_query.answer("Забанен.")
                new_text = f"🔨 {moderator_name} забанил(а)"
                await bot.send_message(chat_id, f"🚨 {user_name} забанен.")
            except Exception as e:
                await callback_query.answer(f"Ошибка: {e}")
                return
        elif action == "mute":
            try:
                await bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=user_id,
                    permissions=types.ChatPermissions(can_send_messages=False),
                    until_date=datetime.now() + timedelta(hours=24)
                )
                await callback_query.answer("Замучен.")
                new_text = f"🔇 {moderator_name} замутил(а) на 24ч"
                await bot.send_message(chat_id, f"🔇 {user_name} замучен на 24 часа.")
            except Exception as e:
                await callback_query.answer(f"Ошибка: {e}")
                return
        elif action == "delete":
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
                await callback_query.answer("Удалено.")
                new_text = f"🗑 {moderator_name} удалил(а)"
                await bot.send_message(chat_id, f"🗑 Сообщение {user_name} удалено.")
            except Exception as e:
                await callback_query.answer(f"Ошибка: {e}")
                return
        await callback_query.message.edit_text(
            callback_query.message.text + "\n\n" + new_text
        )
        del PENDING_REPORTS[report_id]
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await callback_query.answer(f"Ошибка: {e}")

# ===== ПОДТВЕРЖДЕНИЕ ОТПРАВКИ (НОВОЕ) =====
@dp.callback_query(lambda c: c.data in ['confirm_send', 'cancel_send'])
async def process_confirm(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    
    if user_id != ADMIN_ID:
        await callback_query.answer("Только админ.", show_alert=True)
        return
    
    pending = PENDING_CONFIRMATIONS.get(user_id)
    if not pending:
        await callback_query.answer("Нет сообщений для отправки.", show_alert=True)
        return
    
    if callback_query.data == "confirm_send":
        try:
            await bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text=pending['text'],
                message_thread_id=pending['thread_id']
            )
            await callback_query.message.edit_text(
                f"✅ Отправлено в **{pending['thread_name']}**\n\n"
                f"{pending['text'][:300]}{'...' if len(pending['text']) > 300 else ''}",
                parse_mode="HTML"
            )
            await callback_query.answer("✅ Отправлено!")
        except Exception as e:
            await callback_query.message.edit_text(f"❌ Ошибка: {e}")
            await callback_query.answer("Ошибка отправки", show_alert=True)
        
        del PENDING_CONFIRMATIONS[user_id]
    
    elif callback_query.data == "cancel_send":
        await callback_query.message.edit_text("❌ Отменено")
        await callback_query.answer("Отменено")
        del PENDING_CONFIRMATIONS[user_id]

# ===== ЛИЧНЫЕ СООБЩЕНИЯ (С ПОДТВЕРЖДЕНИЕМ) =====
@dp.message(F.chat.type == ChatType.PRIVATE)
async def handle_private_messages(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    if message.text.startswith('/'):
        return
    
    thread_id = SELECTED_THREADS.get(message.from_user.id, DEFAULT_THREAD_ID)
    thread_name = "неизвестная"
    for name, tid in CHAT_THREADS.items():
        if tid == thread_id:
            thread_name = name
            break
    
    PENDING_CONFIRMATIONS[message.from_user.id] = {
        'text': message.text,
        'thread_id': thread_id,
        'thread_name': thread_name
    }
    
    await message.answer(
        f"📤 Отправить в **{thread_name}**?\n\n"
        f"Текст:\n{message.text[:300]}{'...' if len(message.text) > 300 else ''}",
        reply_markup=get_confirm_keyboard(),
        parse_mode="HTML"
    )

# ===== ПРОВЕРКА СООБЩЕНИЙ В ГРУППЕ =====
@dp.message(F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP]))
async def check_messages(message: types.Message):
    if not message.text:
        return
    trigger_found = check_triggers(message.text)
    if trigger_found:
        logging.info(f"Триггер '{trigger_found}' от {message.from_user.username}")
        await send_report_to_moderators(message, trigger_found)

# ===== ЗАПУСК =====
async def health_check(request):
    return web.Response(text="🐱 Агата на посту!")

def main():
    PORT = int(os.getenv("PORT", 8080))
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    
    async def start_polling():
        await bot.delete_webhook()
        await dp.start_polling(bot)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(start_polling())
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()