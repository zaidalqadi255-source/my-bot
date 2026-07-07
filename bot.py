import os
import requests
from telegram import Update, ChatMember
from telegram.ext import Application, ChatMemberHandler, ContextTypes

# --- 1. CONFIGURATION ---
TELEGRAM_TOKEN = "8347518330:AAHp5I8rlfx6sgb51I59ktcF8acxBZTWRAo"
SIGHTENGINE_USER = "399304305"
SIGHTENGINE_SECRET = "ZBiC5s4SQJe4ZS9LpFkPkziHDNx93tDa"

# --- 2. MAIN LOGIC (CHANNEL VERSION - PERMANENT BAN) ---
async def handle_channel_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # التقاط إشعار الدخول الخفي الخاص بالقنوات
    chat_member_update = update.chat_member
    if not chat_member_update:
        return

    old_status = chat_member_update.old_chat_member.status
    new_status = chat_member_update.new_chat_member.status
    member = chat_member_update.new_chat_member.user

    # التأكد أن الشخص "دخل" فعلياً ولم يقم فقط بتغيير إعداداته
    was_member = old_status in [ChatMember.MEMBER, ChatMember.OWNER, ChatMember.ADMINISTRATOR, ChatMember.RESTRICTED]
    is_member = new_status in [ChatMember.MEMBER, ChatMember.RESTRICTED]

    if not was_member and is_member:
        print(f"\n--- DOORBELL: {member.first_name} just joined the CHANNEL! ---")
        
        # Rule A: Permanent Ban for users without a username
        if not member.username:
            print(f"Action: Banning {member.first_name} PERMANENTLY because they have NO username.")
            await context.bot.ban_chat_member(chat_id=chat_member_update.chat.id, user_id=member.id)
            return 
            
        # Rule B: Check for NSFW profile pictures
        print("Checking their profile picture...")
        user_profile_photos = await context.bot.get_user_profile_photos(member.id, limit=1)
        
        if user_profile_photos.total_count > 0:
            print("Picture found! Sending it to the AI for scanning...")
            photo = user_profile_photos.photos[0][-1]
            file = await context.bot.get_file(photo.file_id)
            
            file_path = f"{member.id}.jpg"
            await file.download_to_drive(file_path)
            
            with open(file_path, 'rb') as img:
                response = requests.post(
                    'https://api.sightengine.com/1.0/check.json',
                    files={'media': img},
                    data={
                        'models': 'nudity-2.0',
                        'api_user': SIGHTENGINE_USER,
                        'api_secret': SIGHTENGINE_SECRET
                    }
                )
            
            os.remove(file_path)
            result = response.json()
            
            if 'nudity' in result:
                sexual_activity = result['nudity'].get('sexual_activity', 0)
                sexual_display = result['nudity'].get('sexual_display', 0)
                erotica = result['nudity'].get('erotica', 0)
                
                print(f"AI Results:")
                print(f"- Sexual Activity: {sexual_activity}")
                print(f"- Sexual Display: {sexual_display}")
                print(f"- Erotica: {erotica}")
                
                if max(sexual_activity, sexual_display, erotica) > 0.5:
                    print(f"Action: Banning {member.first_name} PERMANENTLY for NSFW picture!")
                    await context.bot.ban_chat_member(chat_id=chat_member_update.chat.id, user_id=member.id)
                else:
                    print("Action: Picture is safe. Letting them stay.")
            else:
                print(f"AI Error: Something went wrong with Sightengine -> {result}")
        else:
            print("Action: User has no profile picture. Letting them stay.")

# --- 3. START THE BOT ---
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(ChatMemberHandler(handle_channel_member, ChatMemberHandler.CHAT_MEMBER))
    
    print("Bot is running and monitoring the CHANNEL gates...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
