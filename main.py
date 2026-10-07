import asyncio
import logging
import json
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

# ==================== 1. BOT SOZLAMALARI ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8770001356:AAGq5P-ZfhYssSKGI87h5XDeWrDLTwfnkEE")
ADMIN_ID = 8286159397  # Sizning Telegram ID-ingiz

CHANNELS = [
    "@ochiqkanalim",
    "@dddduzd"
]

VIP_USERS = set()
JSON_FILE = "movies.json"

# ==================== 2. MA'LUMOTLAR BAZASI ====================
def load_movies():
    if not os.path.exists(JSON_FILE):
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
        return {}
    try:
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_movies(data):
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

class AddMovieState(StatesGroup):
    waiting_for_details = State()
    waiting_for_video = State()

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

# ==================== 3. YORDAMCHI FUNKSIYALAR ====================
async def check_all_subs(user_id: int) -> bool:
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception as e:
            logging.error(f"Kanalni tekshirishda xatolik ({channel}): {e}")
            return False
    return True

def get_sub_keyboard():
    buttons = []
    for idx, channel in enumerate(CHANNELS, start=1):
        clean_username = channel.replace("@", "")
        buttons.append([
            InlineKeyboardButton(text=f"📢 {idx}-Kanalga obuna bo'lish", url=f"https://t.me/{clean_username}")
        ])
    buttons.append([
        InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_subscription")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ==================== 4. ADMIN BUYRUQLARI ====================

@dp.message(Command("add"))
async def start_add_movie(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    await message.answer(
        "🎬 *Yangi kino qo'shish rejimi*\n\n"
        "Iltimos, kino kodi, nomi va turini quyidagi formatda yuboring:\n"
        "`kod | Kino nomi | free` (yoki `premium`)\n\n"
        "*Masalan:* `105 | Forsaj 10 | free`"
    )
    await state.set_state(AddMovieState.waiting_for_details)

@dp.message(AddMovieState.waiting_for_details)
async def process_movie_details(message: types.Message, state: FSMContext):
    try:
        parts = [p.strip() for p in message.text.split("|")]
        if len(parts) < 3:
            await message.answer("⚠️ Format noto'g'ri! Qaytadan kiriting (Masalan: `105 | Forsaj 10 | free`):")
            return

        code, title, is_premium_str = parts[0], parts[1], parts[2].lower()
        is_premium = True if is_premium_str in ["premium", "vip", "true"] else False

        await state.update_data(code=code, title=title, is_premium=is_premium)
        await message.answer(f"✅ Ma'lumot qabul qilindi:\n\n📌 Kod: `{code}`\n🎬 Nomi: *{title}*\n⭐ VIP: *{is_premium}*\n\n**Endi kinoning video faylini botga yuboring:**")
        await state.set_state(AddMovieState.waiting_for_video)
    except Exception as e:
        await message.answer(f"⚠️ Xatolik yuz berdi: {e}")

@dp.message(AddMovieState.waiting_for_video, F.video)
async def process_movie_video(message: types.Message, state: FSMContext):
    data = await state.get_data()
    file_id = message.video.file_id

    movies = load_movies()
    movies[data['code']] = {
        "type": "single",
        "title": data['title'],
        "is_premium": data['is_premium'],
        "file_id": file_id
    }
    save_movies(movies)

    await message.answer(f"🎉 *\"{data['title']}\"* kinosi muvaffaqiyatli saqlandi!\n🔑 Kodi: `{data['code']}`")
    await state.clear()

@dp.message(Command("list"))
async def list_movies(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    movies = load_movies()
    if not movies:
        await message.answer("📭 Bazada hali hech qanday kino yo'q.")
        return

    text = "📋 *Bazardagi kinolar ro'yxati:*\n\n"
    for code, m in movies.items():
        vip_tag = "⭐ VIP" if m.get("is_premium") else "🆓 Bepul"
        text += f"• `{code}` - *{m['title']}* ({vip_tag})\n"

    await message.answer(text)

@dp.message(Command("del"))
async def delete_movie(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        code = message.text.split()[1]
        movies = load_movies()
        if code in movies:
            del movies[code]
            save_movies(movies)
            await message.answer(f"🗑 `{code}` kodli kino bazadan o'chirildi.")
        else:
            await message.answer("❌ Bunday kodli kino topilmadi.")
    except Exception:
        await message.answer("⚠️ Ishlatish usuli: `/del 105`")

@dp.message(Command("vip"))
async def make_vip(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        target_id = int(message.text.split()[1])
        VIP_USERS.add(target_id)
        await message.answer(f"✅ `ID: {target_id}` foydalanuvchisiga VIP status berildi!")
    except Exception:
        await message.answer("⚠️ Ishlatish usuli: `/vip 8286159397`")

# ==================== 5. FOYDALANUVCHILAR UCHUN ====================

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    
    # Obuna tekshiruvi
    if not await check_all_subs(user_id):
        await message.answer(
            "👋 Assalomu alaykum!\n\n"
            "Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling va **'Obunani tekshirish'** tugmasini bosing:",
            reply_markup=get_sub_keyboard()
        )
        return

    status = "⭐ VIP Obunachi" if user_id in VIP_USERS else ("👨‍💻 Admin" if user_id == ADMIN_ID else "👤 Oddiy foydalanuvchi")
    
    await message.answer(
        f"Assalomu alaykum, *{message.from_user.full_name}*!\n\n"
        f"Sizning kodingiz (ID): `{user_id}`\n"
        f"Sizning maqomingiz: *{status}*\n\n"
        "🎬 Kino ko'rish uchun *kino kodini* yuboring:"
    )

@dp.callback_query(F.data == "check_subscription")
async def check_sub_callback(call: CallbackQuery):
    if await check_all_subs(call.from_user.id):
        await call.message.delete()
        await call.message.answer("✅ Barcha kanallarga obunangiz tasdiqlandi!\n\n🎬 Endi kino kodini yuborishingiz mumkin.")
    else:
        await call.answer("❌ Siz hali barcha kanallarga obuna bo'lmadingiz!", show_alert=True)

@dp.message(F.text)
async def get_movie(message: types.Message):
    user_id = message.from_user.id
    code = message.text.strip()

    # Avval obunani tekshiramiz
    if not await check_all_subs(user_id):
        await message.answer(
            "⚠️ Kinoni ko'rish uchun avval ushbu kanallarga obuna bo'ling:",
            reply_markup=get_sub_keyboard()
        )
        return

    movies = load_movies()

    if code not in movies:
        await message.answer("❌ Bu kodda hali kino joylanmagan. Iltimos to'g'ri kodni kiriting.")
        return

    movie = movies[code]
    is_vip = (user_id in VIP_USERS) or (user_id == ADMIN_ID)

    if movie.get("is_premium") and not is_vip:
        await message.answer(
            f"🔒 *\"{movie['title']}\" kinosi faqat VIP obunachilar uchun!*\n\n"
            f"Sizning ID kodingiz: `{user_id}`\n\n"
            "VIP obuna sotib olish uchun adminga murojaat qiling."
        )
        return

    await message.answer_video(
        video=movie["file_id"],
        caption=f"🎬 *{movie['title']}*\n\nMaroqli hordiq chiqaring!"
    )

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
