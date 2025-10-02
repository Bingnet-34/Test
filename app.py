import os
import secrets
import sqlite3
import json
from datetime import datetime
from functools import wraps
from threading import Thread

from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
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

# إنشاء مجلدات التكوينات
for config_type in CONFIG_TYPES:
    os.makedirs(os.path.join(DOWNLOAD_FOLDER, config_type), exist_ok=True)

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

@app.route('/')
def index():
    # نعتمد على أن Telegram WebApp سيقوم بإرسال بيانات المستخدم عبر JavaScript
    return render_template_string('''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FREE INTERNET 🔐</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body {
            background: linear-gradient(135deg, #0a192f 0%, #1a1a2e 100%);
            color: white;
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            text-align: center;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: rgba(0,0,0,0.8);
            padding: 20px;
            border-radius: 15px;
        }
        .loading {
            font-size: 1.2rem;
            margin: 50px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="loading">
            ⏳ جاري التحميل والتحقق من الهوية...
        </div>
    </div>

    <script>
        // انتظر حتى يتم تهيئة Telegram WebApp
        Telegram.WebApp.ready();

        // احصل على بيانات المستخدم من Telegram WebApp
        const user = Telegram.WebApp.initDataUnsafe.user;

        if (user) {
            console.log('User data:', user);
            
            // أرسل بيانات المستخدم إلى الخادم
            fetch('/auth', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    id: user.id,
                    first_name: user.first_name,
                    last_name: user.last_name || '',
                    username: user.username || ''
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // إعادة التوجيه إلى الصفحة الرئيسية مع بيانات الجلسة
                    window.location.href = '/main';
                } else {
                    document.querySelector('.container').innerHTML = `
                        <h1>❌ خطأ في المصادقة</h1>
                        <p>${data.error || 'حدث خطأ غير معروف'}</p>
                    `;
                }
            })
            .catch(error => {
                document.querySelector('.container').innerHTML = `
                    <h1>❌ خطأ في الاتصال</h1>
                    <p>${error}</p>
                `;
            });
        } else {
            document.querySelector('.container').innerHTML = `
                <h1>❌ لم يتم العثور على بيانات المستخدم</h1>
                <p>يجب فتح التطبيق من خلال بوت تليجرام</p>
                <p>إذا كنت تستخدم المتصفح العادي، هذا التطبيق لن يعمل بشكل صحيح</p>
            `;
        }
    </script>
</body>
</html>
    ''')

@app.route('/auth', methods=['POST'])
def auth():
    try:
        user_data = request.get_json()
        
        if not user_data or 'id' not in user_data:
            return jsonify({'success': False, 'error': 'بيانات غير صالحة'})
        
        # حفظ في الجلسة
        session['telegram_id'] = user_data['id']
        session['first_name'] = user_data['first_name']
        session['last_name'] = user_data.get('last_name', '')
        session['username'] = user_data.get('username', '')
        session['photo_url'] = f"https://api.dicebear.com/7.x/bottts/svg?seed={user_data['id']}"
        
        # حفظ في قاعدة البيانات
        save_user_info(user_data)
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/main')
def main():
    user_info = None
    
    if session.get('telegram_id'):
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
    
    if not user_info:
        return redirect('/')
    
    config_files = get_config_files()
    
    return render_template_string('''
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#0a192f">
    <title>FREE INTERNET 🔐</title>
    <style>
        :root {
            --primary: #ff6b00;
            --dark: #0a192f;
            --light: #f8f9fa;
        }
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a192f 0%, #1a1a2e 100%);
            color: white;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: rgba(0, 0, 0, 0.8);
            border-radius: 20px;
            padding: 30px;
            border: 1px solid var(--primary);
            box-shadow: 0 10px 30px rgba(255, 107, 0, 0.2);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            color: var(--primary);
            font-size: 2.5rem;
            margin-bottom: 10px;
        }
        .user-section {
            text-align: center;
            margin: 30px 0;
        }
        .avatar {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            border: 3px solid var(--primary);
            margin: 0 auto 15px;
        }
        .user-name {
            font-size: 1.5rem;
            color: orange;
            margin-bottom: 10px;
        }
        .stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin: 20px 0;
        }
        .stat-card {
            background: rgba(255, 107, 0, 0.1);
            padding: 15px;
            border-radius: 10px;
            border: 1px solid rgba(255, 107, 0, 0.3);
        }
        .file-section {
            margin: 30px 0;
        }
        .config-type {
            margin: 20px 0;
        }
        .config-type h3 {
            color: var(--primary);
            margin-bottom: 15px;
            padding-bottom: 5px;
            border-bottom: 2px solid var(--primary);
        }
        .file-item {
            background: rgba(255, 107, 0, 0.1);
            border: 1px solid rgba(255, 107, 0, 0.3);
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
        }
        .file-name {
            font-weight: bold;
            margin-bottom: 5px;
        }
        .download-btn {
            background: linear-gradient(45deg, #ff6b00, #ff8c00);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            width: 100%;
            font-size: 1rem;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ FREE INTERNET 🔐</h1>
            <p>خدمة إعدادات VPN مجانية</p>
        </div>

        <div class="user-section">
            <img src="{{ user_info.photo_url }}" alt="Avatar" class="avatar">
            <div class="user-name">
                {{ user_info.first_name }} {{ user_info.last_name }}
                {% if user_info.username %}
                    <br><small>@{{ user_info.username }}</small>
                {% endif %}
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <div>عدد التنزيلات</div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #ff8c00;">
                        {{ user_info.download_count }}
                    </div>
                </div>
                <div class="stat-card">
                    <div>آخر تنزيل</div>
                    <div style="font-size: 1.1rem; color: #ff8c00;">
                        {{ user_info.last_download }}
                    </div>
                </div>
            </div>
        </div>

        <div class="file-section">
            <h2 style="text-align: center; margin-bottom: 30px; color: var(--primary);">
                📁 الملفات المتاحة للتحميل
            </h2>
            
            {% for config_type, files in config_files.items() %}
            <div class="config-type">
                <h3>🎯 {{ config_type }}</h3>
                {% if files %}
                    {% for file in files %}
                    <div class="file-item">
                        <div class="file-name">{{ file.name }}</div>
                        <div style="color: #ccc; font-size: 0.9rem; margin: 5px 0;">
                            الحجم: {{ file.size }}
                        </div>
                        <button class="download-btn" onclick="downloadFile('{{ config_type }}', '{{ file.name }}')">
                            ⬇️ تنزيل الملف
                        </button>
                    </div>
                    {% endfor %}
                {% else %}
                    <div style="text-align: center; padding: 20px; color: #ccc;">
                        لا توجد ملفات متاحة حالياً
                    </div>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>

    <script>
        function downloadFile(configType, fileName) {
            fetch(`/download/${configType}/${encodeURIComponent(fileName)}`)
                .then(response => {
                    if (response.ok) {
                        return response.text();
                    } else {
                        throw new Error('خطأ في الخادم');
                    }
                })
                .then(message => {
                    alert('✅ ' + message);
                    // تحديث الصفحة لعرض الإحصائيات المحدثة
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                })
                .catch(error => {
                    alert('❌ ' + error.message);
                });
        }

        // إظهار رسالة ترحيب
        setTimeout(() => {
            alert('🎉 أهلاً بك {{ user_info.first_name }}!\\n\\nيمكنك الآن تحميل الإعدادات المجانية');
        }, 1000);
    </script>
</body>
</html>
''', user_info=user_info, config_files=config_files)

@app.route('/download/<config_type>/<path:filename>')
def download_file(config_type, filename):
    if 'telegram_id' not in session:
        return "يجب تسجيل الدخول أولاً", 403
    
    if config_type not in CONFIG_TYPES:
        return "نوع التكوين غير صالح", 400
    
    try:
        file_path = safe_join(DOWNLOAD_FOLDER, config_type, filename)
        if not os.path.exists(file_path):
            return "الملف غير موجود", 404
        
        # تحديث إحصائيات المستخدم
        update_user_download(session['telegram_id'], filename)
        
        # إرسال الملف عبر البوت
        try:
            with open(file_path, 'rb') as file:
                bot.send_document(
                    session['telegram_id'],
                    file,
                    caption=f"📁 {filename}\n\nتم التنزيل بنجاح! ✅\n\nشكراً لاستخدامك خدمتنا 🚀"
                )
            return "تم إرسال الملف إلى محادثتك في تليجرام"
        except Exception as e:
            return f"خطأ في إرسال الملف: {str(e)}"
            
    except Exception as e:
        return f"حدث خطأ: {str(e)}"

@bot.message_handler(commands=['start'])
def start_command(message):
    try:
        # إنشاء زر Web App
        keyboard = InlineKeyboardMarkup()
        
        # استخدم رابط التطبيق الحقيقي هنا - تأكد من تغييره!
        web_app_url = "https://test-bgei.onrender.com/"  # ⚠️ غير هذا بالرابط الحقيقي
        
        web_app_button = InlineKeyboardButton(
            "🚀 فتح التطبيق", 
            web_app=WebAppInfo(url=web_app_url)
        )
        keyboard.add(web_app_button)
        
        welcome_text = """
        🎉 أهلاً بك في بوت الإعدادات المجانية!

        🔓 من خلال هذا البوت يمكنك:
        • تحميل إعدادات VPN مجانية
        • الحصول على تطبيقات متميزة
        • خوادم سريعة ومستقرة

        📱 اضغط على الزر أدناه لفتح التطبيق والبدء:
        """
        
        bot.send_message(
            message.chat.id,
            welcome_text,
            reply_markup=keyboard
        )
        
        print(f"Sent WebApp button to user {message.from_user.id}")
        
    except Exception as e:
        print(f"Error in start command: {e}")

@bot.message_handler(commands=['stats'])
def stats_command(message):
    try:
        user_info = get_user_info(message.from_user.id)
        if user_info:
            stats_text = f"""
            📊 إحصائياتك الشخصية:

            👤 الاسم: {user_info[2]} {user_info[3]}
            📧 المستخدم: @{user_info[4] if user_info[4] else 'لا يوجد'}
            📥 عدد التنزيلات: {user_info[7]}
            🕒 آخر تنزيل: {user_info[6] if user_info[6] else 'لم تقم بأي تنزيل بعد'}

            🔓 استمر في استخدام التطبيق لتحميل المزيد!
            """
        else:
            stats_text = """
            ❌ لم نعثر على بياناتك!
            
            🔧 الحل:
            1. اضغط على زر 'فتح التطبيق' 
            2. سجل الدخول تلقائياً
            3. عد هنا وشاهد إحصائياتك
            """
        
        bot.send_message(message.chat.id, stats_text)
    except Exception as e:
        print(f"Error in stats command: {e}")

def run_bot():
    try:
        print("🤖 Starting Telegram Bot...")
        # احصل على معلومات البوت
        bot_info = bot.get_me()
        print(f"✅ Bot @{bot_info.username} is running!")
        
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ Bot error: {e}")
        import time
        time.sleep(10)
        run_bot()

# تشغيل البوت في thread منفصل
try:
    bot_thread = Thread(target=run_bot, daemon=True)
    bot_thread.start()
    print("✅ Bot thread started successfully")
except Exception as e:
    print(f"❌ Error starting bot thread: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
