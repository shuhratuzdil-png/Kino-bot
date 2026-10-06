import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

# ==================== 1. BOT VA SOZLAMALAR ====================
BOT_TOKEN = "8770001356:AAFzObBGaC_gHoEVY0AA1wUYR0Xtv6TrosM"
ADMIN_ID = 8286159397  # Sizning Telegram ID-ingiz

# ==================== 2. MAJBURIY OBUNA KANALLARI ====================
CHANNELS = [
    "@ochiqkanalim",
    "@dddduzd"
]

VIP_USERS = set()

# ==================== 3. KINOLAR BAZASI ====================
MOVIES_DB = {
    "101": {
        "type": "single",
        "title": "Forsaj 10 (Bepul)",
        "is_premium": False,
        "file_id": "AAMCAgADGQEAAS92s2rEnmt3CRZDurj34JuXHSl99T0CAAKnogACovUhSjFsOIJjmAv8AQAHbQADPQQ"
    },
    "102": {
        "type": "single",
        "title": "Avatar 2 (VIP Premium)",
        "is_premium": True,
        "file_id": "AAMCAgADGQEAAS92s2rEnmt3CRZDurj34JuXHSl99T0CAAKnogACovUhSjFsOIJjmAv8AQAHbQADPQQ"
    },
    "664": {
        "type": "serial",
        "title": "Merlin",
        "is_premium": False,
        "episodes": {
            "1": "AAMCAgADGQEAAS92s2rEnmt3CRZDurj34JuXHSl99T0CAAKnogACovUhSjFsOIJjmAv8AQAHbQADPQQ",
            "2": "AAMCAgADGQEAAS92s2rEnmt3CRZDurj34JuXHSl99T0CAAKnogACovUhSjFsOIJjmAv8AQAHbQADPQQ"
        }
    }
}

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()

# Barcha kanallarga obunani aniq tekshirish
async def check_all_subs(user_id: int) -> bool:
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ["creator", "administrator", "member"]:
                logging.info(f"Foydalanuvchi {user_id} {channel} kanalida yo'q. Status: {member.status}")
                return False
        except Exception as e:
            logging.error(f"Xatolik yuz berdi ({channel}): {e}")
            return False
    return True

# Obuna klaviaturasini yaratish
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

# /start buyrug'i
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    status = "⭐ VIP Obunachi" if user_id in VIP_USERS else "👤 Oddiy foydalanuvchi"
    
    await message.answer(
        f"Assalomu alaykum, *{message.from_user.full_name}*!\n\n"
        f"Sizning kodingiz (ID): `{user_id}`\n"
        f"Sizning maqomingiz: *{status}*\n\n"
        "🎬 Kino ko'rish uchun *kino kodini* yuboring (masalan: 101, 102 yoki 664):"
    )

# Admin uchun VIP berish
@dp.message(Command("vip"))
async def make_vip(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        target_id = int(message.text.split()[1])
        VIP_USERS.add(target_id)
        await message.answer(f"✅ `ID: {target_id}` foydalanuvchisiga VIP status berildi!")
        
        try:
            await bot.send_message(
                target_id, 
                "🎉 Sizga VIP status berildi! Endi siz barcha kinolarni majburiy obunasiz va cheklovlarsiz ko'rishingiz mumkin."
            )
        except Exception:
            pass
    except Exception:
        await message.answer("⚠️ Xato kiritdingiz! Buyruq shakli: `/vip 8286159397`")

# Obunani tekshirish tugmasi bosilganda
@dp.callback_query(F.data == "check_subscription")
async def check_sub_callback(call: CallbackQuery):
    if await check_all_subs(call.from_user.id):
        await call.message.delete()
        await call.message.answer("✅ Barcha kanallarga obunangiz tasdiqlandi! Endi kino kodini yuborishingiz mumkin.")
    else:
        await call.answer("❌ Siz hali barcha kanallarga obuna bo'lmadingiz! Har ikkala kanalga ham a'zo bo'ling.", show_alert=True)

# Kino kodini qabul qilish
@dp.message(F.text)
async def get_movie(message: types.Message):
    user_id = message.from_user.id
    code = message.text.strip()

    # Noto'g'ri kod kiritilganda
    if code not in MOVIES_DB:
        await message.answer("❌ Bu kodda hali kino joylanmagan. Iltimos to'g'ri kodni kiriting.")
        return

    movie = MOVIES_DB[code]
    is_vip = user_id in VIP_USERS

    # 1. VIP kino tekshiruvi
    if movie.get("is_premium") and not is_vip:
        await message.answer(
            f"🔒 *\"{movie['title']}\" kinosi faqat VIP obunachilar uchun!*\n\n"
            f"Sizning ID kodingiz: `{user_id}`\n\n"
            "VIP obuna sotib olish uchun adminga murojaat qiling."
        )
        return

    # 2. Majburiy obuna tekshiruvi (VIP foydalanuvchidan so'ralmaydi)
    if not is_vip and not await check_all_subs(user_id):
        await message.answer(
            "⚠️ Kinoni ko'rish uchun avval ushbu kanallarga obuna bo'ling:",
            reply_markup=get_sub_keyboard()
        )
        return

    # 3. Kinoni yuborish
    if movie["type"] == "single":
        await message.answer_video(
            video=movie["file_id"],
            caption=f"🎬 *{movie['title']}*\n\nMaroqli hordiq chiqaring!"
        )
    elif movie["type"] == "serial":
        buttons = []
        for ep_num in movie["episodes"].keys():
            buttons.append([InlineKeyboardButton(
                text=f"▶️ {ep_num}-qism", 
                callback_data=f"ep_{code}_{ep_num}"
            )])
        
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(
            f"📺 *{movie['title']}* seriali.\nKo'rmoqchi bo'lgan qismingizni tanlang:",
            reply_markup=kb
        )

# Serial qismiga bosilganda
@dp.callback_query(F.data.startswith("ep_"))
async def send_episode(call: CallbackQuery):
    _, code, ep_num = call.data.split("_")
    
    if code in MOVIES_DB and ep_num in MOVIES_DB[code]["episodes"]:
        file_id = MOVIES_DB[code]["episodes"][ep_num]
        title = MOVIES_DB[code]["title"]
        
        await call.answer(f"{ep_num}-qism yuklanmoqda...")
        await call.message.answer_video(
            video=file_id,
            caption=f"🎬 *{title}* — {ep_num}-qism"
        )

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
