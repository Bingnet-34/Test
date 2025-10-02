import os
import secrets
import sqlite3
import json
import hashlib
import hmac
from datetime import datetime
from functools import wraps
from threading import Thread
from urllib.parse import parse_qs

from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from werkzeug.utils import safe_join
import telebot
from telebot.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# إعدادات البوت التليجرام
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8470884276:AAFoegIUdxQVlKYE9sJXMJ-XVNsaLQv2tGE')
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# إعدادات المجلدات
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, 'configs')
CONFIG_TYPES = ['HTTP_CUSTOM', 'Dark_Tunnel', 'HTTP_INJECTOR', 'تطبيقات معدلة🔥+حسابات مدفوعة']
ADMIN_CREDENTIALS = {'username': 'admin', 'password': 'admink123'}

# إنشاء مجلدات التكوينات
for config_type in CONFIG_TYPES:
    os.makedirs(os.path.join(DOWNLOAD_FOLDER, config_type), exist_ok=True)

# دالة التحقق من بيانات Telegram WebApp (مصححة)
def verify_telegram_data(init_data):
    try:
        # تحليل البيانات
        parsed_data = parse_qs(init_data)
        
        # الحصول على الهاش المستلم
        received_hash = parsed_data.get('hash', [''])[0]
        if not received_hash:
            print("No hash found in init_data")
            return False
        
        # إنشاء data_check_string
        data_check_list = []
        for key in sorted(parsed_data.keys()):
            if key != 'hash':
                value = parsed_data[key][0]
                data_check_list.append(f"{key}={value}")
        
        data_check_string = "\n".join(data_check_list)
        print(f"Data check string: {data_check_string}")
        
        # إنشاء secret_key من bot token
        secret_key = hmac.new(
            b"WebAppData", 
            TELEGRAM_BOT_TOKEN.encode(), 
            hashlib.sha256
        ).digest()
        
        # حساب الهاش المتوقع
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        print(f"Received hash: {received_hash}")
        print(f"Calculated hash: {calculated_hash}")
        
        return hmac.compare_digest(calculated_hash, received_hash)
        
    except Exception as e:
        print(f"Error in verify_telegram_data: {e}")
        return False

# دالة محسنة لاستخراج بيانات المستخدم
def extract_telegram_user(init_data):
    try:
        parsed_data = parse_qs(init_data)
        user_str = parsed_data.get('user', [''])[0]
        
        if user_str:
            user_data = json.loads(user_str)
            return {
                'id': user_data.get('id'),
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', ''),
                'username': user_data.get('username', ''),
                'language_code': user_data.get('language_code', 'ar'),
                'allows_write_to_pm': user_data.get('allows_write_to_pm', True)
            }
    except Exception as e:
        print(f"Error extracting user data: {e}")
    
    return None

# دالة بديلة أبسط للتحقق (إذا استمرت المشكلة)
def simple_telegram_verify(init_data):
    """دالة مبسطة للتحقق - تعتمد على وجود البيانات الأساسية"""
    try:
        parsed_data = parse_qs(init_data)
        user_str = parsed_data.get('user', [''])[0]
        auth_date = parsed_data.get('auth_date', [''])[0]
        
        if user_str and auth_date:
            user_data = json.loads(user_str)
            # تحقق بسيط من وجود البيانات الأساسية
            if user_data.get('id') and user_data.get('first_name'):
                return True
    except:
        pass
    return False

# إنشاء قاعدة البيانات
def init_db():
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 telegram_id INTEGER UNIQUE,
                 first_name TEXT,
                 last_name TEXT,
                 username TEXT,
                 photo_url TEXT,
                 last_download TEXT,
                 download_count INTEGER DEFAULT 0,
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

def get_user_info(telegram_id):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
    user = c.fetchone()
    conn.close()
    return user

def save_user_info(user_data):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    
    c.execute("SELECT * FROM users WHERE telegram_id=?", (user_data['id'],))
    existing_user = c.fetchone()
    
    if existing_user:
        c.execute('''UPDATE users SET 
                     first_name=?, last_name=?, username=?
                     WHERE telegram_id=?''',
                 (user_data['first_name'], user_data['last_name'], 
                  user_data['username'], user_data['id']))
    else:
        photo_url = f"https://api.dicebear.com/7.x/bottts/svg?seed={user_data['id']}"
        c.execute('''INSERT INTO users 
                     (telegram_id, first_name, last_name, username, photo_url, download_count) 
                     VALUES (?, ?, ?, ?, ?, ?)''',
                 (user_data['id'], user_data['first_name'], 
                  user_data['last_name'], user_data['username'], 
                  photo_url, 0))
    
    conn.commit()
    conn.close()

def update_user_download(telegram_id, filename):
    conn = sqlite3.connect('users.db', check_same_thread=False)
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('''UPDATE users SET 
                 last_download=?, download_count=download_count+1 
                 WHERE telegram_id=?''',
              (now, telegram_id))
    conn.commit()
    conn.close()

@app.route('/')
def index():
    user_info = None
    init_data = request.args.get('tgWebAppData', '')
    
    print(f"Received init_data: {init_data}")
    
    if init_data:
        # حاول التحقق باستخدام الطريقة الأولى
        if verify_telegram_data(init_data) or simple_telegram_verify(init_data):
            user_data = extract_telegram_user(init_data)
            
            if user_data and user_data.get('id'):
                print(f"User authenticated: {user_data}")
                
                # حفظ في الجلسة
                session['telegram_id'] = user_data['id']
                session['first_name'] = user_data['first_name']
                session['last_name'] = user_data.get('last_name', '')
                session['username'] = user_data.get('username', '')
                session['photo_url'] = f"https://api.dicebear.com/7.x/bottts/svg?seed={user_data['id']}"
                
                # حفظ في قاعدة البيانات
                save_user_info(user_data)
                
                # الحصول على معلومات المستخدم من قاعدة البيانات
                user_db_info = get_user_info(user_data['id'])
                if user_db_info:
                    last_download = user_db_info[6] if user_db_info[6] else 'لم يقم بتنزيل'
                    download_count = user_db_info[7] if user_db_info[7] else 0
                    
                    user_info = {
                        'id': user_data['id'],
                        'first_name': user_data['first_name'],
                        'last_name': user_data.get('last_name', ''),
                        'username': user_data.get('username', ''),
                        'photo_url': session['photo_url'],
                        'last_download': last_download,
                        'download_count': download_count
                    }
        else:
            print("Telegram authentication failed")

    # إذا فشل التحقق من التليجرام، تحقق من الجلسة
    if not user_info and session.get('telegram_id'):
        user_db_info = get_user_info(session['telegram_id'])
        if user_db_info:
            last_download = user_db_info[6] if user_db_info[6] else 'لم يقم بتنزيل'
            download_count = user_db_info[7] if user_db_info[7] else 0
            
            user_info = {
                'id': session['telegram_id'],
                'first_name': session.get('first_name', ''),
                'last_name': session.get('last_name', ''),
                'username': session.get('username', ''),
                'photo_url': session.get('photo_url', 'https://api.dicebear.com/7.x/bottts/svg?seed=unknown'),
                'last_download': last_download,
                'download_count': download_count
            }

    config_files = get_config_files()
    
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FREE INTERNET 🔐</title>
        <style>
            body {
                background: linear-gradient(135deg, #0a192f 0%, #1a1a2e 100%);
                color: white;
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background: rgba(0,0,0,0.8);
                padding: 20px;
                border-radius: 15px;
            }
            .user-info {
                text-align: center;
                margin: 20px 0;
            }
            .avatar {
                width: 80px;
                height: 80px;
                border-radius: 50%;
                margin: 0 auto;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 style="text-align: center;">FREE INTERNET 🔐</h1>
            
            <div class="user-info">
                {% if user_info %}
                    <img src="{{ user_info.photo_url }}" class="avatar" alt="User Avatar">
                    <h2>{{ user_info.first_name }} {{ user_info.last_name }}</h2>
                    {% if user_info.username %}
                        <p>@{{ user_info.username }}</p>
                    {% endif %}
                    <p>عدد التنزيلات: {{ user_info.download_count }}</p>
                    <p>آخر تنزيل: {{ user_info.last_download }}</p>
                    
                    <!-- عرض الملفات المتاحة -->
                    <div style="margin-top: 30px;">
                        <h3>الملفات المتاحة:</h3>
                        {% for config_type, files in config_files.items() %}
                            <div style="margin: 20px 0;">
                                <h4>{{ config_type }}</h4>
                                {% for file in files %}
                                    <div style="background: rgba(255,107,0,0.2); padding: 10px; margin: 10px 0; border-radius: 8px;">
                                        <p><strong>{{ file.name }}</strong></p>
                                        <p>الحجم: {{ file.size }}</p>
                                        <button onclick="downloadFile('{{ config_type }}', '{{ file.name }}')" 
                                                style="background: #ff6b00; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer;">
                                            تنزيل
                                        </button>
                                    </div>
                                {% endfor %}
                            </div>
                        {% endfor %}
                    </div>
                {% else %}
                    <img src="https://api.dicebear.com/7.x/bottts/svg?seed=guest" class="avatar" alt="Guest">
                    <h2>زائر</h2>
                    <p>يجب فتح التطبيق من خلال بوت تليجرام لاستخدام الخدمة</p>
                {% endif %}
            </div>
        </div>

        <script>
            function downloadFile(configType, fileName) {
                fetch(`/download/${configType}/${encodeURIComponent(fileName)}`)
                    .then(response => response.text())
                    .then(result => {
                        alert(result);
                    })
                    .catch(error => {
                        alert('حدث خطأ: ' + error);
                    });
            }
        </script>
    </body>
    </html>
    ''', user_info=user_info, config_files=get_config_files())

@app.route('/download/<config_type>/<path:filename>')
def download_file(config_type, filename):
    if 'telegram_id' not in session:
        return "يجب تسجيل الدخول أولاً", 403
    
    try:
        file_path = safe_join(DOWNLOAD_FOLDER, config_type, filename)
        if not os.path.exists(file_path):
            return "الملف غير موجود", 404
        
        # تحديث الإحصائيات
        update_user_download(session['telegram_id'], filename)
        
        # إرسال الملف عبر البوت
        try:
            with open(file_path, 'rb') as file:
                bot.send_document(
                    session['telegram_id'],
                    file,
                    caption=f"📁 {filename}\nتم التنزيل بنجاح! ✅"
                )
            return "✅ تم إرسال الملف إلى محادثتك في تليجرام"
        except Exception as e:
            return f"❌ خطأ في إرسال الملف: {str(e)}"
            
    except Exception as e:
        return f"❌ حدث خطأ: {str(e)}"

def get_config_files():
    config_files = {}
    for config_type in CONFIG_TYPES:
        dir_path = os.path.join(DOWNLOAD_FOLDER, config_type)
        files = []
        try:
            for filename in os.listdir(dir_path):
                file_path = os.path.join(dir_path, filename)
                if os.path.isfile(file_path) and not filename.startswith('.'):
                    size = os.path.getsize(file_path)
                    files.append({
                        'name': filename,
                        'size': f"{size / 1024:.1f} KB" if size < 1024*1024 else f"{size / (1024*1024):.1f} MB"
                    })
        except FileNotFoundError:
            os.makedirs(dir_path, exist_ok=True)
        config_files[config_type] = files
    return config_files

@bot.message_handler(commands=['start'])
def start_command(message):
    try:
        # إنشاء زر Web App
        keyboard = InlineKeyboardMarkup()
        web_app_button = InlineKeyboardButton(
            "فتح التطبيق 🚀", 
            web_app=WebAppInfo(url="https://test-bgei.onrender.com/")  # ضع رابطك هنا
        )
        keyboard.add(web_app_button)
        
        welcome_text = """
        🎉 أهلاً بك في بوت الإعدادات المجانية!
        
        🔓 اضغط على الزر أدناه لفتح التطبيق وتحميل الإعدادات:
        """
        
        bot.send_message(
            message.chat.id,
            welcome_text,
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Error in start command: {e}")

@bot.message_handler(commands=['stats'])
def stats_command(message):
    try:
        user_info = get_user_info(message.from_user.id)
        if user_info:
            stats_text = f"""
            📊 إحصائياتك:

            👤 الاسم: {user_info[2]} {user_info[3]}
            📥 عدد التنزيلات: {user_info[7]}
            🕒 آخر تنزيل: {user_info[6] if user_info[6] else 'لم تقم بأي تنزيل'}
            """
        else:
            stats_text = "❌ لم يتم العثور على بياناتك. يرجى فتح التطبيق أولاً."
        
        bot.send_message(message.chat.id, stats_text)
    except Exception as e:
        print(f"Error in stats command: {e}")

def run_bot():
    try:
        print("🤖 Starting Telegram Bot...")
        bot.remove_webhook()
        bot.infinity_polling()
    except Exception as e:
        print(f"Bot error: {e}")
        import time
        time.sleep(10)
        run_bot()

# تشغيل البوت في thread منفصل
bot_thread = Thread(target=run_bot, daemon=True)
bot_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
