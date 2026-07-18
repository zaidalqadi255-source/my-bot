import os
import requests
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, ChatMember
from telegram.ext import Application, ChatMemberHandler, ContextTypes
from langdetect import detect

# --- حط أرقامك السرية هون بين علامات التنصيص ---
TELEGRAM_TOKEN = "التوكن_تبع_تيليجرام_هون"
SIGHTENGINE_API_USER = "رقم_اليوزر_تبع_sightengine"
SIGHTENGINE_API_SECRET = "الرقم_السري_تبع_sightengine"
# -----------------------------------------------

# خادم ويب وهمي عشان Render و UptimeRobot يضلوا شايفين البوت شغال
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is running!")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    def log_message(self, format, *args):
        pass # إخفاء سجلات الخادم عشان ما تزعجنا

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    print(f"Dummy web server started on port {port}")
    server.serve_forever()

async def check_image_with_sightengine(image_url: str) -> bool:
    """بفحص الصورة عن طريق موقع Sightengine"""
    params = {
        'models': 'nudity-2.0',
        'api_user': SIGHTENGINE_API_USER,
        'api_secret': SIGHTENGINE_API_SECRET,
        'url': image_url
    }
    try:
        r = requests.get('https://api.sightengine.com/1.0/check.json', params=params)
        data = r.json()
        if data.get('status') == 'success':
            nudity = data.get('nudity', {})
            if nudity.get('sexual_activity', 0) > 0.5 or nudity.get('sexual_display', 0) > 0.5 or nudity.get('erotica', 0) > 0.5:
                return True
    except Exception as e:
        print(f"Error checking image: {e}")
    return False

async def handle_channel_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مراقب القناة: يفحص أي عضو جديد بيدخل"""
    result = update.chat_member
    if not result:
        return
    
    chat = result.chat
    new_status = result.new_chat_member.status
    old_status = result.old_chat_member.status
    user = result.new_chat_member.user
    
    # التأكد إن العضو دخل القناة للتو (تغيرت حالته إلى عضو)
    if new_status == ChatMember.MEMBER and old_status != ChatMember.MEMBER:
        print(f"New user detected: {user.first_name} (ID: {user.id})")
        try:
            # 1. الشرط الأول: يوزرنيم (إذا ما في يوزرنيم، بان)
            if not user.username:
                await context.bot.ban_chat_member(chat.id, user.id)
                print(f"Banned {user.id} - No username")
                return 

            # 2. الشرط الثاني: فحص البايو (تم عزله بأمان)
            try:
                user_info = await context.bot.get_chat(user.id)
                if user_info.bio:
                    bio_lang = detect(user_info.bio)
                    if bio_lang not in ['ar', 'en']:
                        await context.bot.ban_chat_member(chat.id, user.id)
                        print(f"Banned {user.id} - Bio language: {bio_lang}")
                        return
            except Exception as e:
                print(f"Bio check skipped for {user.id} (Telegram restriction)")
            
            # 3. الشرط الثالث: فحص الصورة الشخصية 
            photos = await context.bot.get_user_profile_photos(user.id)
            if photos.total_count > 0:
                photo = photos.photos[0][-1]
                file = await context.bot.get_file(photo.file_id)
                is_explicit = await check_image_with_sightengine(file.file_path)
                
                if is_explicit:
                    await context.bot.ban_chat_member(chat.id, user.id)
                    print(f"Banned {user.id} - Explicit profile picture")
                    
        except Exception as e:
            print(f"Error processing new member: {e}")

def main():
    # 1. تشغيل الخادم الوهمي في الخلفية
    t = Thread(target=run_dummy_server)
    t.daemon = True
    t.start()

    # 2. تشغيل البوت
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(ChatMemberHandler(handle_channel_member, ChatMemberHandler.CHAT_MEMBER))
    
    print("Bot and Web Server are running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
