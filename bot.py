import asyncio
import re
import logging
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ChatType
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# ===== ТОКЕН =====
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("Ошибка запуска: отсутствует TELEGRAM_TOKEN в переменных окружения.")

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
PENDING_CONFIRMATIONS = {}
SELECTED_THREADS = {ADMIN_ID: DEFAULT_THREAD_ID}

# ===== ТРИГГЕРЫ (впиши свои слова вместо "---") =====
TRIGGER_ROOTS = [
    "---",
    "---",
]

EXACT_TRIGGERS = [
    "---",
    "---",
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
        if word != "---" and word in normalized_text:
            return word
    for root in TRIGGER_ROOTS:
        if root != "---" and root in normalized_text:
            return root
    return None


def get_moderator_keyboard(report_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="🔨 Забанить", callback_data=f"ban_{report_id}"),
            InlineKeyboardButton(text="📄 Игнор", callback_data=f"reject_{report_id}")
        ],
        [
            InlineKeyboardButton(text="🔇 Мут 24ч", callback_data=f"mute_{report_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_{report_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_thread_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    current = SELECTED_THREADS.get(ADMIN_ID, DEFAULT_THREAD_ID)
    for thread_name, thread_id in CHAT_THREADS.items():
        display_name = f"📁 [Выбрано] {thread_name}" if thread_id == current else f"📁 {thread_name}"
        buttons.append([
            InlineKeyboardButton(
                text=display_name,
                callback_data=f"thread_{thread_id}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="📄 Подтвердить отправку", callback_data="confirm_send"),
            InlineKeyboardButton(text="✖ Отмена", callback_data="cancel_send")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def send_report_to_moderators(message: types.Message, trigger_word: str):
    report_id = message.message_id
    chat_title = message.chat.title or "Комментарии канала"
    msg_link = message.get_url() or "ссылка недоступна"

    PENDING_REPORTS[report_id] = {
        'chat_id': message.chat.id,
        'message_id': message.message_id,
        'user_id': message.from_user.id,
        'user_name': message.from_user.full_name,
        'username': message.from_user.username or 'отсутствует',
        'text': message.text,
        'trigger': trigger_word,
        'timestamp': datetime.now()
    }

    report_text = (
        f"Рапорт о нарушении порядка. (=｀ω´=)\n\n"
        f"Участок: {chat_title}\n"
        f"Подозреваемый: {message.from_user.full_name} (@{message.from_user.username or 'без тега'})\n"
        f"ID: {message.from_user.id}\n"
        f"Триггер: {trigger_word}\n"
        f"Текст: {message.text[:500]}\n"
        f"Материалы дела: {msg_link}\n\n"
        f"Я взяла его на карандаш, но самовольно мешать вам не стану. Жду вашего решения, товарищ командир."
    )

    for moderator_id in MODERATORS:
        try:
            await bot.send_message(
                chat_id=moderator_id,
                text=report_text,
                reply_markup=get_moderator_keyboard(report_id)
            )
        except Exception as e:
            logging.error(f"Ошибка отправки рапорта модератору {moderator_id}: {e}")


# ===== КОМАНДЫ =====
@dp.message(CommandStart())
async def start_command(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer(
            "Офицер Агата на посту. (=｀ω´=)\n"
            "Не думайте, что я ждала именно вашего сообщения, просто проверяю связь.\n\n"
            "Служебный регламент:\n"
            "/order - выписать ордер на аресты (ответом на сообщение в группе)\n"
            "/add_moderator - зачислить в штат модераторов\n"
            "/remove_moderator - отстранить от службы\n"
            "/list_moderators - личный состав\n"
            "/stats - сводка по участку\n"
            "/threads - выбрать канал связи\n\n"
            "Если нужно передать сообщение в группу — просто напишите его сюда. Я проверю и отправлю, чтобы вы не наделали глупостей."
        )
    else:
        await message.answer("Отставить. Посторонним вход в штаб строго воспрещен. (=｀ω´=)")


@dp.message(Command("order"))
async def cmd_give_order(message: types.Message):
    if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.reply("Ордер выписывается только на месте службы — в группе или комментариях. (=｀ω´=)")
        return

    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if message.from_user.id != ADMIN_ID and member.status not in ["administrator", "creator"]:
        await message.reply("Не по чину. Доступ к архиву ордеров есть только у старшего состава. (=｀ω´=)")
        return

    if not message.reply_to_message:
        await message.reply("Укажите цель. Ответьте этой командой на сообщение того, кому нужно выписать ордер на аресты. (=｀ω´=)")
        return

    target_user = message.reply_to_message.from_user
    if target_user.is_bot:
        await message.reply("Ботам полномочия ни к чему. Я сама справлюсь с патрулированием. (=｀ω´=)")
        return

    try:
        await bot.promote_chat_member(
            chat_id=message.chat.id,
            user_id=target_user.id,
            can_restrict_members=True,
            can_delete_messages=True
        )
        MODERATORS.add(target_user.id)
        await message.reply(
            f"Ордер на аресты оформлен по всей форме. (=｀ω´=)\n"
            f"Сотрудник {target_user.full_name} наделяется правом задерживать нарушителей. "
            f"И не вздумайте злоупотреблять полномочиями, я за вами приглядываю."
        )
    except Exception as e:
        await message.reply(
            f"Не удалось оформить документы. Проверьте, выданы ли мне права на назначение администраторов. (=｀ω´=)\n"
            f"Код сбоя: {e}"
        )


@dp.message(Command("threads"))
async def cmd_threads(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Отказано. Вы не уполномочены менять частоты связи. (=｀ω´=)")
        return
    await message.answer(
        "Выберите направление для отправки депеши:",
        reply_markup=get_thread_keyboard()
    )


@dp.message(Command("add_moderator"))
async def cmd_add_moderator(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Отказано. Кадровые вопросы решает только командование. (=｀ω´=)")
        return
    if message.reply_to_message:
        new_moderator_id = message.reply_to_message.from_user.id
        new_moderator_name = message.reply_to_message.from_user.full_name
    else:
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("Укажите личный номер (ID) или ответьте на сообщение кандидата.")
            return
        try:
            new_moderator_id = int(parts[1])
            new_moderator_name = f"Сотрудник {new_moderator_id}"
        except ValueError:
            await message.answer("Неверный формат ID. Не тратьте мое время зря. (=｀ω´=)")
            return
    MODERATORS.add(new_moderator_id)
    await message.answer(
        f"Приказ подписан. {new_moderator_name} зачислен в штат модераторов. (=｀ω´=)\n"
        f"Надеюсь, от него будет толк, а то мне одной за всем следить... то есть, работы много."
    )


@dp.message(Command("remove_moderator"))
async def cmd_remove_moderator(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Отказано. Не в вашей компетенции. (=｀ω´=)")
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Укажите ID сотрудника для отстранения.")
        return
    try:
        moderator_id = int(parts[1])
        if moderator_id in MODERATORS and moderator_id != ADMIN_ID:
            MODERATORS.remove(moderator_id)
            await message.answer(f"Сотрудник {moderator_id} сдал жетон и отстранен от службы. (=｀ω´=)")
        else:
            await message.answer("В списках личного состава такого сотрудника нет.")
    except ValueError:
        await message.answer("Некорректный ID. Проверьте данные.")


@dp.message(Command("list_moderators"))
async def cmd_list_moderators(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Засекреченная информация. (=｀ω´=)")
        return
    moderators_list = "\n".join([f"- ID: {mod_id}" for mod_id in MODERATORS])
    await message.answer(f"Действующий состав патруля:\n{moderators_list}")


async def check_messages(message: types.Message):
if not message.text:
return
if message.from_user and message.from_user.id == ADMIN_ID:
return
trigger_found = check_triggers(message.text)
if trigger_found:
logging.info(f"Зафиксирован триггер '{trigger_found}' от {message.from_user.username}")
await send_report_to_moderators(message, trigger_found)

===== ЗАПУСК =====

async def main():
print("Офицер Агата заступила на дежурство...")
await dp.start_polling(bot)
if name == "main":
asyncio.run(main())