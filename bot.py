import os
import requests
from telegram import Update, ChatMember
from telegram.ext import Application, ChatMemberHandler, ContextTypes
from langdetect import detect, LangDetectException

# --- حط أرقامك السرية هون بين علامات التنصيص ---
TELEGRAM_TOKEN = "8347518330:AAHp5I8rlfx6sgb51I59ktcF8acxBZTWRAo"
SIGHTENGINE_API_USER = "399304305"
SIGHTENGINE_API_SECRET = "ZBiC5s4SQJe4ZS9LpFkPkziHDNx93tDa"
# -----------------------------------------------

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
    """مراقب القناة: يفحص أي عضو جديد بيدخل للقناة"""
    result = update.chat_member
    if not result:
        return
    
    chat = result.chat
    new_status = result.new_chat_member.status
    old_status = result.old_chat_member.status
    user = result.new_chat_member.user
    
    if new_status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR] and old_status not in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR]:
        try:
            # 1. الشرط الأول: يوزرنيم (إذا ما في يوزرنيم، بان)
            if not user.username:
                await context.bot.ban_chat_member(chat.id, user.id)
                print(f"Banned user {user.id} - No username")
                return 

            # 2. الشرط الثاني: فحص البايو (آمن الآن ولن يعطل البوت)
            try:
                user_info = await context.bot.get_chat(user.id)
                if user_info.bio:
                    bio_lang = detect(user_info.bio)
                    if bio_lang not in ['ar', 'en']:
                        await context.bot.ban_chat_member(chat.id, user.id)
                        print(f"Banned user {user.id} - Bio language: {bio_lang}")
                        return
            except Exception:
                # إذا تيليجرام رفض يعطينا البايو، بنكمل بصمت لفحص الصورة
                pass
            
            # 3. الشرط الثالث: فحص الصورة الشخصية 
            photos = await context.bot.get_user_profile_photos(user.id)
            if photos.total_count > 0:
                photo = photos.photos[0][-1]
                file = await context.bot.get_file(photo.file_id)
                is_explicit = await check_image_with_sightengine(file.file_path)
                
                if is_explicit:
                    await context.bot.ban_chat_member(chat.id, user.id)
                    print(f"Banned user {user.id} - Explicit profile picture")
                    
        except Exception as e:
            print(f"Error processing new channel member: {e}")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(ChatMemberHandler(handle_channel_member, ChatMemberHandler.CHAT_MEMBER))
    print("Bot is running with isolated Bio & Photo filters...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
