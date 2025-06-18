import os
import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
import pytz

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, filters
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
CHOOSING_LANGUAGE, LESSON_TEXT, LESSON_IMAGE, LESSON_DATETIME, LESSON_TOPIC, CONFIRM_LESSON = range(6)
EDIT_FIELD, EDIT_VALUE = range(6, 8)

# Timezone
LOCAL_TZ = pytz.timezone('Europe/Berlin')  # UTC+1

class StudyBotTranslations:
    """Bilingual translations for the bot"""
    
    TEXTS = {
        'en': {
            'welcome': '🎓 Welcome to Study Group Bot!\n\nPlease choose your language:',
            'language_selected': '🇬🇧 Language set to English!',
            'language_ar_selected': '🇸🇦 تم تعيين اللغة إلى العربية!',
            'send_lesson_text': '📝 Please send the lesson text:',
            'ask_image': '📷 Do you want to attach an image?\n\n✅ Yes - Send the image now\n❌ No - Type "skip"',
            'ask_datetime': '⏰ When should I post this lesson?\n\nFormat: YYYY-MM-DD HH:MM\nExample: 2025-07-01 08:00',
            'ask_topic_id': '📌 What is the topic ID (thread ID) where I should post this lesson?',
            'confirm_lesson': '✅ Lesson scheduled!\n\n📅 Date: {date}\n🕐 Time: {time}\n📍 Topic ID: {topic_id}\n\n📝 Preview:\n{text}',
            'lesson_saved': '💾 Lesson saved successfully!',
            'invalid_datetime': '❌ Invalid date/time format. Please use: YYYY-MM-DD HH:MM',
            'invalid_topic_id': '❌ Topic ID must be a number.',
            'no_lessons': '📭 No scheduled lessons found.',
            'lessons_list': '📚 Scheduled Lessons:\n\n',
            'lesson_item': '🔹 ID: {id}\n📅 {datetime}\n📍 Topic: {topic_id}\n📝 {preview}...\n\n',
            'lesson_deleted': '🗑️ Lesson deleted successfully!',
            'lesson_not_found': '❌ Lesson not found.',
            'choose_edit_field': '✏️ What would you like to edit?\n\n1️⃣ Text\n2️⃣ Date/Time\n3️⃣ Topic ID\n4️⃣ Image',
            'edit_text': '📝 Send the new lesson text:',
            'edit_datetime': '⏰ Send the new date and time (YYYY-MM-DD HH:MM):',
            'edit_topic': '📌 Send the new topic ID:',
            'edit_image': '📷 Send the new image or type "remove" to remove current image:',
            'lesson_updated': '✅ Lesson updated successfully!',
            'export_data': '💾 Here\'s your backup data:',
            'help_text': '''🤖 Study Group Bot Commands:

📚 Lesson Management:
/addlesson - Add a new scheduled lesson
/listlessons - View all scheduled lessons  
/deletelesson <id> - Delete a lesson
/editlesson <id> - Edit a lesson
/export - Export all lessons as backup

⚙️ Settings:
/language - Change language
/help - Show this help

🕐 Time Format: YYYY-MM-DD HH:MM (UTC+1)
📍 Topic ID: The thread ID from your group''',
            'cancel': 'Operation cancelled.',
        },
        'ar': {
            'welcome': '🎓 أهلاً بك في بوت مجموعة الدراسة!\n\nالرجاء اختيار لغتك:',
            'language_selected': '🇬🇧 تم تعيين اللغة إلى الإنجليزية!',
            'language_ar_selected': '🇸🇦 تم تعيين اللغة إلى العربية!',
            'send_lesson_text': '📝 الرجاء إرسال محتوى الدرس:',
            'ask_image': '📷 هل تريد إرفاق صورة؟\n\n✅ نعم - أرسل الصورة الآن\n❌ لا - اكتب "تخطي"',
            'ask_datetime': '⏰ متى يجب أن أنشر هذا الدرس؟\n\nالصيغة: YYYY-MM-DD HH:MM\nمثال: 2025-07-01 08:00',
            'ask_topic_id': '📌 ما هو معرف الموضوع (معرف المحادثة) الذي يجب أن أنشر فيه هذا الدرس؟',
            'confirm_lesson': '✅ تم جدولة الدرس!\n\n📅 التاريخ: {date}\n🕐 الوقت: {time}\n📍 معرف الموضوع: {topic_id}\n\n📝 معاينة:\n{text}',
            'lesson_saved': '💾 تم حفظ الدرس بنجاح!',
            'invalid_datetime': '❌ صيغة التاريخ والوقت غير صحيحة. الرجاء استخدام: YYYY-MM-DD HH:MM',
            'invalid_topic_id': '❌ معرف الموضوع يجب أن يكون رقماً.',
            'no_lessons': '📭 لا توجد دروس مجدولة.',
            'lessons_list': '📚 الدروس المجدولة:\n\n',
            'lesson_item': '🔹 المعرف: {id}\n📅 {datetime}\n📍 الموضوع: {topic_id}\n📝 {preview}...\n\n',
            'lesson_deleted': '🗑️ تم حذف الدرس بنجاح!',
            'lesson_not_found': '❌ الدرس غير موجود.',
            'choose_edit_field': '✏️ ماذا تريد أن تعدل؟\n\n1️⃣ النص\n2️⃣ التاريخ والوقت\n3️⃣ معرف الموضوع\n4️⃣ الصورة',
            'edit_text': '📝 أرسل النص الجديد للدرس:',
            'edit_datetime': '⏰ أرسل التاريخ والوقت الجديد (YYYY-MM-DD HH:MM):',
            'edit_topic': '📌 أرسل معرف الموضوع الجديد:',
            'edit_image': '📷 أرسل الصورة الجديدة أو اكتب "إزالة" لحذف الصورة الحالية:',
            'lesson_updated': '✅ تم تحديث الدرس بنجاح!',
            'export_data': '💾 إليك بيانات النسخ الاحتياطي:',
            'help_text': '''🤖 أوامر بوت مجموعة الدراسة:

📚 إدارة الدروس:
/addlesson - إضافة درس مجدول جديد
/listlessons - عرض جميع الدروس المجدولة
/deletelesson <id> - حذف درس
/editlesson <id> - تعديل درس
/export - تصدير جميع الدروس كنسخة احتياطية

⚙️ الإعدادات:
/language - تغيير اللغة
/help - عرض هذه المساعدة

🕐 صيغة الوقت: YYYY-MM-DD HH:MM (UTC+1)
📍 معرف الموضوع: معرف المحادثة من مجموعتك''',
            'cancel': 'تم إلغاء العملية.',
        }
    }

class StudyBot:
    def __init__(self):
        self.lessons_file = "lessons.json"
        self.users_file = "users.json"
        self.lessons: Dict[str, Any] = {}
        self.user_preferences: Dict[str, Dict] = {}
        self.load_data()
        
    def load_data(self):
        """Load lessons and user data from files"""
        try:
            if os.path.exists(self.lessons_file):
                with open(self.lessons_file, 'r', encoding='utf-8') as f:
                    self.lessons = json.load(f)
        except Exception as e:
            logger.error(f"Error loading lessons: {e}")
            self.lessons = {}
            
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    self.user_preferences = json.load(f)
        except Exception as e:
            logger.error(f"Error loading user preferences: {e}")
            self.user_preferences = {}
    
    def save_data(self):
        """Save lessons and user data to files"""
        try:
            with open(self.lessons_file, 'w', encoding='utf-8') as f:
                json.dump(self.lessons, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving lessons: {e}")
            
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_preferences, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving user preferences: {e}")
    
    def get_user_language(self, user_id: str) -> str:
        """Get user's preferred language"""
        return self.user_preferences.get(str(user_id), {}).get('language', 'en')
    
    def set_user_language(self, user_id: str, language: str):
        """Set user's preferred language"""
        user_id_str = str(user_id)
        if user_id_str not in self.user_preferences:
            self.user_preferences[user_id_str] = {}
        self.user_preferences[user_id_str]['language'] = language
        self.save_data()
    
    def get_text(self, user_id: str, key: str, **kwargs) -> str:
        """Get translated text for user"""
        lang = self.get_user_language(user_id)
        text = StudyBotTranslations.TEXTS[lang].get(key, key)
        if kwargs:
            text = text.format(**kwargs)
        return text
    
    def parse_datetime(self, datetime_str: str) -> Optional[datetime]:
        """Parse datetime string in UTC+1"""
        try:
            naive_dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
            local_dt = LOCAL_TZ.localize(naive_dt)
            return local_dt
        except ValueError:
            return None
    
    def add_lesson(self, lesson_data: Dict[str, Any]) -> str:
        """Add a new lesson and return its ID"""
        lesson_id = str(len(self.lessons) + 1)
        self.lessons[lesson_id] = lesson_data
        self.save_data()
        return lesson_id
    
    def delete_lesson(self, lesson_id: str) -> bool:
        """Delete a lesson by ID"""
        if lesson_id in self.lessons:
            del self.lessons[lesson_id]
            self.save_data()
            return True
        return False
    
    def update_lesson(self, lesson_id: str, field: str, value: Any) -> bool:
        """Update a specific field of a lesson"""
        if lesson_id in self.lessons:
            self.lessons[lesson_id][field] = value
            self.save_data()
            return True
        return False

# Initialize bot instance
study_bot = StudyBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start command - language selection"""
    keyboard = [
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎓 Welcome to Study Group Bot!\n\nPlease choose your language:\n\nأهلاً بك في بوت مجموعة الدراسة!\n\nالرجاء اختيار لغتك:",
        reply_markup=reply_markup
    )
    return CHOOSING_LANGUAGE

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle language selection"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    language = query.data.split('_')[1]  # lang_en -> en
    
    study_bot.set_user_language(user_id, language)
    
    if language == 'en':
        text = study_bot.get_text(user_id, 'language_selected')
    else:
        text = study_bot.get_text(user_id, 'language_ar_selected')
    
    await query.edit_message_text(text)
    
    # Show help after language selection
    help_text = study_bot.get_text(user_id, 'help_text')
    await query.message.reply_text(help_text)
    
    return ConversationHandler.END

async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Change language command"""
    keyboard = [
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇸🇦 العربية", callback_data="lang_ar")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    user_id = update.effective_user.id
    current_lang = study_bot.get_user_language(user_id)
    
    if current_lang == 'ar':
        text = "اختر لغتك:"
    else:
        text = "Choose your language:"
    
    await update.message.reply_text(text, reply_markup=reply_markup)
    return CHOOSING_LANGUAGE

async def add_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start adding a new lesson"""
    user_id = update.effective_user.id
    context.user_data['lesson'] = {}
    
    text = study_bot.get_text(user_id, 'send_lesson_text')
    await update.message.reply_text(text)
    return LESSON_TEXT

async def lesson_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive lesson text"""
    user_id = update.effective_user.id
    context.user_data['lesson']['text'] = update.message.text
    
    text = study_bot.get_text(user_id, 'ask_image')
    await update.message.reply_text(text)
    return LESSON_IMAGE

async def lesson_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive lesson image or skip"""
    user_id = update.effective_user.id
    
    if update.message.photo:
        # Get the largest photo
        photo = update.message.photo[-1]
        context.user_data['lesson']['image_file_id'] = photo.file_id
    elif update.message.text and update.message.text.lower() in ['skip', 'تخطي']:
        context.user_data['lesson']['image_file_id'] = None
    else:
        text = study_bot.get_text(user_id, 'ask_image')
        await update.message.reply_text(text)
        return LESSON_IMAGE
    
    text = study_bot.get_text(user_id, 'ask_datetime')
    await update.message.reply_text(text)
    return LESSON_DATETIME

async def lesson_datetime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive lesson datetime"""
    user_id = update.effective_user.id
    datetime_str = update.message.text
    
    parsed_dt = study_bot.parse_datetime(datetime_str)
    if not parsed_dt:
        text = study_bot.get_text(user_id, 'invalid_datetime')
        await update.message.reply_text(text)
        return LESSON_DATETIME
    
    context.user_data['lesson']['datetime'] = parsed_dt.isoformat()
    
    text = study_bot.get_text(user_id, 'ask_topic_id')
    await update.message.reply_text(text)
    return LESSON_TOPIC

async def lesson_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive lesson topic ID"""
    user_id = update.effective_user.id
    
    try:
        topic_id = int(update.message.text)
        context.user_data['lesson']['topic_id'] = topic_id
    except ValueError:
        text = study_bot.get_text(user_id, 'invalid_topic_id')
        await update.message.reply_text(text)
        return LESSON_TOPIC
    
    # Show confirmation
    lesson = context.user_data['lesson']
    dt = datetime.fromisoformat(lesson['datetime'])
    
    text = study_bot.get_text(
        user_id, 'confirm_lesson',
        date=dt.strftime('%Y-%m-%d'),
        time=dt.strftime('%H:%M'),
        topic_id=lesson['topic_id'],
        text=lesson['text'][:100]
    )
    await update.message.reply_text(text)
    
    # Save lesson
    lesson['user_id'] = user_id
    lesson['group_chat_id'] = context.bot_data.get('group_chat_id')  # Set this in group
    lesson_id = study_bot.add_lesson(lesson)
    
    saved_text = study_bot.get_text(user_id, 'lesson_saved')
    await update.message.reply_text(saved_text)
    
    return ConversationHandler.END

async def list_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all scheduled lessons"""
    user_id = update.effective_user.id
    
    if not study_bot.lessons:
        text = study_bot.get_text(user_id, 'no_lessons')
        await update.message.reply_text(text)
        return
    
    text = study_bot.get_text(user_id, 'lessons_list')
    
    for lesson_id, lesson in study_bot.lessons.items():
        dt = datetime.fromisoformat(lesson['datetime'])
        preview = lesson['text'][:50]
        
        item_text = study_bot.get_text(
            user_id, 'lesson_item',
            id=lesson_id,
            datetime=dt.strftime('%Y-%m-%d %H:%M'),
            topic_id=lesson['topic_id'],
            preview=preview
        )
        text += item_text
    
    await update.message.reply_text(text)

async def delete_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a lesson"""
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text("Usage: /deletelesson <id>")
        return
    
    lesson_id = context.args[0]
    
    if study_bot.delete_lesson(lesson_id):
        text = study_bot.get_text(user_id, 'lesson_deleted')
    else:
        text = study_bot.get_text(user_id, 'lesson_not_found')
    
    await update.message.reply_text(text)

async def export_lessons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export lessons as JSON backup"""
    user_id = update.effective_user.id
    
    export_data = {
        'lessons': study_bot.lessons,
        'export_date': datetime.now(LOCAL_TZ).isoformat()
    }
    
    text = study_bot.get_text(user_id, 'export_data')
    await update.message.reply_text(text)
    
    # Send as file
    import io
    json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
    json_file = io.BytesIO(json_str.encode('utf-8'))
    json_file.name = f'lessons_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    await update.message.reply_document(document=json_file)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message"""
    user_id = update.effective_user.id
    text = study_bot.get_text(user_id, 'help_text')
    await update.message.reply_text(text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel current operation"""
    user_id = update.effective_user.id
    text = study_bot.get_text(user_id, 'cancel')
    await update.message.reply_text(text)
    return ConversationHandler.END

async def check_and_send_lessons(context: ContextTypes.DEFAULT_TYPE):
    """Check for lessons to send and send them"""
    now = datetime.now(LOCAL_TZ)
    lessons_to_remove = []
    
    for lesson_id, lesson in study_bot.lessons.items():
        lesson_dt = datetime.fromisoformat(lesson['datetime'])
        
        # Check if it's time to send (within 1 minute)
        if abs((now - lesson_dt).total_seconds()) <= 60:
            try:
                # Send the lesson to the group
                chat_id = lesson.get('group_chat_id')
                if not chat_id:
                    # Fallback - you need to set your group chat ID
                    chat_id = os.getenv('GROUP_CHAT_ID')
                
                if lesson.get('image_file_id'):
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=lesson['image_file_id'],
                        caption=lesson['text'],
                        message_thread_id=lesson['topic_id']
                    )
                else:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=lesson['text'],
                        message_thread_id=lesson['topic_id']
                    )
                
                lessons_to_remove.append(lesson_id)
                logger.info(f"Sent lesson {lesson_id} to topic {lesson['topic_id']}")
                
            except Exception as e:
                logger.error(f"Error sending lesson {lesson_id}: {e}")
    
    # Remove sent lessons
    for lesson_id in lessons_to_remove:
        study_bot.delete_lesson(lesson_id)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors"""
    logger.error(f"Exception while handling an update: {context.error}")

def main():
    """Start the bot"""
    # Get bot token from environment variable
    token = os.getenv('BOT_TOKEN')
    if not token:
        raise ValueError("BOT_TOKEN environment variable is required")
    
    # Create application
    application = Application.builder().token(token).build()
    
    # Add conversation handler for adding lessons
    add_lesson_handler = ConversationHandler(
        entry_points=[CommandHandler('addlesson', add_lesson)],
        states={
            CHOOSING_LANGUAGE: [CallbackQueryHandler(language_callback, pattern='^lang_')],
            LESSON_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, lesson_text)],
            LESSON_IMAGE: [
                MessageHandler(filters.PHOTO, lesson_image),
                MessageHandler(filters.TEXT & ~filters.COMMAND, lesson_image)
            ],
            LESSON_DATETIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, lesson_datetime)],
            LESSON_TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, lesson_topic)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # Add language selection handler
    language_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), CommandHandler('language', change_language)],
        states={
            CHOOSING_LANGUAGE: [CallbackQueryHandler(language_callback, pattern='^lang_')],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # Add handlers
    application.add_handler(language_handler)
    application.add_handler(add_lesson_handler)
    application.add_handler(CommandHandler('listlessons', list_lessons))
    application.add_handler(CommandHandler('deletelesson', delete_lesson))
    application.add_handler(CommandHandler('export', export_lessons))
    application.add_handler(CommandHandler('help', help_command))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Schedule lesson checking every minute
    job_queue = application.job_queue
    job_queue.run_repeating(check_and_send_lessons, interval=60, first=10)
    
    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()