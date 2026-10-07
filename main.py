import json
import logging
import os
from pathlib import Path

from aiohttp import web

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery
)
from aiogram.webhook.aiohttp_server import (
    SimpleRequestHandler,
    setup_application
)


# ============================================================
# 1. ASOSIY SOZLAMALAR
# ============================================================

BOT_TOKEN = os.getenv("
8770001356:AAGq5P-ZfhYssSKGI87h5XDeWrDLTWfnkEE")

ADMIN_ID = 8286159397

# Admin Telegram username.
# @ belgisini qo'ymasdan yozing.
ADMIN_USERNAME = "RapKino"

# Majburiy obuna kanallari
CHANNELS = [
    "@ochiqkanalim",
    "@dddduzd"
]

# Render URL
WEBHOOK_HOST = "https://kino-bot-13xu.onrender.com"
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = WEBHOOK_HOST + WEBHOOK_PATH

# Render PORT
WEB_SERVER_HOST = "0.0.0.0"
WEB_SERVER_PORT = int(os.getenv("PORT", "10000"))

# Ma'lumotlar
DATA_FILE = Path("bot_data.json")


# ============================================================
# 2. LOG
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# 3. BOT VA DISPATCHER
# ============================================================

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN Environment Variable topilmadi!")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

dp = Dispatcher()


# ============================================================
# 4. MA'LUMOTLAR BAZASI
# ============================================================

def default_data():
    return {
        "movies": {},
        "vip_users": [],
        "users": []
    }


def load_data():
    if not DATA_FILE.exists():
        data = default_data()
        save_data(data)
        return data

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            return default_data()

        data.setdefault("movies", {})
        data.setdefault("vip_users", [])
        data.setdefault("users", [])

        return data

    except Exception as e:
        logger.error(f"Database o'qishda xatolik: {e}")
        return default_data()


def save_data(data):
    try:
        temp_file = DATA_FILE.with_suffix(".tmp")

        with open(temp_file, "w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=4
            )

        temp_file.replace(DATA_FILE)

    except Exception as e:
        logger.error(f"Database saqlashda xatolik: {e}")


# ============================================================
# 5. FSM
# ============================================================

class AddMovieState(StatesGroup):
    waiting_for_details = State()
    waiting_for_video = State()


# ============================================================
# 6. FOYDALANUVCHINI SAQLASH
# ============================================================

def register_user(user_id: int):
    data = load_data()

    if user_id not in data["users"]:
        data["users"].append(user_id)
        save_data(data)


def is_vip(user_id: int) -> bool:
    data = load_data()

    return (
        user_id == ADMIN_ID
        or user_id in data["vip_users"]
    )


# ============================================================
# 7. MAJBURIY OBUNA
# ============================================================

async def check_all_subs(user_id: int) -> bool:

    for channel in CHANNELS:

        try:
            member = await bot.get_chat_member(
                chat_id=channel,
                user_id=user_id
            )

            if member.status in ["left", "kicked"]:
                return False

        except Exception as e:
            logger.error(
                f"Obuna tekshirish xatosi {channel}: {e}"
            )

            return False

    return True


def subscription_keyboard():

    buttons = []

    for index, channel in enumerate(CHANNELS, start=1):

        username = channel.replace("@", "")

        buttons.append([
            InlineKeyboardButton(
                text=f"📢 {index}-kanalga obuna bo‘lish",
                url=f"https://t.me/{username}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="✅ Obunani tekshirish",
            callback_data="check_subscription"
        )
    ])

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


async def send_subscription_message(message: types.Message):

    await message.answer(
        "🔐 <b>Botdan foydalanish uchun obuna kerak</b>\n\n"
        "Kino olishdan oldin quyidagi kanallarga "
        "obuna bo‘ling.\n\n"
        "1️⃣ Kanalga kiring\n"
        "2️⃣ <b>Obuna bo‘lish</b> tugmasini bosing\n"
        "3️⃣ Barcha kanallarga obuna bo‘lgach, "
        "<b>✅ Obunani tekshirish</b> tugmasini bosing.\n\n"
        "🎬 Shundan so‘ng kino kodini yuborishingiz mumkin.",
        reply_markup=subscription_keyboard()
    )


# ============================================================
# 8. ASOSIY MENYU
# ============================================================

def main_menu():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="🎬 Kino olish",
                    callback_data="get_movie"
                ),
                InlineKeyboardButton(
                    text="💎 VIP",
                    callback_data="vip_info"
                )
            ],

            [
                InlineKeyboardButton(
                    text="📢 Kanallar",
                    callback_data="channels"
                ),
                InlineKeyboardButton(
                    text="ℹ️ Yordam",
                    callback_data="help"
                )
            ]

        ]
    )


# ============================================================
# 9. ADMIN MENYU
# ============================================================

def admin_menu():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="➕ Kino qo‘shish",
                    callback_data="admin_add"
                ),
                InlineKeyboardButton(
                    text="📋 Kinolar",
                    callback_data="admin_list"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🗑 Kino o‘chirish",
                    callback_data="admin_delete"
                ),
                InlineKeyboardButton(
                    text="📊 Statistika",
                    callback_data="admin_stats"
                )
            ],

            [
                InlineKeyboardButton(
                    text="💎 VIP berish",
                    callback_data="admin_vip_add"
                ),
                InlineKeyboardButton(
                    text="❌ VIPdan chiqarish",
                    callback_data="admin_vip_remove"
                )
            ]

        ]
    )


# ============================================================
# 10. START
# ============================================================

@dp.message(CommandStart())
async def start_handler(message: types.Message):

    user_id = message.from_user.id

    register_user(user_id)

    if not await check_all_subs(user_id):

        await send_subscription_message(message)
        return

    if user_id == ADMIN_ID:

        await message.answer(
            "👑 <b>Admin panel</b>\n\n"
            "Bot boshqaruviga xush kelibsiz.\n"
            "Quyidagi menyudan kerakli amalni tanlang:",
            reply_markup=admin_menu()
        )

        return

    status = (
        "💎 VIP foydalanuvchi"
        if is_vip(user_id)
        else "👤 Oddiy foydalanuvchi"
    )

    await message.answer(
        f"🎬 <b>Kino Botga xush kelibsiz!</b>\n\n"
        f"👋 Salom, <b>{message.from_user.full_name}</b>!\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"⭐ Status: <b>{status}</b>\n\n"
        "🎥 Kino olish uchun kino kodini yuboring.\n\n"
        "Masalan:\n"
        "<code>105</code>",
        reply_markup=main_menu()
    )


# ============================================================
# 11. OBUNA TEKSHIRISH CALLBACK
# ============================================================

@dp.callback_query(F.data == "check_subscription")
async def check_subscription_callback(
    call: CallbackQuery
):

    user_id = call.from_user.id

    if await check_all_subs(user_id):

        await call.answer(
            "✅ Obuna tasdiqlandi!",
            show_alert=True
        )

        try:
            await call.message.edit_text(
                "🎉 <b>Obunangiz tasdiqlandi!</b>\n\n"
                "Endi kino kodini yuborishingiz mumkin.\n\n"
                "🎬 Masalan: <code>105</code>",
                reply_markup=main_menu()
            )

        except Exception:
            pass

    else:

        await call.answer(
            "❌ Siz hali barcha kanallarga obuna bo‘lmagansiz.",
            show_alert=True
        )


# ============================================================
# 12. KINO OLISH TUGMASI
# ============================================================

@dp.callback_query(F.data == "get_movie")
async def get_movie_button(call: CallbackQuery):

    if not await check_all_subs(call.from_user.id):

        await call.answer(
            "Avval kanallarga obuna bo‘ling.",
            show_alert=True
        )

        return

    await call.message.answer(
        "🎬 <b>Kino kodini yuboring</b>\n\n"
        "Masalan:\n"
        "<code>105</code>\n\n"
        "💡 Kino kodi odatda raqamlardan iborat bo‘ladi."
    )

    await call.answer()


# ============================================================
# 13. VIP MA'LUMOT
# ============================================================

@dp.callback_query(F.data == "vip_info")
async def vip_info(call: CallbackQuery):

    await call.message.answer(
        "💎 <b>VIP OBUNA</b>\n\n"
        "VIP obunachilar maxsus pullik kinolardan "
        "foydalanishlari mumkin.\n\n"
        "⭐ VIP imkoniyatlari:\n"
        "• 🔐 VIP kinolarga kirish\n"
        "• 🎬 Maxsus kontent\n"
        "• ⚡ Qulay foydalanish\n\n"
        "💳 VIP obuna olish uchun admin bilan bog‘laning.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💎 VIP obuna sotib olish",
                        url=f"https://t.me/{ADMIN_USERNAME}"
                    )
                ]
            ]
        )
    )

    await call.answer()


# ============================================================
# 14. KANALLAR
# ============================================================

@dp.callback_query(F.data == "channels")
async def channels_callback(call: CallbackQuery):

    await call.message.answer(
        "📢 <b>Bizning kanallar</b>\n\n"
        "Botdan foydalanish uchun quyidagi kanallarga "
        "obuna bo‘lish kerak.",
        reply_markup=subscription_keyboard()
    )

    await call.answer()


# ============================================================
# 15. YORDAM
# ============================================================

@dp.callback_query(F.data == "help")
async def help_callback(call: CallbackQuery):

    await call.message.answer(
        "ℹ️ <b>BOTDAN FOYDALANISH</b>\n\n"
        "1️⃣ Kanallarga obuna bo‘ling.\n"
        "2️⃣ Obunani tekshiring.\n"
        "3️⃣ Kino kodini yuboring.\n"
        "4️⃣ Kino mavjud bo‘lsa, video avtomatik yuboriladi.\n\n"
        "❓ Kod ishlamasa, kodni qayta tekshiring.\n\n"
        "💎 VIP kino uchun VIP obuna kerak."
    )

    await call.answer()


# ============================================================
# 16. KINO KODI
# ============================================================

@dp.message(F.text)
async def movie_search(message: types.Message):

    user_id = message.from_user.id

    # Buyruqlarni o'tkazib yuboramiz
    if message.text.startswith("/"):
        return

    register_user(user_id)

    # Obuna
    if not await check_all_subs(user_id):

        await send_subscription_message(message)
        return

    code = message.text.strip()

    data = load_data()
    movies = data["movies"]

    # ========================================================
    # KINO TOPILMADI
    # ========================================================

    if code not in movies:

        await message.answer(
            "🔎 <b>Kino topilmadi</b>\n\n"
            f"❌ Siz yuborgan kod: <code>{code}</code>\n\n"
            "Bu kod bo‘yicha kino bazamizda ma'lumot topilmadi.\n\n"
            "💡 <b>Iltimos:</b>\n"
            "• Kodni qayta tekshiring\n"
            "• Raqamlarni to‘g‘ri yuboring\n"
            "• Masalan: <code>105</code>\n\n"
            "🎬 Kino kodi bo‘yicha yana urinib ko‘ring."
        )

        return

    movie = movies[code]

    title = movie.get("title", "Noma'lum kino")
    premium = movie.get("is_premium", False)
    file_id = movie.get("file_id")

    # ========================================================
    # VIP KINO
    # ========================================================

    if premium and not is_vip(user_id):

        await message.answer(
            "🔐 <b>VIP KINO</b>\n\n"
            f"🎬 <b>{title}</b>\n\n"
            "Bu kino <b>VIP obunachilar</b> uchun maxsus.\n\n"
            "💎 VIP obuna orqali ushbu kinoni tomosha "
            "qilishingiz mumkin.\n\n"
            "👇 VIP obuna haqida ma'lumot olish uchun "
            "quyidagi tugmani bosing.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[

                    [
                        InlineKeyboardButton(
                            text="💎 VIP obuna sotib olish",
                            url=f"https://t.me/{ADMIN_USERNAME}"
                        )
                    ],

                    [
                        InlineKeyboardButton(
                            text="ℹ️ VIP haqida",
                            callback_data="vip_info"
                        )
                    ]

                ]
            )
        )

        return

    # ========================================================
    # KINO YUBORISH
    # ========================================================

    if not file_id:

        await message.answer(
            "⚠️ <b>Texnik xatolik</b>\n\n"
            "Ushbu kinoning video fayli topilmadi.\n"
            "Admin tez orada muammoni hal qiladi."
        )

        return

    try:

        await message.answer_video(
            video=file_id,
            caption=(
                f"🎬 <b>{title}</b>\n\n"
                "🍿 Maroqli tomosha tilaymiz!\n\n"
                "⭐ <b>Kino Bot</b>"
            )
        )

    except Exception as e:

        logger.error(f"Video yuborishda xatolik: {e}")

        await message.answer(
            "⚠️ <b>Videoni yuborishda xatolik yuz berdi.</b>\n\n"
            "Iltimos, birozdan keyin qayta urinib ko‘ring."
        )


# ============================================================
# 17. ADMIN TEKSHIRUVI
# ============================================================

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ============================================================
# 18. ADMIN PANEL
# ============================================================

@dp.message(Command("admin"))
async def admin_command(message: types.Message):

    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "👑 <b>ADMIN PANEL</b>\n\n"
        "Botni boshqarish uchun menyudan foydalaning.",
        reply_markup=admin_menu()
    )


@dp.callback_query(F.data == "admin_add")
async def admin_add_button(
    call: CallbackQuery,
    state: FSMContext
):

    if not is_admin(call.from_user.id):
        await call.answer("⛔ Ruxsat yo‘q!", show_alert=True)
        return

    await call.message.answer(
        "➕ <b>YANGI KINO QO‘SHISH</b>\n\n"
        "Quyidagi formatda yuboring:\n\n"
        "<code>105 | Forsaj 10 | free</code>\n\n"
        "yoki:\n\n"
        "<code>106 | Avatar 2 | premium</code>\n\n"
        "📌 <b>free</b> — bepul kino\n"
        "💎 <b>premium</b> — VIP kino"
    )

    await state.set_state(
        AddMovieState.waiting_for_details
    )

    await call.answer()


# ============================================================
# 19. KINO MA'LUMOTI
# ============================================================

@dp.message(AddMovieState.waiting_for_details)
async def process_movie_details(
    message: types.Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        return

    if not message.text:
        return

    try:

        parts = [
            p.strip()
            for p in message.text.split("|")
        ]

        if len(parts) < 3:

            await message.answer(
                "❌ <b>Format noto‘g‘ri!</b>\n\n"
                "To‘g‘ri format:\n"
                "<code>105 | Forsaj 10 | free</code>"
            )

            return

        code = parts[0]
        title = parts[1]
        type_value = parts[2].lower()

        if not code:
            await message.answer("❌ Kino kodi bo‘sh bo‘lishi mumkin emas.")
            return

        if not title:
            await message.answer("❌ Kino nomi bo‘sh bo‘lishi mumkin emas.")
            return

        premium = type_value in [
            "premium",
            "vip",
            "true"
        ]

        await state.update_data(
            code=code,
            title=title,
            is_premium=premium
        )

        status = "💎 VIP" if premium else "🆓 Bepul"

        await message.answer(
            "✅ <b>Kino ma'lumotlari qabul qilindi</b>\n\n"
            f"🔑 Kod: <code>{code}</code>\n"
            f"🎬 Nom: <b>{title}</b>\n"
            f"⭐ Tur: <b>{status}</b>\n\n"
            "🎥 Endi shu kinoning <b>video faylini</b> yuboring."
        )

        await state.set_state(
            AddMovieState.waiting_for_video
        )

    except Exception as e:

        logger.error(e)

        await message.answer(
            "⚠️ Ma'lumotni qayta ishlashda xatolik yuz berdi."
        )


# ============================================================
# 20. VIDEO QABUL QILISH
# ============================================================

@dp.message(
    AddMovieState.waiting_for_video,
    F.video
)
async def process_movie_video(
    message: types.Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        return

    data_state = await state.get_data()

    code = data_state["code"]
    title = data_state["title"]
    premium = data_state["is_premium"]

    data = load_data()

    data["movies"][code] = {
        "title": title,
        "is_premium": premium,
        "file_id": message.video.file_id
    }

    save_data(data)

    status = "💎 VIP" if premium else "🆓 Bepul"

    await message.answer(
        "🎉 <b>KINO MUVAFFAQIYATLI SAQLANDI!</b>\n\n"
        f"🎬 <b>{title}</b>\n"
        f"🔑 Kod: <code>{code}</code>\n"
        f"⭐ Tur: <b>{status}</b>\n\n"
        "Endi foydalanuvchi ushbu kodni yuborsa, "
        "kino avtomatik yuboriladi."
    )

    await state.clear()


# ============================================================
# 21. ADMIN KINO RO‘YXATI
# ============================================================

@dp.callback_query(F.data == "admin_list")
async def admin_list(call: CallbackQuery):

    if not is_admin(call.from_user.id):
        return

    data = load_data()
    movies = data["movies"]

    if not movies:

        await call.message.answer(
            "📭 <b>Kino bazasi bo‘sh.</b>"
        )

        await call.answer()
        return

    text = "📋 <b>KINOLAR RO‘YXATI</b>\n\n"

    for code, movie in movies.items():

        title = movie.get("title", "Noma'lum")
        tag = (
            "💎 VIP"
            if movie.get("is_premium")
            else "🆓 FREE"
        )

        text += (
            f"🔑 <code>{code}</code> — "
            f"<b>{title}</b> — {tag}\n"
        )

    await call.message.answer(text)
    await call.answer()


# ============================================================
# 22. ADMIN DEL
# ============================================================

@dp.callback_query(F.data == "admin_delete")
async def admin_delete(call: CallbackQuery):

    if not is_admin(call.from_user.id):
        return

    await call.message.answer(
        "🗑 <b>KINO O‘CHIRISH</b>\n\n"
        "Kino kodini yuboring.\n\n"
        "Masalan:\n"
        "<code>/del 105</code>"
    )

    await call.answer()


@dp.message(Command("del"))
async def delete_movie(message: types.Message):

    if not is_admin(message.from_user.id):
        return

    try:

        parts = message.text.split()

        if len(parts) < 2:
            raise ValueError

        code = parts[1]

        data = load_data()

        if code not in data["movies"]:

            await message.answer(
                "❌ Bu kod bo‘yicha kino topilmadi."
            )

            return

        title = data["movies"][code]["title"]

        del data["movies"][code]

        save_data(data)

        await message.answer(
            "🗑 <b>KINO O‘CHIRILDI</b>\n\n"
            f"🎬 {title}\n"
            f"🔑 Kod: <code>{code}</code>"
        )

    except Exception:

        await message.answer(
            "⚠️ To‘g‘ri foydalanish:\n"
            "<code>/del 105</code>"
        )


# ============================================================
# 23. VIP BERISH
# ============================================================

@dp.callback_query(F.data == "admin_vip_add")
async def admin_vip_add_button(call: CallbackQuery):

    if not is_admin(call.from_user.id):
        return

    await call.message.answer(
        "💎 <b>VIP BERISH</b>\n\n"
        "Foydalanuvchi Telegram ID raqamini yuboring.\n\n"
        "Masalan:\n"
        "<code>/vip 123456789</code>"
    )

    await call.answer()


@dp.message(Command("vip"))
async def make_vip(message: types.Message):

    if not is_admin(message.from_user.id):
        return

    try:

        user_id = int(message.text.split()[1])

        data = load_data()

        if user_id not in data["vip_users"]:
            data["vip_users"].append(user_id)

        save_data(data)

        await message.answer(
            "💎 <b>VIP MUVAFFAQIYATLI BERILDI!</b>\n\n"
            f"👤 ID: <code>{user_id}</code>\n\n"
            "Ushbu foydalanuvchi endi VIP kinolarni "
            "olishi mumkin."
        )

    except Exception:

        await message.answer(
            "⚠️ To‘g‘ri foydalanish:\n"
            "<code>/vip 123456789</code>"
        )


# ============================================================
# 24. VIPDAN CHIQARISH
# ============================================================

@dp.callback_query(F.data == "admin_vip_remove")
async def admin_vip_remove_button(call: CallbackQuery):

    if not is_admin(call.from_user.id):
        return

    await call.message.answer(
        "❌ <b>VIPDAN CHIQARISH</b>\n\n"
        "Foydalanuvchi ID sini yuboring:\n\n"
        "<code>/unvip 123456789</code>"
    )

    await call.answer()


@dp.message(Command("unvip"))
async def remove_vip(message: types.Message):

    if not is_admin(message.from_user.id):
        return

    try:

        user_id = int(message.text.split()[1])

        data = load_data()

        if user_id in data["vip_users"]:
            data["vip_users"].remove(user_id)
            save_data(data)

            await message.answer(
                "❌ <b>VIP STATUS O‘CHIRILDI</b>\n\n"
                f"👤 ID: <code>{user_id}</code>"
            )

        else:

            await message.answer(
                "ℹ️ Bu foydalanuvchi VIP ro‘yxatida yo‘q."
            )

    except Exception:

        await message.answer(
            "⚠️ To‘g‘ri foydalanish:\n"
            "<code>/unvip 123456789</code>"
        )


# ============================================================
# 25. STATISTIKA
# ============================================================

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery):

    if not is_admin(call.from_user.id):
        return

    data = load_data()

    total_movies = len(data["movies"])
    total_users = len(data["users"])
    total_vip = len(data["vip_users"])

    free_movies = sum(
        1
        for movie in data["movies"].values()
        if not movie.get("is_premium")
    )

    premium_movies = sum(
        1
        for movie in data["movies"].values()
        if movie.get("is_premium")
    )

    await call.message.answer(
        "📊 <b>BOT STATISTIKASI</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{total_users}</b>\n"
        f"💎 VIP foydalanuvchilar: <b>{total_vip}</b>\n\n"
        f"🎬 Jami kinolar: <b>{total_movies}</b>\n"
        f"🆓 Bepul kinolar: <b>{free_movies}</b>\n"
        f"💎 VIP kinolar: <b>{premium_movies}</b>"
    )

    await call.answer()


# ============================================================
# 26. ADMIN BUYRUQLARI
# ============================================================

@dp.message(Command("list"))
async def list_command(message: types.Message):

    if not is_admin(message.from_user.id):
        return

    data = load_data()

    if not data["movies"]:

        await message.answer(
            "📭 Kino bazasi hozircha bo‘sh."
        )

        return

    text = "📋 <b>KINOLAR</b>\n\n"

    for code, movie in data["movies"].items():

        tag = (
            "💎 VIP"
            if movie.get("is_premium")
            else "🆓 FREE"
        )

        text += (
            f"🔑 <code>{code}</code> — "
            f"{movie.get('title')} — {tag}\n"
        )

    await message.answer(text)


# ============================================================
# 27. ADMIN PANEL CALLBACK
# ============================================================

@dp.callback_query(F.data == "admin_panel")
async def admin_panel_callback(call: CallbackQuery):

    if not is_admin(call.from_user.id):
        return

    await call.message.answer(
        "👑 <b>ADMIN PANEL</b>",
        reply_markup=admin_menu()
    )

    await call.answer()


# ============================================================
# 28. WEBHOOK STARTUP
# ============================================================

async def on_startup(bot: Bot):

    logger.info(
        f"Webhook o'rnatilmoqda: {WEBHOOK_URL}"
    )

    await bot.set_webhook(
        url=WEBHOOK_URL,
        drop_pending_updates=True
    )

    logger.info("Webhook muvaffaqiyatli o'rnatildi.")


async def on_shutdown(bot: Bot):

    logger.info("Bot to'xtatilmoqda...")

    try:
        await bot.delete_webhook()
    except Exception as e:
        logger.error(e)


# ============================================================
# 29. WEB SERVER
# ============================================================

def main():

    app = web.Application()

    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    )

    webhook_handler.register(
        app,
        path=WEBHOOK_PATH
    )

    setup_application(
        app,
        dp,
        bot=bot
    )

    logger.info(
        f"Server ishga tushmoqda: "
        f"{WEB_SERVER_HOST}:{WEB_SERVER_PORT}"
    )

    web.run_app(
        app,
        host=WEB_SERVER_HOST,
        port=WEB_SERVER_PORT
    )


if __name__ == "__main__":
    main()
