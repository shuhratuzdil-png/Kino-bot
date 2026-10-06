import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

# ==================== SOZLAMALAR ====================
BOT_TOKEN = "AAFzObBGaC_gHoEVY0AA1wUYR0Xtv6TrosM"
CHANNEL_USERNAME = "@ochiqkanalim"  # Majburiy obuna kanali
ADMIN_ID = 8286159397  # O'zingizning Telegram ID raqamingizni yozing

# FOYDALANUVCHILAR BAZASI (VIP statuslarini saqlash uchun)
VIP_USERS = set()  # VIP bo'lgan foydalanuvchilar Telegram ID-lari

# KINOLAR BAZASI
MOVIES_DB = {
    # 1. BEPUL KINO (101 kodi)
    "101": {
        "type": "single",
        "title": "Forsaj 10 (Bepul)",
        "is_premium": False,  # Bepul kino
        "file_id": "AAMCAgADGQEAAS92s2rEnmt3CRZDurj34JuXHSl99T0CAAKnogACovUhSjFsOIJjmAv8AQAHbQADPQQ"
    },
    
    # 2. PULLI / PREMIUM KINO (102 kodi)
    "102": {
        "type": "single",
        "title": "Avatar 2 (VIP Premium)",
        "is_premium": True,   # Pulli kino
        "file_id": "AAMCAgADGQEAAS92s2rEnmt3CRZDurj34JuXHSl99T0CAAKnogACovUhSjFsOIJjmAv8AQAHbQADPQQ"
    },
    
    # 3. SERIAL (664 kodi)
    "664": {
        "type": "serial",
        "title": "Merlin",
        "is_premium": False,  # Bepul serial
        "episodes": {
            "1": "AAMCAgADGQEAAS92s2rEnmt3CRZDurj34JuXHSl99T0CAAKnogACovUhSjFsOIJjmAv8AQAHbQADPQQ",
            "2": "AAMCAgADGQEAAS92s2rEnmt3CRZDurj34JuXHSl99T0CAAKnogACovUhSjFsOIJjmAv8AQAHbQADPQQ"
        }
    }
}
# ====================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Majburiy obunani tekshirish funksiyasi
async def check_sub(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception:
        return False

# Obuna klaviaturasi
def get_sub_keyboard():
    channel_link = CHANNEL_USERNAME.replace("@", "")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{channel_link}")],
        [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_subscription")]
    ])

# /start buyrug'i
@dp.message(CommandStart())
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    status = "⭐ VIP Obunachi" if user_id in VIP_USERS else "👤 Oddiy foydalanuvchi"
    
    await message.answer(
        f"Assalomu alaykum, {message.from_user.full_name}!\n\n"
        f"Sizning kodingiz (ID): `{user_id}`\n"
        f"Sizning maqomingiz: **{status}**\n\n"
        "🎬 Kino ko'rish uchun **kino kodini** yuboring (masalan: 101, 102 yoki 664):"
    )

# Admin uchun foydalanuvchini VIP qilish buyrug'i: /vip 123456789
@dp.message(Command("vip"))
async def make_vip(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        target_id = int(message.text.split()[1])
        VIP_USERS.add(target_id)
        await message.answer(f"✅ `ID: {target_id}` foydalanuvchisiga VIP status berildi!")
        
        try:
            await bot.send_message(target_id, "🎉 Sizga VIP status berildi! Endi barcha pulli kinolarni ko'rishingiz va majburiy obunasiz foydalanishingiz mumkin.")
        except:
            pass
    except Exception:
        await message.answer("⚠️ Xato kiritdingiz! Buyruq shakli: `/vip 123456789`")

# Obunani tekshirish tugmasi
@dp.callback_query(F.data == "check_subscription")
async def check_sub_callback(call: CallbackQuery):
    if await check_sub(call.from_user.id):
        await call.message.delete()
        await call.message.answer("✅ Obunangiz tasdiqlandi. Endi kino kodini yuborishingiz mumkin.")
    else:
        await call.answer("❌ Siz hali kanalimizga obuna bo'lmadingiz!", show_alert=True)

# Kino kodini qabul qilish va tekshirish
@dp.message(F.text)
async def get_movie(message: types.Message):
    user_id = message.from_user.id
    code = message.text.strip()

    if code not in MOVIES_DB:
        await message.answer("❌ Bunday kodli kino topilmadi. Kodni qayta tekshirib yuboring.")
        return

    movie = MOVIES_DB[code]
    is_vip = user_id in VIP_USERS

    # 1. PULLI KINO TEKSHIRUVI
    if movie.get("is_premium") and not is_vip:
        await message.answer(
            f"🔒 **\"{movie['title']}\" kinosi faqat VIP obunachilar uchun!**\n\n"
            "VIP obuna sotib olish uchun adminga muloqotga chiqing.\n"
            f"Sizning ID kodingiz: `{user_id}`\n\n"
            "👨‍💻 Admin: @admin_username"
        )
        return

    # 2. MAJBURIY OBUNA TEKSHIRUVI (VIP bo'lsa tekshirmaydi)
    if not is_vip and not await check_sub(user_id):
        await message.answer(
            "⚠️ Kinoni ko'rish uchun avval rasmiy kanalimizga obuna bo'ling:",
            reply_markup=get_sub_keyboard()
        )
        return

    # 3. KINONI YUBORISH
    if movie["type"] == "single":
        await message.answer_video(
            video=movie["file_id"],
            caption=f"🎬 **{movie['title']}**\n\nMaroqli hordiq chiqaring!"
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
            f"📺 **{movie['title']}** seriali.\nKo'rmoqchi bo'lgan qismingizni tanlang:",
            reply_markup=kb
        )

# Serial qismi bosilganda
@dp.callback_query(F.data.startswith("ep_"))
async def send_episode(call: CallbackQuery):
    _, code, ep_num = call.data.split("_")
    
    if code in MOVIES_DB and ep_num in MOVIES_DB[code]["episodes"]:
        file_id = MOVIES_DB[code]["episodes"][ep_num]
        title = MOVIES_DB[code]["title"]
        
        await call.answer(f"{ep_num}-qism yuklanmoqda...")
        await call.message.answer_video(
            video=file_id,
            caption=f"🎬 **{title}** — {ep_num}-qism"
        )

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
