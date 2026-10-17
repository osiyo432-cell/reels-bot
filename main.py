import asyncio
import os
import http.server
import socketserver
import threading

PORT = int(os.environ.get("PORT", 10000))

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive and running!")

def run_server():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving dummy web server on port {PORT}")
        httpd.serve_forever()

threading.Thread(target=run_server, daemon=True).start() 
import yt_dlp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from google import genai

BOT_TOKEN = "8397481010:AAFZIhKRVaaGi5NHMYkIXTkRjQLCWdTsZb4"
GEMINI_API_KEY = "AQ.Ab8RN6LGwTMEjmjqj9B5SODzxwncrpeTR3JJ3hR8yYSI2OB2FA"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

video_info_store = {}

# Gemini so'rovlarini xavfsiz va qayta urinish bilan yuborish funksiyasi
async def query_gemini(prompt: str) -> str:
    for attempt in range(3):
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model='gemini-3.8-flash',
                contents=prompt,
            )
            return response.text
        except Exception as e:
            if "503" in str(e) and attempt < 2:
                await asyncio.sleep(2)
                continue
            return f"❌ AI xatosi: {e}"

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 Assalomu alaykum! Men **Reels AI Copilot** botman 🤖🎬\n\n"
        "Men nimalar qila olaman?\n"
        "1. 📥 **Instagram Reels yuklash:** Menga havola yuborsangiz, videoni yuklab beraman.\n"
        "2. 💡 **AI Ssenariy va Post:** Har qanday Reels uchun viral hooklar, ssenariy va tavsif tuzib beraman.\n"
        "3. 💬 ** AI Suhbat:** Menga istalgan savolingizni yozsangiz, xuddi Ai kabi javob beraman!"
    )

def download_instagram_video(url: str, output_path: str):
    ydl_opts = {
        'outtmpl': output_path,
        'format': 'mp4/bestvideo+bestaudio/best',
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get('title', 'Reels video')
        description = info.get('description', '')
        return title, description

@dp.message(F.text.regexp(r'https?://(www\.)?instagram\.com/[^\s]+'))
async def handle_instagram_link(message: Message):
    url = message.text.strip()
    status_msg = await message.answer("⏳ Video yuklanmoqda va tahlil qilinmoqda...")
    
    file_name = f"reels_{message.message_id}.mp4"
    
    try:
        loop = asyncio.get_event_loop()
        title, desc = await loop.run_in_executor(None, download_instagram_video, url, file_name)
        
        session_id = str(message.message_id)
        video_info_store[session_id] = {
            "title": title or "Reels",
            "desc": desc or title or "Reels video"
        }

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔥 3 xil Hook & Ssenariy", callback_data=f"ai_script:{session_id}"),
            ],
            [
                InlineKeyboardButton(text="📝 Post tavsifi & Xeshteglar", callback_data=f"ai_post:{session_id}"),
                InlineKeyboardButton(text="📊 Viral tahlil & Maslahat", callback_data=f"ai_tips:{session_id}")
            ]
        ])

        if os.path.exists(file_name):
            video_file = FSInputFile(file_name)
            await message.answer_video(
                video=video_file,
                caption="✅ Video muvaffaqiyatli yuklandi!\n\nAI tahlil yoki yangi ssenariy olish uchun quyidagi tugmalarni bosing:",
                reply_markup=keyboard
            )
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ Videoni yuklab bo‘lmadi. Havola ochiq ekanligini tekshiring.")
            
    except Exception as e:
        await status_msg.edit_text(f"❌ Xatolik yuz berdi: {e}")
        
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)

@dp.callback_query(F.data.startswith("ai_script:"))
async def generate_ai_script(callback: CallbackQuery):
    session_id = callback.data.split(":")[1]
    info = video_info_store.get(session_id, {"title": "Reels", "desc": "Trend video"})
    
    await callback.answer()
    wait_msg = await callback.message.reply("🎬 Ssenariy va hooklar ishlab chiqilmoqda...")

    prompt = (
        f"Mavzu: '{info['desc']}'. "
        f"Instagram Reels uchun o'zbek tilida mukammal ssenariy tuzib ber:\n"
        f"1. 3 xil kuchli Hook (Vizual, Matnli, Provokatsion).\n"
        f"2. 15-25 soniyalik kadrlar rejasi (harakatlar va ekrandagi yozuvlar bilan).\n"
        f"3. Fon musiqasi uslubi bo'yicha maslahat.\n"
        f"4. Izoh yozdiruvchi CTA."
    )
    
    result = await query_gemini(prompt)
    await wait_msg.edit_text(result)

@dp.callback_query(F.data.startswith("ai_post:"))
async def generate_ai_post(callback: CallbackQuery):
    session_id = callback.data.split(":")[1]
    info = video_info_store.get(session_id, {"title": "Reels", "desc": "Trend video"})
    
    await callback.answer()
    wait_msg = await callback.message.reply("✍️ Post matni tayyorlanmoqda...")

    prompt = (
        f"Mavzu: '{info['desc']}'. "
        f"Instagram uchun jalb qiluvchi sarlavha, qisqa qiziqarli matn, harakatga chaqiruv (CTA) "
        f"va 7 ta o'zbek auditoriyasiga mos trend xeshteg yozib ber."
    )
    
    result = await query_gemini(prompt)
    await wait_msg.edit_text(result)

@dp.callback_query(F.data.startswith("ai_tips:"))
async def generate_ai_tips(callback: CallbackQuery):
    await callback.answer()
    tips = (
        "📊 **Reelsni Trendga Chiqarish Bo‘yicha Maslahatlar:**\n\n"
        "1. **3 soniya qoidasi (Retention):** Dastlabki kadrlarda dinamik harakat yoki qiziq savol bering.\n"
        "2. **Dinamik kadrlar:** Har 2-3 soniyada rakurs yoki reja o‘zgarib tursin.\n"
        "3. **Loop effekti:** Oxirgi jumla boshiga ulanib ketadigan qilib montaj qiling.\n"
        "4. **Kommentariya:** Odamlar bahslashadigan yoki o‘z tajribasini yozadigan savol qoldiring."
    )
    await callback.message.reply(tips)

# Gemini bilan erkin suhbat handler'i
@dp.message(F.text & ~F.text.startswith("/"))
async def handle_general_chat(message: Message):
    if "instagram.com" in message.text:
        return

    wait_msg = await message.answer("🤔 O‘ylayapman...")
    result = await query_gemini(message.text)
    await wait_msg.edit_text(result)

async def main():
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
