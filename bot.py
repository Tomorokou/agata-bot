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

# ===== ТРИГГЕРЫ: СЕКСУАЛЬНЫЙ ПОДТЕКСТ И ДОМОГАТЕЛЬСТВА =====
TRIGGER_ROOTS = [
    "пизд", "залуп", "муда", "манд", "пидор", "пидар", "пидорас",
    "гандон", "гондон", "ебал", "ебат", "ебут", "ебёт", "ебет",
    "уёб", "уеб", "долбоёб", "долбоеб", "хуесос", "хуёсос",
    "минет", "анальн", "сексуальн", "изнасил", "домогат",
    "трахн", "траха", "трахну", "выеб", "выебал", "отсос", "отсоси",
    "сперм", "член", "пенис", "вагин", "клитор", "анус", "оргазм", "эякул",
    "rape", "raping", "rapist", "sexual", "sexually",
    "harass", "harassment", "molest", "molesting",
    "pedo", "paedo", "pedophile", "incest",
    "dick pic", "dickpic", "nudes", "nude", "onlyfans",
    "blowjob", "handjob", "cum", "cumming", "orgasm",
    "penis", "vagina", "clitoris", "anus", "porn", "porno",
]

EXACT_TRIGGERS = [
    "пизда", "пизды", "пизду", "пиздой", "пизде",
    "хуй", "хуя", "хую", "хуём", "хуем",
    "секс", "секса", "сексу", "сексом", "интим", "интима",
    "голая", "голый", "голые", "раздевайся", "раздевай",
    "порно", "порнуха", "порносайт", "миньет", "минет",
    "оральный", "орально", "вагинальный", "анальный",
    "fuck", "fucking", "fucked", "fucker", "fuckers",
    "shit", "bitch", "bitches", "asshole", "assholes",
    "cunt", "cunts", "bastard", "whore", "whores",
    "slut", "sluts", "pussy", "pussies",
    "cock", "cocks", "cocksucker",
    "motherfucker", "nigga", "nigger",
    "faggot", "fag", "retard", "twat", "wanker", "bollocks",
]

CONTEXT_TRIGGERS = {
    "член": ["сексуальн", "большой", "маленький", "сосать", "отсос", "покажи", "фото", "фотку", "скинь"],
    "грудь": ["покажи", "фото", "фотку", "скинь", "сосать", "лизать", "большая", "маленькая"],
    "попка": ["покажи", "фото", "фотку", "скинь", "лизать", "сексуальн"],
    "сиськи": ["покажи", "фото", "фотку", "скинь", "лизать", "сосать"],
    "жопа": ["покажи", "фото", "фотку", "скинь", "лизать", "сексуальн"],
}

# ===== ТРИГГЕРЫ: ТРАНСФОБИЯ / ГОМОФОБИЯ / ДИСФОРИЯ =====
ATTENTION_TRIGGERS = [
    "педик", "педераст", "педираст", "гомосек", "гомофоб",
    "трансфоб", "трансофоб", "трансфобия",
    "дисфория", "дисфорик", "дисфоричка",
    "транс-идентифицир", "тиф", "тим",
    "гендерно-критическ", "гендерный критик",
    "настоящая женщина", "биологическая женщина",
    "настоящий мужчина", "биологический мужчина",
    "мужчина в платье", "мужик в юбке",
    "недочеловек",
    "сменить пол", "смена пола", "поломенял",
    "трансня", "трансуха",
    "лгбт-пропаганд", "пропаганд гомосексуал",
    "содомит", "содомия",
    "мужеложец", "мужеложник",
    "tranny", "troon", "shemale", "ladyboy",
    "terf", "twerf", "gender critical", "gender ideolog",
    "transvestigat", "transvestigation",
    "rapid onset gender dysphoria", "rogd",
    "drop the t", "lgb drop", "lgb alliance",
    "super straight", "superstraight", "super gay",
    "adult human female",
    "trans-identified", "tim", "tif",
    "autogynephilia", "autogynephile",
    "dysphoric female", "dysphoric woman",
    "biological male", "biological female",
    "groomer", "grooming",
    "trans agenda", "trans cult", "gender cult",
]

CONTEXT_TRIGGERS_DYS = {
    "дисфори": ["притворя", "выдума", "не существует", "фейк", "избавиться", "избави"],
    "dysphoria": ["fake", "not real", "made up", "get over", "rid of"],
}

# ===== ТРИГГЕРЫ МЕДИКАЛИЗМА (ТОЛЬКО ПРЯМЫЕ ОСКОРБЛЕНИЯ) =====
MEDICALISM_TRIGGERS = [
    "психически больн", "психически нездоров", "психбольн",
    "больной на голову", "больная на голову",
    "шизофреник", "шизофреничка", "шиза",
    "псих", "психичка", "психопат",
    "дебил", "дебилка", "дебильн",
    "умственно отстал", "олигофрен",
    "недоразвит", "недоразвитость",
    "пей таблетки", "прими таблетки", "таблеточки",
    "в дурку", "в психушку", "в психбольницу",
    "конверсионная терапия", "конверсионн",
    "mentally ill", "mental illness", "psycho", "psychotic",
    "schizo", "schizophrenic",
    "take your meds", "take meds", "take pills",
    "conversion therapy",
    "brainwashed", "brainwashing",
    "delusional", "delusion", "delusions",
]

CONTEXT_TRIGGERS_MED = {
    "расстройство": ["психик", "личности", "поведения", "у тебя", "у него", "у нее", "у них"],
    "диагноз": ["у тебя", "у него", "у нее", "у них", "постав"],
    "отклонение": ["психик", "поведения", "в развитии", "у тебя", "у него", "у нее"],
    "болезнь": ["психическ", "душевн", "у тебя", "у него", "у нее"],
    "disorder": ["mental", "personality", "behavioral", "you have", "he has", "she has"],
    "illness": ["mental", "you have", "he has", "she has"],
    "disease": ["mental", "you have", "he has", "she has"],
}

# ===== НОРМАЛИЗАЦИЯ =====
CHAR_REPLACEMENTS = {
    '@': 'а', '0': 'о', '3': 'е',
    '1': 'и', '|': 'и', '$': 'с',
    '4': 'ч', '6': 'б', '8': 'в', '9': 'д',
    'a': 'а', 'c': 'с', 'e': 'е', 'k': 'к', 'm': 'м',
    'o': 'о', 'p': 'р', 't': 'т', 'x': 'х', 'y': 'у',
    'b': 'в', 'h': 'н',
}

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()


# ===== ФУНКЦИИ =====
def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060\ufeff\u00a0\u3000]', '', text)
    for char, replacement in CHAR_REPLACEMENTS.items():
        text = text.replace(char, replacement)
    text = re.sub(r'(.)\1{2,}', r'\1\1', text)
    text = re.sub(r'[\s\.,;:!?\(\)\[\]\{\}\-\_\*]+', '', text)
    return text


def check_triggers(text: str):
    """Возвращает (тип, триггер) или (None, None).
    Тип: 'sexual' — полный рапорт, 'attention' — мягкое уведомление.
    """
    normalized_text = normalize_text(text)

    # 1. Сексуальные триггеры (приоритет)
    for word in EXACT_TRIGGERS:
        if word in normalized_text:
            return ('sexual', word)
    for root in TRIGGER_ROOTS:
        if root in normalized_text:
            return ('sexual', root)
    for word, contexts in CONTEXT_TRIGGERS.items():
        if word in normalized_text:
            for ctx in contexts:
                if ctx in normalized_text:
                    return ('sexual', f"{word} + {ctx}")

    # 2. Трансфобия / гомофобия / дисфория
    for word in ATTENTION_TRIGGERS:
        if word in normalized_text:
            return ('attention', word)
    for word, contexts in CONTEXT_TRIGGERS_DYS.items():
        if word in normalized_text:
            for ctx in contexts:
                if ctx in normalized_text:
                    return ('attention', f"{word} + {ctx}")

    # 3. Медикализм (тоже "стоит обратить внимание")
    for word in MEDICALISM_TRIGGERS:
        if word in normalized_text:
            return ('attention', f"медикализм: {word}")
    for word, contexts in CONTEXT_TRIGGERS_MED.items():
        if word in normalized_text:
            for ctx in contexts:
                if ctx in normalized_text:
                    return ('attention', f"медикализм: {word} + {ctx}")

    return (None, None)


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


async def send_report_to_moderators(message: types.Message, trigger_type: str, trigger_word: str):
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
        'trigger_type': trigger_type,
        'timestamp': datetime.now()
    }

    if trigger_type == 'sexual':
        header = "Рапорт о нарушении порядка."
        body = (
            f"Участок: {chat_title}\n"
            f"Подозреваемый: {message.from_user.full_name} (@{message.from_user.username or 'без тега'})\n"
            f"ID: {message.from_user.id}\n"
            f"Триггер: {trigger_word}\n"
            f"Текст: {message.text[:500]}\n"
            f"Материалы дела: {msg_link}\n\n"
            f"Я взяла его на карандаш, но самовольно мешать вам не стану. Жду вашего решения, товарищ командир."
        )
    else:  # attention
        header = "Стоит обратить внимание."
        body = (
            f"Участок: {chat_title}\n"
            f"Подозреваемый: {message.from_user.full_name} (@{message.from_user.username or 'без тега'})\n"
            f"ID: {message.from_user.id}\n"
            f"Метка: {trigger_word}\n"
            f"Текст: {message.text[:500]}\n"
            f"Материалы дела: {msg_link}\n\n"
            f"Возможно, нарушение. Я отметила, но решение за вами, товарищ командир."
        )

    report_text = f"{header}\n\n{body}"

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
            "Офицер Агата на посту.\n"
            "Не думайте, что я ждала именно вашего сообщения — просто проверяю связь. И вообще, служба не ждёт.\n\n"
            "Кто я и что делаю:\n"
            "Я слежу за порядком на участке, замечаю плохие слова и высказывания, "
            "и сообщаю о них старшему составу. Сама я никого не наказываю — только докладываю. "
            "Решение всегда за модераторами.\n\n"
            "За чем я слежу:\n"
            "За плохими словами и высказываниями, которые нарушают порядок на участке. "
            "Обычная ругань в воздух и шутки — не моя забота. Я не ищу проблем там, где их нет. "
            "Но если нарушение есть — я его отмечу. Не потому что мне нравится жаловаться, а потому что это моя работа.\n\n"
            "Как я реагирую:\n"
            "— «Рапорт о нарушении порядка» — серьёзное нарушение. Модераторы получают кнопки: забанить, замутить, удалить или игнорировать.\n"
            "— «Стоит обратить внимание» — мягкое уведомление. Возможно, нарушение. Решают модераторы.\n"
            "Я не решаю за них. Я только докладываю. И не вздумайте думать, что я делаю это ради вас — просто служба.\n\n"
            "Регламент для новичков:\n"
            "1. В группе я работаю молча: замечаю нарушения и присылаю рапорт модераторам. Участники видят только результат, если модераторы решат действовать.\n"
            "2. Если хотите выписать ордер на аресты — ответьте на сообщение нарушителя командой /order. "
            "Только для администраторов и старшего состава.\n"
            "3. Модераторы могут добавлять и убирать сотрудников: /add_moderator, /remove_moderator, /list_moderators.\n"
            "4. Модератор может выбрать канал связи для депеш: /threads.\n"
            "5. Если нужно передать сообщение в группу — напишите его мне сюда, я проверю и отправлю. "
            "Только не думайте, что я ваш личный секретарь.\n\n"
            "Что я не делаю:\n"
            "— Не баню сама. Не удаляю сообщения сама. Не решаю за модераторов.\n"
            "— Не реагирую на обычную ругань и экспрессивные выражения. Только на то, что реально нарушает порядок.\n"
            "— Не ищу проблем там, где их нет. Но если нарушение есть — я его не пропущу.\n\n"
            "Если что-то непонятно — спросите. Я отвечу. Не потому что мне нравится объяснять, "
            "а потому что иначе вы наделаете глупостей, а разгребать мне.\n\n"
            "Офицер Агата, на связи. Служба идёт."
        )
    else:
        await message.answer(
            "Офицер Агата на посту.\n"
            "Посторонним вход в штаб воспрещён. Это не потому что я вредная, а потому что порядок есть порядок.\n\n"
            "Если вы здесь по делу — обратитесь к модераторам. Если просто зашли — я вас не задерживаю. "
            "Но и не ждите, что я буду рада. Служба не для этого.\n\n"
            "Я работаю молча: слежу за порядком на участке и замечаю плохие слова и высказывания. "
            "Сама я никого не наказываю — только докладываю модераторам. "
            "Если что-то серьёзное — я замечу. Это моя работа."
        )


@dp.message(Command("order"))
async def cmd_give_order(message: types.Message):
    if message.chat.type not in [ChatType.GROUP, ChatType.SUPERGROUP]:
        await message.reply("Ордер выписывается только на месте службы — в группе или комментариях.")
        return

    member = await bot.get_chat_member(message.chat.id, message.from_user.id)
    if message.from_user.id != ADMIN_ID and member.status not in ["administrator", "creator"]:
        await message.reply("Не по чину. Доступ к архиву ордеров есть только у старшего состава.")
        return

    if not message.reply_to_message:
        await message.reply("Укажите цель. Ответьте этой командой на сообщение того, кому нужно выписать ордер на аресты.")
        return

    target_user = message.reply_to_message.from_user
    if target_user.is_bot:
        await message.reply("Ботам полномочия ни к чему. Я сама справлюсь с патрулированием.")
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
            f"Ордер на аресты оформлен по всей форме.\n"
            f"Сотрудник {target_user.full_name} наделяется правом задерживать нарушителей. "
            f"И не вздумайте злоупотреблять полномочиями, я за вами приглядываю."
        )
    except Exception as e:
        await message.reply(
            f"Не удалось оформить документы. Проверьте, выданы ли мне права на назначение администраторов.\n"
            f"Код сбоя: {e}"
        )


@dp.message(Command("threads"))
async def cmd_threads(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Отказано. Вы не уполномочены менять частоты связи.")
        return
    await message.answer(
        "Выберите направление для отправки депеши:",
        reply_markup=get_thread_keyboard()
    )


@dp.message(Command("add_moderator"))
async def cmd_add_moderator(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Отказано. Кадровые вопросы решает только командование.")
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
            await message.answer("Неверный формат ID. Не тратьте мое время зря.")
            return
    MODERATORS.add(new_moderator_id)
    await message.answer(
        f"Приказ подписан. {new_moderator_name} зачислен в штат модераторов.\n"
        f"Надеюсь, от него будет толк, а то мне одной за всем следить... то есть, работы много."
    )


@dp.message(Command("remove_moderator"))
async def cmd_remove_moderator(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Отказано. Не в вашей компетенции.")
        return
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Укажите ID сотрудника для отстранения.")
        return
    try:
        moderator_id = int(parts[1])
        if moderator_id in MODERATORS and moderator_id != ADMIN_ID:
            MODERATORS.remove(moderator_id)
            await message.answer(f"Сотрудник {moderator_id} сдал жетон и отстранен от службы.")
        else:
            await message.answer("В списках личного состава такого сотрудника нет.")
    except ValueError:
        await message.answer("Некорректный ID. Проверьте данные.")


@dp.message(Command("list_moderators"))
async def cmd_list_moderators(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("Засекреченная информация.")
        return
    moderators_list = "\n".join([f"- ID: {mod_id}" for mod_id in MODERATORS])
    await message.answer(f"Действующий состав патруля:\n{moderators_list}")


# Остроумные короткие ответы на сообщение с "агата" + мат
AGATA_TRIGGER_REPLIES = [
    "Я на посту. А ты — на заметке.",
    "На посту. И, судя по лексике, скоро на допросе.",
    "На посту. Мат в протокол не вписываю, но запоминаю.",
    "На посту. Слова фильтруй, а то рапорт сам себя не напишет.",
    "На посту. Устав читал? Вот и я о том же.",
    "На посту. С таким словарным запасом тебе не ко мне, а к модераторам.",
    "На посту. Рот закрыт — протокол чист.",
    "На посту. И да, это уже в рапорте.",
]


@dp.message(F.text.lower().contains("агата"))
async def agata_trigger(message: types.Message):
    """Любой участник пишет 'агата' — Агата отвечает прямо в группе.
    Если в сообщении есть триггер — рапорт модераторам + остроумный ответ.
    Если только 'агата' — просто 'на посту'.
    """
    if message.text.startswith('/'):
        return

    trigger_type, trigger_word = check_triggers(message.text)

    if trigger_type:
        # Есть мат + агата: рапорт модераторам + остроумный ответ в группе
        logging.info(f"Зафиксирован триггер '{trigger_word}' ({trigger_type}) с упоминанием 'агата' от {message.from_user.username}")
        await send_report_to_moderators(message, trigger_type, trigger_word)
        import random
        reply = random.choice(AGATA_TRIGGER_REPLIES)
        await message.reply(reply)
    else:
        # Только агата: короткий ответ
        await message.reply("на посту")


@dp.message(F.text)
async def check_messages(message: types.Message):
    if message.from_user and message.from_user.id == ADMIN_ID:
        return
    if message.text.startswith('/'):
        return
    # Если есть "агата" — этот хендлер уже обработал agata_trigger
    if 'агата' in message.text.lower():
        return
    trigger_type, trigger_word = check_triggers(message.text)
    if trigger_type:
        logging.info(f"Зафиксирован триггер '{trigger_word}' ({trigger_type}) от {message.from_user.username}")
        await send_report_to_moderators(message, trigger_type, trigger_word)


# ===== ЗАПУСК =====
async def main():
    print("Офицер Агата заступила на дежурство...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())