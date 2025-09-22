import os
import secrets
import sqlite3
import json
import hashlib
import hmac
from datetime import datetime
from functools import wraps
from threading import Thread
from urllib.parse import quote, parse_qs, unquote_plus

from flask import Flask, render_template_string, send_from_directory, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename, safe_join
import telebot
from telebot.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# إعدادات البوت التليجرام - استخدم متغير بيئة آمن
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

# دالة لتحويل حجم الملف إلى صيغة قابلة للقراءة
def human_readable_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} GB"

# دالة لتنسيق التاريخ والوقت
def format_datetime(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def get_unique_filename(directory, original_name):
    base, ext = os.path.splitext(secure_filename(original_name))
    counter = 1
    while True:
        unique_name = f"{base}_{counter}{ext}" if counter > 1 else f"{base}{ext}"
        if not os.path.exists(os.path.join(directory, unique_name)):
            return unique_name
        counter += 1

# دالة للتحقق من بيانات Telegram WebApp
def verify_telegram_data(init_data):
    try:
        # تحليل البيانات
        parsed_data = parse_qs(init_data)
        data_dict = {}
        
        for key, values in parsed_data.items():
            if values:
                data_dict[key] = values[0]
        
        # استخراج الهاش
        received_hash = data_dict.get('hash', '')
        if not received_hash:
            return False
            
        # إنشاء سلسلة التحقق
        data_check_list = []
        for key in sorted(data_dict.keys()):
            if key != 'hash':
                data_check_list.append(f"{key}={data_dict[key]}")
        
        data_check_string = "\n".join(data_check_list)
        
        # إنشاء المفتاح السري
        secret_key = hmac.new(
            b"WebAppData", 
            TELEGRAM_BOT_TOKEN.encode(), 
            hashlib.sha256
        ).digest()
        
        # حساب الهاش
        calculated_hash = hmac.new(
            secret_key, 
            data_check_string.encode(), 
            hashlib.sha256
        ).hexdigest()
        
        return calculated_hash == received_hash
        
    except Exception as e:
        print(f"Error verifying Telegram data: {e}")
        return False

# إنشاء قاعدة بيانات للمستخدمين
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, 
                 telegram_id INTEGER UNIQUE, 
                 first_name TEXT, 
                 last_name TEXT, 
                 username TEXT, 
                 photo_url TEXT,
                 last_download TEXT,
                 download_count INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

# الحصول على معلومات المستخدم من قاعدة البيانات
def get_user_info(telegram_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
    user = c.fetchone()
    conn.close()
    return user

# حفظ معلومات المستخدم في قاعدة البيانات
def save_user_info(user_data):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    c.execute("SELECT * FROM users WHERE telegram_id=?", (user_data['id'],))
    existing_user = c.fetchone()
    
    if existing_user:
        c.execute('''UPDATE users SET 
                     first_name=?, last_name=?, username=?, photo_url=?
                     WHERE telegram_id=?''',
                 (user_data['first_name'], user_data['last_name'], 
                  user_data['username'], user_data['photo_url'], 
                  user_data['id']))
    else:
        c.execute('''INSERT INTO users 
                     (telegram_id, first_name, last_name, username, photo_url, download_count) 
                     VALUES (?, ?, ?, ?, ?, ?)''',
                 (user_data['id'], user_data['first_name'], 
                  user_data['last_name'], user_data['username'], 
                  user_data['photo_url'], 0))
    
    conn.commit()
    conn.close()

# تحديث إحصائيات التنزيل للمستخدم
def update_user_download(telegram_id, filename):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('''UPDATE users SET 
                 last_download=?, download_count=download_count+1 
                 WHERE telegram_id=?''',
              (now, telegram_id))
    conn.commit()
    conn.close()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    return response

template_protection_script = """
<script>
    document.addEventListener("contextmenu", function(event) {
        event.preventDefault();
    });

    document.onkeydown = function(e) {
        if (e.keyCode == 123) { // F12
            return false;
        }
        if (e.ctrlKey && e.shiftKey && e.keyCode == 73) { // Ctrl+Shift+I
            return false;
        }
        if (e.ctrlKey && e.keyCode == 85) { // Ctrl+U
            return false;
        }
    };
</script>
"""

def get_config_files():
    config_files = {}
    for config_type in CONFIG_TYPES:
        dir_path = os.path.join(DOWNLOAD_FOLDER, config_type)
        try:
            files = []
            for filename in os.listdir(dir_path):
                if not filename.endswith('.desc') and not filename.startswith('.'):
                    file_path = os.path.join(dir_path, filename)
                    if os.path.isfile(file_path):
                        desc_path = os.path.join(dir_path, f"{filename}.desc")
                        description = "لا يوجد وصف متاح"
                        if os.path.exists(desc_path):
                            try:
                                with open(desc_path, 'r', encoding='utf-8') as f:
                                    description = f.read().strip()
                            except:
                                description = "خطأ في قراءة الوصف"

                        size = human_readable_size(os.path.getsize(file_path))
                        mod_time = format_datetime(os.path.getmtime(file_path))

                        files.append({
                            'name': filename,
                            'size': size,
                            'mod_time': mod_time,
                            'description': description
                        })
            config_files[config_type] = files
        except FileNotFoundError:
            os.makedirs(dir_path, exist_ok=True)
            config_files[config_type] = []
    return config_files

@app.route('/')
def index():
    user_info = None
    init_data = request.args.get('tgWebAppData', '')
    
    if init_data:
        try:
            if verify_telegram_data(init_data):
                parsed_data = parse_qs(init_data)
                user_str = parsed_data.get('user', ['{}'])[0]
                
                try:
                    user_data = json.loads(user_str)
                except:
                    user_data = {
                        'id': int(parsed_data.get('id', [0])[0]),
                        'first_name': parsed_data.get('first_name', [''])[0],
                        'last_name': parsed_data.get('last_name', [''])[0],
                        'username': parsed_data.get('username', [''])[0]
                    }
                
                # حفظ في الجلسة
                session['telegram_id'] = user_data.get('id', 0)
                session['first_name'] = user_data.get('first_name', '')
                session['last_name'] = user_data.get('last_name', '')
                session['username'] = user_data.get('username', '')
                session['photo_url'] = f"https://api.dicebear.com/7.x/bottts/svg?seed={user_data.get('id', 'unknown')}"
                
                # الحصول من قاعدة البيانات
                user_db_info = get_user_info(user_data.get('id', 0))
                
                if user_db_info:
                    last_download = user_db_info[6] if user_db_info[6] else 'لم يقم بتنزيل'
                    download_count = user_db_info[7] if user_db_info[7] else 0
                else:
                    save_user_info({
                        'id': user_data.get('id', 0),
                        'first_name': user_data.get('first_name', ''),
                        'last_name': user_data.get('last_name', ''),
                        'username': user_data.get('username', ''),
                        'photo_url': session['photo_url']
                    })
                    last_download = 'لم يقم بتنزيل'
                    download_count = 0
                
                user_info = {
                    'id': user_data.get('id', 0),
                    'first_name': user_data.get('first_name', ''),
                    'last_name': user_data.get('last_name', ''),
                    'username': user_data.get('username', ''),
                    'photo_url': session['photo_url'],
                    'last_download': last_download,
                    'download_count': download_count
                }
                
        except Exception as e:
            print(f"Error processing Telegram data: {e}")

    # إذا لم تكن بيانات التليجرام متوفرة، تحقق من الجلسة
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

    # HTML template
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta name="theme-color" content="#0a192f">
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FREE INTERNET 🔐</title>
        <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <meta name="robots" content="noindex,nofollow">
        <style>
            :root {
                --primary: #ff6b00;
                --secondary: #8B4513;
                --dark: #1a1a1a;
                --light: #f8f9fa;
            }
            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }
            body {
                font-family: 'Cairo', sans-serif;
                background: linear-gradient(135deg, #0a192f 0%, #1a1a2e 50%, #16213e 100%);
                color: white;
                min-height: 100vh;
                padding: 20px;
                line-height: 1.6;
            }
            .container {
                max-width: 900px;
                margin: 0 auto;
                background: rgba(0, 0, 0, 0.8);
                border-radius: 20px;
                padding: 30px;
                box-shadow: 0 10px 30px rgba(255, 107, 0, 0.2);
                border: 1px solid rgba(255, 107, 0, 0.3);
                backdrop-filter: blur(10px);
            }
            .header {
                text-align: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 2px solid var(--primary);
            }
            .header h1 {
                font-size: 2.5rem;
                color: var(--primary);
                text-shadow: 0 0 10px rgba(255, 107, 0, 0.5);
                margin-bottom: 10px;
            }
            .avatar-section {
                text-align: center;
                margin: 30px 0;
            }
            .avatar {
                width: 120px;
                height: 120px;
                border-radius: 50%;
                border: 3px solid var(--primary);
                margin: 0 auto 15px;
                object-fit: cover;
            }
            .user-name {
                font-size: 1.4rem;
                color: orange;
                margin-bottom: 10px;
            }
            .user-stats {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
                margin: 20px 0;
            }
            .stat-card {
                background: rgba(255, 107, 0, 0.1);
                padding: 15px;
                border-radius: 10px;
                text-align: center;
                border: 1px solid rgba(255, 107, 0, 0.3);
            }
            .stat-value {
                font-size: 1.2rem;
                font-weight: bold;
                color: #ff8c00;
            }
            .file-select {
                margin: 30px 0;
            }
            .select-box {
                width: 100%;
                padding: 15px;
                border: 2px solid var(--primary);
                border-radius: 10px;
                background: rgba(0, 0, 0, 0.5);
                color: white;
                font-size: 1rem;
                cursor: pointer;
            }
            .file-list {
                margin-top: 20px;
                display: none;
            }
            .file-group {
                display: none;
                animation: fadeIn 0.5s ease;
            }
            .file-item {
                background: rgba(255, 107, 0, 0.1);
                border: 1px solid rgba(255, 107, 0, 0.3);
                border-radius: 10px;
                padding: 20px;
                margin: 15px 0;
                transition: transform 0.3s ease;
            }
            .file-item:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(255, 107, 0, 0.3);
            }
            .file-header {
                display: flex;
                justify-content: between;
                align-items: center;
                margin-bottom: 10px;
            }
            .file-meta {
                display: flex;
                justify-content: space-between;
                color: #ccc;
                font-size: 0.9rem;
                margin-bottom: 10px;
            }
            .file-description {
                background: rgba(76, 175, 80, 0.1);
                padding: 10px;
                border-radius: 5px;
                margin: 10px 0;
                border-left: 3px solid #4CAF50;
            }
            .download-btn {
                width: 100%;
                padding: 12px;
                background: linear-gradient(45deg, #ff6b00, #ff8c00);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 1rem;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            .download-btn:hover {
                background: linear-gradient(45deg, #ff8c00, #ff6b00);
                transform: scale(1.02);
            }
            .admin-btn {
                position: fixed;
                top: 20px;
                left: 20px;
                background: var(--primary);
                color: white;
                padding: 10px 15px;
                border-radius: 25px;
                text-decoration: none;
                z-index: 1000;
            }
            .music-btn {
                position: fixed;
                top: 20px;
                right: 20px;
                background: var(--primary);
                color: white;
                width: 50px;
                height: 50px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                z-index: 1000;
            }
            .telegram-section {
                text-align: center;
                margin: 40px 0 20px;
            }
            .telegram-btn {
                display: inline-flex;
                align-items: center;
                gap: 10px;
                background: #0088cc;
                color: white;
                padding: 12px 25px;
                border-radius: 25px;
                text-decoration: none;
                font-weight: bold;
                transition: all 0.3s ease;
            }
            .telegram-btn:hover {
                transform: scale(1.05);
                box-shadow: 0 5px 15px rgba(0, 136, 204, 0.4);
            }
            .copyright {
                text-align: center;
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid rgba(255, 107, 0, 0.3);
                color: #ccc;
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            @media (max-width: 768px) {
                .container {
                    padding: 20px;
                    margin: 10px;
                }
                .header h1 {
                    font-size: 2rem;
                }
                .admin-btn, .music-btn {
                    position: relative;
                    top: auto;
                    left: auto;
                    margin: 10px;
                    display: inline-block;
                }
            }
        </style>
        {{ protection_script|safe }}
    </head>
    <body>
        <div class="container">
            {% if not session.get('admin_logged_in') %}
            <a href="{{ url_for('admin_login') }}" class="admin-btn">
                <i class="fas fa-user-shield"></i> Admin Panel
            </a>
            {% endif %}
            
            <div class="music-btn" onclick="toggleMusic()">
                <i class="fas fa-music"></i>
            </div>

            <div class="header">
                <h1><i class="fas fa-globe"></i> FREE INTERNET 🔐</h1>
            </div>

            <div class="avatar-section">
                {% if user_info %}
                    <img src="{{ user_info.photo_url }}" alt="User Avatar" class="avatar">
                    <div class="user-name">
                        {{ user_info.first_name }} {{ user_info.last_name }}
                        {% if user_info.username %}(@{{ user_info.username }}){% endif %}
                    </div>
                    <div class="user-stats">
                        <div class="stat-card">
                            <div>عدد التنزيلات</div>
                            <div class="stat-value">{{ user_info.download_count }}</div>
                        </div>
                        <div class="stat-card">
                            <div>آخر تنزيل</div>
                            <div class="stat-value">{{ user_info.last_download }}</div>
                        </div>
                    </div>
                {% else %}
                    <img src="https://api.dicebear.com/7.x/bottts/svg?seed=guest" alt="Guest" class="avatar">
                    <div class="user-name">زائر</div>
                    <p>يجب فتح التطبيق من خلال بوت تليجرام لاستخدام الخدمة</p>
                {% endif %}
            </div>

            {% if user_info %}
            <div class="file-select">
                <select class="select-box" id="configType" onchange="showFiles()">
                    <option value="">اختر نوع التطبيق...</option>
                    {% for config_type in config_files %}
                        <option value="{{ config_type }}">{{ config_type }}</option>
                    {% endfor %}
                </select>
            </div>

            <div class="file-list" id="fileList">
                {% for config_type, files in config_files.items() %}
                    <div class="file-group" id="{{ config_type }}Group">
                        {% for file in files %}
                            <div class="file-item">
                                <div class="file-header">
                                    <strong>{{ file.name }}</strong>
                                </div>
                                <div class="file-meta">
                                    <span>الحجم: {{ file.size }}</span>
                                    <span>التاريخ: {{ file.mod_time }}</span>
                                </div>
                                <div class="file-description">
                                    {{ file.description }}
                                </div>
                                <button class="download-btn" onclick="downloadFile('{{ config_type }}', '{{ file.name }}')">
                                    <i class="fas fa-download"></i> تنزيل الملف
                                </button>
                            </div>
                        {% endfor %}
                    </div>
                {% endfor %}
            </div>
            {% endif %}

            <div class="telegram-section">
                <a href="https://t.me/dis102" target="_blank" class="telegram-btn">
                    <i class="fab fa-telegram"></i> انضم لقناتنا على تليجرام
                </a>
            </div>

            <div class="copyright">
                <p>© 2024 VPN Configs. جميع الحقوق محفوظة</p>
            </div>
        </div>

        <audio id="backgroundMusic" loop>
            <source src="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3" type="audio/mpeg">
        </audio>

        <script>
            function showFiles() {
                const selectedType = document.getElementById('configType').value;
                const groups = document.querySelectorAll('.file-group');
                
                groups.forEach(group => {
                    group.style.display = 'none';
                });
                
                if (selectedType) {
                    const selectedGroup = document.getElementById(selectedType + 'Group');
                    if (selectedGroup) {
                        selectedGroup.style.display = 'block';
                        document.getElementById('fileList').style.display = 'block';
                    }
                } else {
                    document.getElementById('fileList').style.display = 'none';
                }
            }

            function toggleMusic() {
                const music = document.getElementById('backgroundMusic');
                const icon = document.querySelector('.music-btn i');
                
                if (music.paused) {
                    music.play();
                    icon.className = 'fas fa-volume-up';
                } else {
                    music.pause();
                    icon.className = 'fas fa-music';
                }
            }

            function downloadFile(configType, fileName) {
                fetch(`/download/${configType}/${fileName}`)
                    .then(response => {
                        if (response.ok) {
                            alert('✅ تم طلب الملف، سيتم إرساله لك عبر البوت');
                            setTimeout(() => {
                                window.location.reload();
                            }, 2000);
                        } else {
                            alert('❌ حدث خطأ أثناء طلب الملف');
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        alert('❌ حدث خطأ في الاتصال');
                    });
            }

            // إظهار رسالة ترحيب
            setTimeout(() => {
                alert('🛡️ مرحبًا بك في خدمة VPN المجانية\n\nيمكنك تنزيل أفضل الإعدادات المجانية');
            }, 1000);
        </script>
    </body>
    </html>
    ''', user_info=user_info, config_files=config_files, protection_script=template_protection_script)

# بقية الرواتب (admin_login, admin_dashboard, etc.) تبقى كما هي مع تعديلات طفيفة
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if (username == ADMIN_CREDENTIALS['username'] and 
            password == ADMIN_CREDENTIALS['password']):
            session['admin_logged_in'] = True
            session.permanent = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('بيانات الدخول غير صحيحة!', 'error')
    
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Admin Login</title>
        <style>
            body {
                background: linear-gradient(135deg, #0a192f 0%, #1a1a2e 100%);
                font-family: 'Cairo', sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
            }
            .login-box {
                background: rgba(0, 0, 0, 0.8);
                padding: 40px;
                border-radius: 15px;
                border: 1px solid #ff6b00;
                width: 100%;
                max-width: 400px;
            }
            .login-box h2 {
                color: #ff6b00;
                text-align: center;
                margin-bottom: 30px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            .form-group label {
                display: block;
                margin-bottom: 5px;
                color: #fff;
            }
            .form-group input {
                width: 100%;
                padding: 12px;
                border: 1px solid #ff6b00;
                border-radius: 5px;
                background: rgba(255, 255, 255, 0.1);
                color: white;
            }
            .login-btn {
                width: 100%;
                padding: 12px;
                background: #ff6b00;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            }
        </style>
    </head>
    <body>
        <div class="login-box">
            <h2><i class="fas fa-lock"></i> Admin Login</h2>
            <form method="POST">
                <div class="form-group">
                    <label>Username:</label>
                    <input type="text" name="username" required>
                </div>
                <div class="form-group">
                    <label>Password:</label>
                    <input type="password" name="password" required>
                </div>
                <button type="submit" class="login-btn">Login</button>
            </form>
        </div>
    </body>
    </html>
    ''')

@app.route('/download/<config_type>/<path:filename>')
def download(config_type, filename):
    if 'telegram_id' not in session:
        return "يجب تسجيل الدخول أولاً", 403
    
    if config_type not in CONFIG_TYPES:
        return "نوع التكوين غير صالح", 400
    
    file_path = safe_join(DOWNLOAD_FOLDER, config_type, filename)
    if not os.path.exists(file_path):
        return "الملف غير موجود", 404
    
    try:
        # تحديث إحصائيات المستخدم
        update_user_download(session['telegram_id'], filename)
        
        # إرسال الملف عبر البوت
        with open(file_path, 'rb') as file:
            bot.send_document(
                session['telegram_id'], 
                file, 
                caption=f"📁 {filename}\n\nتم التنزيل بنجاح ✅"
            )
        
        return "تم إرسال الملف إلى حسابك في تليجرام", 200
        
    except Exception as e:
        print(f"Error sending file: {e}")
        return f"خطأ في إرسال الملف: {str(e)}", 500

@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        markup = InlineKeyboardMarkup()
        web_app_button = InlineKeyboardButton(
            "فتح التطبيق 🔓", 
            web_app=WebAppInfo(url="https://your-app-url.onrender.com")
        )
        markup.add(web_app_button)
        
        welcome_text = """
        🎉 أهلاً بك في بوت VPN المجاني!

        🔐 يمكنك من خلال هذا البوت:
        • تحميل إعدادات VPN مجانية
        • إعدادات خوادم عالية السرعة
        • تطبيقات متميزة مجانية

        📱 اضغط على الزر أدناه لفتح التطبيق:
        """
        
        bot.send_message(
            message.chat.id, 
            welcome_text, 
            reply_markup=markup,
            parse_mode='HTML'
        )
    except Exception as e:
        print(f"Bot error: {e}")

def run_bot():
    try:
        print("Starting Telegram bot...")
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"Bot polling error: {e}")
        # إعادة التشغيل بعد 10 ثواني في حال فشل
        import time
        time.sleep(10)
        run_bot()

# تشغيل البوت في خيط منفصل
try:
    bot_thread = Thread(target=run_bot, daemon=True)
    bot_thread.start()
    print("Bot thread started successfully")
except Exception as e:
    print(f"Error starting bot thread: {e}")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
