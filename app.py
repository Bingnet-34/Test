import os
import secrets
import sqlite3
import json
from datetime import datetime
from functools import wraps
from threading import Thread
from urllib.parse import quote

from flask import Flask, render_template_string, send_from_directory, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename, safe_join
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

# إنشاء قاعدة البيانات للمستخدمين
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
                     first_name=?, last_name=?, username=?, photo_url=?
                     WHERE telegram_id=?''',
                 (user_data['first_name'], user_data['last_name'], 
                  user_data['username'], user_data.get('photo_url', ''), 
                  user_data['id']))
    else:
        photo_url = user_data.get('photo_url', f"https://api.dicebear.com/7.x/bottts/svg?seed={user_data['id']}")
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
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    return response

template_protection_script = """
<script>
    document.addEventListener("contextmenu", function(event) {
        event.preventDefault();
    });

    document.onkeydown = function(e) {
        if (e.keyCode == 123) {
            return false;
        }
        if (e.ctrlKey && e.shiftKey && (e.keyCode == 73 || e.keyCode == 74)) {
            return false;
        }
        if (e.ctrlKey && e.keyCode == 85) {
            return false;
        }
    };
</script>
"""

@app.route('/')
def index():
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
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                text-align: center;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
            }
            .container {
                background: rgba(0,0,0,0.9);
                padding: 50px 30px;
                border-radius: 20px;
                max-width: 500px;
                border: 2px solid #ff6b00;
                box-shadow: 0 10px 30px rgba(255, 107, 0, 0.3);
            }
            .loading {
                font-size: 1.3rem;
                margin: 25px 0;
                color: #ff8c00;
            }
            .spinner {
                border: 5px solid rgba(255, 107, 0, 0.3);
                border-radius: 50%;
                border-top: 5px solid #ff6b00;
                width: 60px;
                height: 60px;
                animation: spin 1.5s linear infinite;
                margin: 0 auto;
            }
            .status {
                margin-top: 20px;
                padding: 15px;
                border-radius: 10px;
                background: rgba(255, 107, 0, 0.1);
                border: 1px solid rgba(255, 107, 0, 0.3);
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            h1 {
                color: #ff6b00;
                margin-bottom: 30px;
                font-size: 2.2rem;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛡️ FREE INTERNET 🔐</h1>
            <div class="spinner"></div>
            <div class="loading">🔄 جاري التحميل والتحقق من الهوية...</div>
            <div class="status" id="status">
                ⏳ يرجى الانتظار جاري معالجة طلبك...
            </div>
        </div>

        <script>
            // انتظر حتى يتم تهيئة Telegram WebApp
            Telegram.WebApp.ready();
            Telegram.WebApp.expand();

            // تحديث الحالة
            document.getElementById('status').innerHTML = '✅ تم تحميل Telegram WebApp<br>🔍 جاري استخراج بيانات المستخدم...';

            // احصل على بيانات المستخدم من Telegram WebApp
            const user = Telegram.WebApp.initDataUnsafe.user;

            if (user) {
                console.log('User data:', user);
                document.getElementById('status').innerHTML = '✅ تم العثور على بيانات المستخدم<br>📧 جاري تسجيل الدخول...';
                
                // إنشاء بيانات المستخدم مع الصورة الحقيقية إذا كانت متاحة
                const userData = {
                    id: user.id,
                    first_name: user.first_name,
                    last_name: user.last_name || '',
                    username: user.username || '',
                    photo_url: user.photo_url || `https://api.dicebear.com/7.x/avataaars/svg?seed=${user.id}`
                };

                // أرسل بيانات المستخدم إلى الخادم
                fetch('/auth', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(userData)
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('status').innerHTML = '✅ تم تسجيل الدخول بنجاح<br>🚀 جاري التوجيه...';
                        setTimeout(() => {
                            window.location.href = '/main';
                        }, 1000);
                    } else {
                        document.getElementById('status').innerHTML = 
                            '❌ خطأ في المصادقة<br>' + (data.error || 'حدث خطأ غير معروف');
                    }
                })
                .catch(error => {
                    document.getElementById('status').innerHTML = 
                        '❌ خطأ في الاتصال<br>' + error;
                });
            } else {
                document.getElementById('status').innerHTML = 
                    '❌ لم يتم العثور على بيانات المستخدم<br>⚠️ يجب فتح التطبيق من خلال بوت تليجرام';
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
        session['photo_url'] = user_data.get('photo_url', f"https://api.dicebear.com/7.x/avataaars/svg?seed={user_data['id']}")
        session.permanent = True
        
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
                'photo_url': session.get('photo_url', f"https://api.dicebear.com/7.x/avataaars/svg?seed={session['telegram_id']}"),
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
        <meta name="theme-color" content="#0a192f">
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FREE INTERNET 🔐</title>
        <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <meta name="robots" content="noindex,nofollow">
        <style>
            :root {
                --primary: #ff6b00;
                --secondary: #8B4513;
                --dark: #1a1a1a;
                --light: #f8f9fa;
                --success: #28a745;
                --warning: #ffc107;
                --danger: #dc3545;
            }
            
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
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
                background: rgba(0, 0, 0, 0.85);
                border-radius: 20px;
                padding: 25px;
                box-shadow: 0 15px 35px rgba(255, 107, 0, 0.25);
                border: 2px solid rgba(255, 107, 0, 0.4);
                backdrop-filter: blur(10px);
                position: relative;
            }
            
            .back-btn {
                position: absolute;
                top: 20px;
                left: 20px;
                background: var(--primary);
                color: white;
                padding: 12px 20px;
                border-radius: 25px;
                text-decoration: none;
                font-weight: bold;
                display: flex;
                align-items: center;
                gap: 8px;
                transition: all 0.3s ease;
                border: none;
                cursor: pointer;
                font-size: 14px;
            }
            
            .back-btn:hover {
                background: #ff5500;
                transform: translateX(-5px);
            }
            
            .admin-btn {
                position: absolute;
                top: 20px;
                right: 20px;
                background: var(--warning);
                color: #000;
                padding: 12px 20px;
                border-radius: 25px;
                text-decoration: none;
                font-weight: bold;
                display: flex;
                align-items: center;
                gap: 8px;
                transition: all 0.3s ease;
                font-size: 14px;
            }
            
            .admin-btn:hover {
                background: #e0a800;
                transform: translateX(5px);
            }
            
            .header {
                text-align: center;
                margin: 40px 0 30px;
                padding-bottom: 20px;
                border-bottom: 2px solid var(--primary);
            }
            
            .header h1 {
                font-size: 2.8rem;
                color: var(--primary);
                text-shadow: 0 0 20px rgba(255, 107, 0, 0.5);
                margin-bottom: 10px;
                background: linear-gradient(45deg, #ff6b00, #ff8c00, #ff6b00);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-size: 200% auto;
                animation: gradientShift 3s ease-in-out infinite;
            }
            
            @keyframes gradientShift {
                0%, 100% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
            }
            
            .user-section {
                text-align: center;
                margin: 30px 0;
                padding: 25px;
                background: rgba(255, 107, 0, 0.1);
                border-radius: 15px;
                border: 1px solid rgba(255, 107, 0, 0.3);
            }
            
            .avatar-container {
                position: relative;
                display: inline-block;
                margin-bottom: 20px;
            }
            
            .avatar-img {
                width: 140px;
                height: 140px;
                border-radius: 50%;
                border: 4px solid var(--primary);
                transition: all 0.3s ease;
                object-fit: cover;
                box-shadow: 0 0 25px rgba(255, 107, 0, 0.4);
            }
            
            .avatar-img:hover {
                transform: scale(1.05);
                box-shadow: 0 0 35px rgba(255, 107, 0, 0.6);
            }
            
            .online-status {
                position: absolute;
                bottom: 10px;
                right: 10px;
                width: 20px;
                height: 20px;
                background: var(--success);
                border: 3px solid #0a192f;
                border-radius: 50%;
            }
            
            .user-name {
                font-size: 1.6rem;
                color: #ff8c00;
                margin-bottom: 8px;
                font-weight: 700;
            }
            
            .user-username {
                color: #ccc;
                font-size: 1.1rem;
                margin-bottom: 20px;
            }
            
            .user-stats {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 15px;
                margin: 25px 0;
            }
            
            .stat-card {
                background: rgba(255, 255, 255, 0.05);
                padding: 20px;
                border-radius: 12px;
                text-align: center;
                border: 1px solid rgba(255, 107, 0, 0.2);
                transition: all 0.3s ease;
            }
            
            .stat-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 20px rgba(255, 107, 0, 0.2);
            }
            
            .stat-value {
                font-size: 1.8rem;
                font-weight: bold;
                color: var(--primary);
                margin-bottom: 5px;
            }
            
            .stat-label {
                color: #ccc;
                font-size: 0.9rem;
            }
            
            .file-select {
                margin: 35px 0;
            }
            
            .select-box {
                width: 100%;
                padding: 18px 20px;
                border: 2px solid var(--primary);
                border-radius: 12px;
                background: rgba(0, 0, 0, 0.6);
                color: white;
                font-size: 1.1rem;
                cursor: pointer;
                transition: all 0.3s ease;
                font-family: 'Cairo', sans-serif;
            }
            
            .select-box:focus {
                outline: none;
                box-shadow: 0 0 0 3px rgba(255, 107, 0, 0.3);
            }
            
            .file-list {
                margin-top: 25px;
                display: none;
            }
            
            .file-group {
                display: none;
                animation: fadeInUp 0.6s ease;
            }
            
            @keyframes fadeInUp {
                from {
                    opacity: 0;
                    transform: translateY(20px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            .file-item {
                background: rgba(255, 107, 0, 0.08);
                border: 1px solid rgba(255, 107, 0, 0.3);
                border-radius: 15px;
                padding: 25px;
                margin: 18px 0;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }
            
            .file-item::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 3px;
                background: linear-gradient(90deg, var(--primary), transparent);
            }
            
            .file-item:hover {
                transform: translateY(-3px);
                box-shadow: 0 10px 25px rgba(255, 107, 0, 0.25);
            }
            
            .file-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                margin-bottom: 15px;
            }
            
            .file-name {
                font-size: 1.2rem;
                font-weight: 700;
                color: #ff8c00;
            }
            
            .file-meta {
                display: flex;
                justify-content: space-between;
                color: #aaa;
                font-size: 0.9rem;
                margin-bottom: 15px;
                padding: 10px 0;
                border-bottom: 1px solid rgba(255, 107, 0, 0.2);
            }
            
            .file-description {
                background: rgba(76, 175, 80, 0.1);
                padding: 15px;
                border-radius: 10px;
                margin: 15px 0;
                border-left: 4px solid var(--success);
                font-size: 0.95rem;
                line-height: 1.5;
            }
            
            .download-btn {
                width: 100%;
                padding: 16px;
                background: linear-gradient(135deg, var(--primary), #ff8c00);
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 1.1rem;
                font-weight: 700;
                cursor: pointer;
                transition: all 0.3s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 10px;
                position: relative;
                overflow: hidden;
            }
            
            .download-btn::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
                transition: left 0.5s;
            }
            
            .download-btn:hover::before {
                left: 100%;
            }
            
            .download-btn:hover {
                background: linear-gradient(135deg, #ff8c00, var(--primary));
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(255, 107, 0, 0.4);
            }
            
            .download-btn:disabled {
                background: #6c757d;
                cursor: not-allowed;
                transform: none;
            }
            
            .telegram-section {
                text-align: center;
                margin: 40px 0 25px;
                padding: 25px;
                background: rgba(0, 136, 204, 0.1);
                border-radius: 15px;
                border: 1px solid rgba(0, 136, 204, 0.3);
            }
            
            .telegram-btn {
                display: inline-flex;
                align-items: center;
                gap: 12px;
                background: linear-gradient(135deg, #0088cc, #00aced);
                color: white;
                padding: 16px 30px;
                border-radius: 25px;
                text-decoration: none;
                font-weight: bold;
                transition: all 0.3s ease;
                font-size: 1.1rem;
            }
            
            .telegram-btn:hover {
                transform: scale(1.05);
                box-shadow: 0 8px 25px rgba(0, 136, 204, 0.4);
            }
            
            .copyright {
                text-align: center;
                margin-top: 50px;
                padding-top: 25px;
                border-top: 1px solid rgba(255, 107, 0, 0.3);
                color: #aaa;
                font-size: 0.9rem;
            }
            
            /* أنماط الإشعارات */
            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 20px 25px;
                border-radius: 12px;
                color: white;
                font-weight: bold;
                z-index: 1000;
                display: flex;
                align-items: center;
                gap: 12px;
                box-shadow: 0 8px 25px rgba(0,0,0,0.3);
                transform: translateX(400px);
                transition: transform 0.4s ease;
                max-width: 350px;
            }
            
            .notification.show {
                transform: translateX(0);
            }
            
            .notification.success {
                background: linear-gradient(135deg, var(--success), #20c997);
                border-left: 5px solid #155724;
            }
            
            .notification.error {
                background: linear-gradient(135deg, var(--danger), #e83e8c);
                border-left: 5px solid #721c24;
            }
            
            .notification.info {
                background: linear-gradient(135deg, #17a2b8, #6f42c1);
                border-left: 5px solid #0c5460;
            }
            
            .notification.warning {
                background: linear-gradient(135deg, var(--warning), #fd7e14);
                border-left: 5px solid #856404;
            }
            
            .loading-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.8);
                display: none;
                justify-content: center;
                align-items: center;
                z-index: 9999;
                backdrop-filter: blur(5px);
            }
            
            .loading-spinner {
                width: 80px;
                height: 80px;
                border: 6px solid rgba(255, 107, 0, 0.3);
                border-top: 6px solid var(--primary);
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }
            
            .loading-text {
                color: white;
                margin-top: 20px;
                font-size: 1.2rem;
                text-align: center;
            }
            
            @media (max-width: 768px) {
                .container {
                    padding: 20px 15px;
                    margin: 10px;
                }
                
                .header h1 {
                    font-size: 2.2rem;
                }
                
                .back-btn, .admin-btn {
                    position: relative;
                    top: auto;
                    left: auto;
                    right: auto;
                    margin: 10px 5px;
                    display: inline-block;
                }
                
                .user-stats {
                    grid-template-columns: 1fr;
                }
                
                .avatar-img {
                    width: 120px;
                    height: 120px;
                }
                
                .file-item {
                    padding: 20px 15px;
                }
                
                .notification {
                    right: 10px;
                    left: 10px;
                    max-width: none;
                }
            }
        </style>
        {{ protection_script|safe }}
    </head>
    <body>
        <!-- زر الرجوع -->
        <button class="back-btn" onclick="goBack()">
            <i class="fas fa-arrow-right"></i> الرجوع
        </button>

        <!-- لوحة الإدارة -->
        {% if not session.admin_logged_in %}
        <a href="{{ url_for('admin_login') }}" class="admin-btn">
            <i class="fas fa-user-shield"></i> لوحة التحكم
        </a>
        {% endif %}

        <!-- نافذة التحميل -->
        <div class="loading-overlay" id="loadingOverlay">
            <div style="text-align: center;">
                <div class="loading-spinner"></div>
                <div class="loading-text" id="loadingText">جاري إرسال الملف...</div>
            </div>
        </div>

        <div class="container">
            <div class="header">
                <h1><i class="fas fa-shield-alt"></i> FREE INTERNET 🔐</h1>
                <p style="color: #ccc; font-size: 1.1rem;">خدمة إعدادات VPN مجانية وآمنة</p>
            </div>

            <!-- قسم معلومات المستخدم -->
            <div class="user-section">
                <div class="avatar-container">
                    <img src="{{ user_info.photo_url }}" alt="صورة المستخدم" class="avatar-img">
                    <div class="online-status"></div>
                </div>
                <div class="user-name">
                    {{ user_info.first_name }} {{ user_info.last_name }}
                </div>
                {% if user_info.username %}
                <div class="user-username">
                    @{{ user_info.username }}
                </div>
                {% endif %}
                
                <div class="user-stats">
                    <div class="stat-card">
                        <div class="stat-value">{{ user_info.download_count }}</div>
                        <div class="stat-label">عدد التنزيلات</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{{ user_info.last_download }}</div>
                        <div class="stat-label">آخر تنزيل</div>
                    </div>
                </div>
            </div>

            <!-- اختيار نوع الملف -->
            <div class="file-select">
                <select class="select-box" id="configType" onchange="showFiles()">
                    <option value="">📁 اختر نوع التطبيق...</option>
                    {% for config_type in config_files %}
                        <option value="{{ config_type }}">{{ config_type }}</option>
                    {% endfor %}
                </select>
            </div>

            <!-- قائمة الملفات -->
            <div class="file-list" id="fileList">
                {% for config_type, files in config_files.items() %}
                    <div class="file-group" id="{{ config_type }}Group">
                        {% for file in files %}
                            <div class="file-item">
                                <div class="file-header">
                                    <div class="file-name">
                                        <i class="fas fa-file-alt"></i> {{ file.name }}
                                    </div>
                                </div>
                                <div class="file-meta">
                                    <span><i class="fas fa-hdd"></i> الحجم: {{ file.size }}</span>
                                    <span><i class="fas fa-calendar"></i> التاريخ: {{ file.mod_time }}</span>
                                </div>
                                <div class="file-description">
                                    <i class="fas fa-info-circle"></i> {{ file.description }}
                                </div>
                                <button class="download-btn" onclick="downloadFile('{{ config_type }}', '{{ file.name }}')">
                                    <i class="fas fa-download"></i> تنزيل الملف
                                </button>
                            </div>
                        {% endfor %}
                    </div>
                {% endfor %}
            </div>

            <!-- قسم تليجرام -->
            <div class="telegram-section">
                <a href="https://t.me/dis102" target="_blank" class="telegram-btn">
                    <i class="fab fa-telegram"></i> انضم لقناتنا على تليجرام
                </a>
            </div>

            <!-- حقوق النشر -->
            <div class="copyright">
                <p>© <span id="currentYear"></span> FREE INTERNET. جميع الحقوق محفوظة</p>
                <p style="margin-top: 8px; font-size: 0.8rem; color: #888;">
                    تم التطوير بواسطة <span style="color: #ff6b00;">𝐊𝐡𝐚𝐥𝐢𝐥</span>
                </p>
            </div>
        </div>

        <script>
            // عرض السنة الحالية
            document.getElementById('currentYear').textContent = new Date().getFullYear();

            // دالة الرجوع
            function goBack() {
                window.history.back();
            }

            // دالة عرض الملفات
            function showFiles() {
                const selectedType = document.getElementById('configType').value;
                const groups = document.querySelectorAll('.file-group');
                const fileList = document.getElementById('fileList');
                
                groups.forEach(group => {
                    group.style.display = 'none';
                });
                
                if (selectedType) {
                    const selectedGroup = document.getElementById(selectedType + 'Group');
                    if (selectedGroup) {
                        selectedGroup.style.display = 'block';
                        fileList.style.display = 'block';
                        
                        // إظهار إشعار
                        showNotification(`تم عرض ملفات ${selectedType}`, 'success');
                    }
                } else {
                    fileList.style.display = 'none';
                }
            }

            // دالة تنزيل الملف
            async function downloadFile(configType, fileName) {
                const button = event.target;
                const originalText = button.innerHTML;
                
                try {
                    // إظهار نافذة التحميل
                    showLoading('جاري إرسال الملف...');
                    
                    // تعطيل الزر
                    button.disabled = true;
                    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> جاري الإرسال...';
                    
                    const response = await fetch(`/download/${configType}/${encodeURIComponent(fileName)}`);
                    const result = await response.text();
                    
                    if (response.ok) {
                        showNotification('✅ تم إرسال الملف بنجاح', 'success');
                        
                        // تحديث الصفحة بعد 2 ثانية
                        setTimeout(() => {
                            window.location.reload();
                        }, 2000);
                    } else {
                        throw new Error(result);
                    }
                } catch (error) {
                    console.error('Error:', error);
                    showNotification('❌ ' + error.message, 'error');
                } finally {
                    // إخفاء نافذة التحميل
                    hideLoading();
                    
                    // إعادة تفعيل الزر
                    setTimeout(() => {
                        button.disabled = false;
                        button.innerHTML = originalText;
                    }, 3000);
                }
            }

            // دالة إظهار الإشعارات
            function showNotification(message, type = 'info') {
                const notification = document.createElement('div');
                notification.className = `notification ${type}`;
                notification.innerHTML = `
                    <i class="fas fa-${getNotificationIcon(type)}"></i>
                    <span>${message}</span>
                `;
                
                document.body.appendChild(notification);
                
                // إظهار الإشعار
                setTimeout(() => notification.classList.add('show'), 100);
                
                // إخفاء الإشعار بعد 5 ثواني
                setTimeout(() => {
                    notification.classList.remove('show');
                    setTimeout(() => {
                        if (notification.parentNode) {
                            notification.parentNode.removeChild(notification);
                        }
                    }, 400);
                }, 5000);
            }

            // دالة الحصول على أيقونة الإشعار
            function getNotificationIcon(type) {
                const icons = {
                    'success': 'check-circle',
                    'error': 'exclamation-circle',
                    'warning': 'exclamation-triangle',
                    'info': 'info-circle'
                };
                return icons[type] || 'info-circle';
            }

            // دالة إظهار نافذة التحميل
            function showLoading(text = 'جاري التحميل...') {
                const overlay = document.getElementById('loadingOverlay');
                const loadingText = document.getElementById('loadingText');
                loadingText.textContent = text;
                overlay.style.display = 'flex';
            }

            // دالة إخفاء نافذة التحميل
            function hideLoading() {
                const overlay = document.getElementById('loadingOverlay');
                overlay.style.display = 'none';
            }

            // إظهار رسالة ترحيب
            window.addEventListener('load', function() {
                setTimeout(() => {
                    showNotification(`🎉 أهلاً بك ${'{{ user_info.first_name }}'}! يمكنك الآن تحميل الإعدادات المجانية`, 'info');
                }, 1500);
            });

            // تحسين تجربة المستخدم على الأجهزة المحمولة
            if (window.Telegram && Telegram.WebApp) {
                Telegram.WebApp.expand();
                Telegram.WebApp.enableClosingConfirmation();
            }
        </script>
    </body>
    </html>
    ''', user_info=user_info, config_files=config_files, protection_script=template_protection_script)

def get_config_files():
    config_files = {}
    for config_type in CONFIG_TYPES:
        dir_path = os.path.join(DOWNLOAD_FOLDER, config_type)
        try:
            files = []
            for filename in os.listdir(dir_path):
                if not filename.endswith('.desc'):
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
                caption=f"📁 {filename}\n\nتم التنزيل بنجاح! ✅\n\nشكراً لاستخدامك خدمتنا 🚀\n\n📊 إحصائياتك:\n• تم تنزيل هذا الملف\n• تابعنا للمزيد من الملفات المجانية"
            )
        
        return "تم إرسال الملف بنجاح إلى محادثتك في تليجرام"
        
    except Exception as e:
        return f"خطأ في إرسال الملف: {str(e)}"

# باقي الرواتب (لوحة التحكم) تبقى كما هي مع بعض التحسينات
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if (request.form['username'] == ADMIN_CREDENTIALS['username'] and
            request.form['password'] == ADMIN_CREDENTIALS['password']):
            session['admin_logged_in'] = True
            flash('تم تسجيل الدخول بنجاح!', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('بيانات الدخول غير صحيحة!', 'error')
    
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta name="theme-color" content="#0a192f">
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>تسجيل الدخول للإدارة</title>
        <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            body {
                font-family: 'Cairo', sans-serif;
                background: linear-gradient(135deg, #0a192f 0%, #1a1a2e 100%);
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                color: white;
            }
            .login-container {
                background: rgba(0, 0, 0, 0.9);
                padding: 40px;
                border-radius: 20px;
                max-width: 400px;
                width: 90%;
                box-shadow: 0 15px 35px rgba(255, 107, 0, 0.25);
                border: 2px solid rgba(255, 107, 0, 0.4);
                backdrop-filter: blur(10px);
            }
            .login-header {
                text-align: center;
                margin-bottom: 35px;
            }
            .login-header h2 {
                color: #ff6b00;
                font-size: 2rem;
                margin-bottom: 15px;
            }
            .login-header i {
                font-size: 3rem;
                color: #ff6b00;
                margin-bottom: 15px;
            }
            .form-group {
                margin-bottom: 25px;
            }
            .form-group label {
                display: block;
                margin-bottom: 10px;
                font-weight: bold;
                color: #ff8c00;
            }
            .form-group input {
                width: 100%;
                padding: 15px;
                border-radius: 10px;
                border: 2px solid #ff6b00;
                background: rgba(0, 0, 0, 0.6);
                color: white;
                font-size: 1rem;
                transition: all 0.3s ease;
            }
            .form-group input:focus {
                outline: none;
                box-shadow: 0 0 0 3px rgba(255, 107, 0, 0.3);
            }
            .login-btn {
                width: 100%;
                padding: 16px;
                background: linear-gradient(135deg, #ff6b00, #ff8c00);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 1.1rem;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s ease;
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 10px;
            }
            .login-btn:hover {
                background: linear-gradient(135deg, #ff8c00, #ff6b00);
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(255, 107, 0, 0.4);
            }
            .back-btn {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                color: #ff6b00;
                text-decoration: none;
                margin-top: 20px;
                transition: all 0.3s ease;
            }
            .back-btn:hover {
                color: #ff8c00;
                transform: translateX(-5px);
            }
            .alert {
                padding: 15px;
                border-radius: 10px;
                margin-top: 20px;
                text-align: center;
                background: rgba(220, 53, 69, 0.2);
                border: 1px solid rgba(220, 53, 69, 0.5);
                color: #f8d7da;
            }
            .alert.success {
                background: rgba(40, 167, 69, 0.2);
                border: 1px solid rgba(40, 167, 69, 0.5);
                color: #d4edda;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="login-header">
                <i class="fas fa-user-shield"></i>
                <h2>تسجيل الدخول للإدارة</h2>
            </div>
            <form method="POST">
                <div class="form-group">
                    <label for="username"><i class="fas fa-user"></i> اسم المستخدم</label>
                    <input type="text" id="username" name="username" required>
                </div>
                <div class="form-group">
                    <label for="password"><i class="fas fa-lock"></i> كلمة المرور</label>
                    <input type="password" id="password" name="password" required>
                </div>
                <button type="submit" class="login-btn">
                    <i class="fas fa-sign-in-alt"></i> دخول
                </button>
            </form>
            <a href="{{ url_for('main') }}" class="back-btn">
                <i class="fas fa-arrow-right"></i> العودة للتطبيق
            </a>
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert {{ category }}">
                            <i class="fas fa-{% if category == 'success' %}check-circle{% else %}exclamation-circle{% endif %}"></i> 
                            {{ message }}
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
        </div>
    </body>
    </html>
    ''')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    config_files = {}
    for config_type in CONFIG_TYPES:
        dir_path = os.path.join(DOWNLOAD_FOLDER, config_type)
        try:
            files = []
            for filename in os.listdir(dir_path):
                if not filename.endswith('.desc'):  # تجاهل ملفات الوصف
                    file_path = os.path.join(dir_path, filename)
                    if os.path.isfile(file_path):
                        # قراءة الوصف من ملف منفصل
                        desc_path = os.path.join(dir_path, f"{filename}.desc")
                        description = "لا يوجد وصف متاح"
                        if os.path.exists(desc_path):
                            try:
                                with open(desc_path, 'r', encoding='utf-8') as f:
                                    description = f.read()
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

    if request.method == 'POST':
        file = request.files['file']
        config_type = request.form['config_type']
        description = request.form.get('description', 'لا يوجد وصف متاح')

        if file and config_type in CONFIG_TYPES:
            original_name = file.filename
            safe_filename = os.path.basename(original_name)
            target_dir = os.path.join(DOWNLOAD_FOLDER, config_type)
            unique_name = get_unique_filename(target_dir, safe_filename)
            try:
                # حفظ الملف الرئيسي
                file.save(os.path.join(target_dir, unique_name))

                # حفظ الوصف في ملف منفصل
                desc_path = os.path.join(target_dir, f"{unique_name}.desc")
                with open(desc_path, 'w', encoding='utf-8') as f:
                    f.write(description)

                flash('تم رفع الملف ووصفه بنجاح ✅', 'success')

                # تحديث قائمة الملفات
                config_files[config_type].append({
                    'name': unique_name,
                    'size': human_readable_size(os.path.getsize(os.path.join(target_dir, unique_name))),
                    'mod_time': format_datetime(os.path.getmtime(os.path.join(target_dir, unique_name))),
                    'description': description
                })

            except Exception as e:
                flash(f'حدث خطأ أثناء رفع الملف: {str(e)}', 'error')

    return render_template_string('''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta name="theme-color" content="#0a192f">
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>لوحة التحكم</title>
        <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            body {
                font-family: 'Cairo', sans-serif;
                background: url('') no-repeat center center fixed;
                background-size: cover;
                margin: 0;
                color: white;
                background-color:#0a192f;
            }
            .admin-container {
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: rgba(0, 0, 0, 0.8);
                min-height: 100vh;
                backdrop-filter: blur(5px);
            }
            .admin-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 30px;
                padding-bottom: 15px;
                border-bottom: 1px solid rgba(255, 107, 0, 0.3);
            }
            .admin-header h1 {
                color: #ff6b00;
                font-size: 1.8rem;
                margin: 0;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .logout-btn {
                background: #ff4444;
                color: white;
                padding: 8px 15px;
                border-radius: 8px;
                text-decoration: none;
                font-weight: bold;
                display: flex;
                align-items: center;
                gap: 8px;
                transition: all 0.3s ease;
            }
            .logout-btn:hover {
                background: #cc0000;
                transform: translateY(-2px);
            }
            .upload-card {
                background: rgba(0, 0, 0, 0.5);
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 30px;
                border: 1px solid rgba(255, 107, 0, 0.2);
            }
            .upload-card h2 {
                color: #ff6b00;
                margin-top: 0;
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            .form-group label {
                display: block;
                margin-bottom: 8px;
                font-weight: bold;
            }
            .form-group select,
            .form-group input[type="file"] {
                width: 100%;
                padding: 12px 15px;
                border-radius: 8px;
                border: 2px solid #ff6b00;
                background: rgba(0, 0, 0, 0.5);
                color: white;
                font-size: 1rem;
                transition: all 0.3s ease;
            }
            .form-group select:focus {
                outline: none;
                box-shadow: 0 0 10px rgba(255, 107, 0, 0.5);
            }
            .form-group textarea {
                width: 100%;
                padding: 12px 15px;
                border-radius: 8px;
                border: 2px solid #ff6b00;
                background: rgba(0, 0, 0, 0.5);
                color: white;
                font-size: 1rem;
                resize: vertical;
                min-height: 100px;
            }
            .upload-btn {
                background: #ff6b00;
                color: white;
                padding: 12px 25px;
                border: none;
                border-radius: 8px;
                font-size: 1rem;
                font-weight: bold;
                cursor: pointer;
                transition: all 0.3s ease;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .upload-btn:hover {
                background: #ff5500;
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(255, 107, 0, 0.4);
            }
            .alert {
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                gap: 10px;
                animation: fadeIn 0.5s ease-out;
            }
            .alert-success {
                background: rgba(76, 175, 80, 0.2);
                border-left: 4px solid #4CAF50;
            }
            .alert-error {
                background: rgba(244, 67, 54, 0.2);
                border-left: 4px solid #f44336;
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .files-section {
                margin-top: 30px;
            }
            .config-type-section {
                background: rgba(0, 0, 0, 0.5);
                padding: 15px;
                border-radius: 10px;
                margin-bottom: 20px;
                border: 1px solid rgba(255, 107, 0, 0.2);
            }
            .config-type-section h3 {
                color: #ff6b00;
                margin-top: 0;
                margin-bottom: 10px;
            }
            .file-list {
                margin-top: 10px;
            }
            .file-item {
                padding: 15px;
                margin-bottom: 15px;
                background: rgba(255, 107, 0, 0.1);
                border-radius: 8px;
                border-left: 3px solid #ff6b00;
            }
            .file-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }
            .file-meta {
                display: flex;
                gap: 15px;
                font-size: 0.85em;
                color: #aaa;
            }
            .file-description {
                padding: 10px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                margin-top: 10px;
                font-size: 0.9em;
            }
            .delete-btn {
                background: #ff4444;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 6px;
                cursor: pointer;
                transition: all 0.3s ease;
                display: flex;
                align-items: center;
                gap: 5px;
            }
            .delete-btn:hover {
                background: #cc0000;
                transform: scale(1.05);
            }
            @media (max-width: 768px) {
                .admin-container {
                    padding: 15px;
                }
                .admin-header {
                    flex-direction: column;
                    gap: 15px;
                }
                .admin-header h1 {
                    font-size: 1.5rem;
                }
            }
        </style>
        {{ protection_script|safe }}
    </head>
    <body>
        <div class="admin-container">
            <div class="admin-header">
                <h1><i class="fas fa-cogs"></i> لوحة التحكم</h1>
                <a href="{{ url_for('admin_logout') }}" class="logout-btn">
                    <i class="fas fa-sign-out-alt"></i> تسجيل الخروج
                </a>
            </div>
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }}">
                            <i class="fas fa-{% if category == 'success' %}check-circle{% else %}exclamation-circle{% endif %}"></i>
                            {{ message }}
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            <div class="upload-card">
                <h2><i class="fas fa-cloud-upload-alt"></i> رفع ملف جديد</h2>
                <form method="POST" enctype="multipart/form-data">
                    <div class="form-group">
                        <label for="config-type"><i class="fas fa-list"></i> نوع التطبيق</label>
                        <select id="config-type" name="config_type" required>
                            <option value="" disabled selected>اختر النوع...</option>
                            {% for type in config_types %}
                                <option value="{{ type }}">{{ type }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="file"><i class="fas fa-file"></i> اختر الملف</label>
                        <input type="file" id="file" name="file" required>
                    </div>
                    <div class="form-group">
                        <label for="description"><i class="fas fa-file-alt"></i> وصف الملف</label>
                        <textarea id="description" name="description" placeholder="أدخل وصفاً للملف...">لا يوجد وصف متاح</textarea>
                    </div>
                    <button type="submit" class="upload-btn">
                        <i class="fas fa-upload"></i> رفع الملف
                    </button>
                </form>
            </div>
            <div class="files-section">
                <h2 style="color: #ff6b00; margin-top: 30px;"><i class="fas fa-files"></i> الملفات المرفوعة</h2>
                {% for config_type, files in config_files.items() %}
                    <div class="config-type-section">
                        <h3>{{ config_type }}</h3>
                        {% if files %}
                            <div class="file-list">
                                {% for file in files %}
                                    <div class="file-item">
                                        <div class="file-header">
                                            <div>
                                                <strong>{{ file.name }}</strong>
                                            </div>
                                            <form method="POST" action="{{ url_for('delete_file') }}" style="display: inline;">
                                                <input type="hidden" name="config_type" value="{{ config_type }}">
                                                <input type="hidden" name="filename" value="{{ file.name }}">
                                                <button type="submit" class="delete-btn" onclick="return confirm('هل أنت متأكد من حذف {{ file.name }}؟')">
                                                    <i class="fas fa-trash"></i> حذف
                                                </button>
                                            </form>
                                        </div>
                                        <div class="file-meta">
                                            <span>الحجم: {{ file.size }}</span>
                                            <span>التاريخ: {{ file.mod_time }}</span>
                                        </div>
                                        <div class="file-description">
                                            {{ file.description }}
                                        </div>
                                    </div>
                                {% endfor %}
                            </div>
                        {% else %}
                            <p>لا توجد ملفات في هذا القسم.</p>
                        {% endif %}
                    </div>
                {% endfor %}
            </div>
        </div>
    </body>
    </html>
    ''', config_types=CONFIG_TYPES, config_files=config_files, protection_script=template_protection_script)

@app.route('/admin/delete', methods=['POST'])
@admin_required
def delete_file():
    config_type = request.form.get('config_type')
    filename = request.form.get('filename')
    if not config_type or not filename:
        flash('بيانات غير صالحة', 'error')
        return redirect(url_for('admin_dashboard'))
    if config_type not in CONFIG_TYPES:
        flash('نوع التكوين غير صالح', 'error')
        return redirect(url_for('admin_dashboard'))
    file_path = os.path.join(DOWNLOAD_FOLDER, config_type, filename)
    desc_path = os.path.join(DOWNLOAD_FOLDER, config_type, f"{filename}.desc")

    if not os.path.exists(file_path):
        flash('الملف غير موجود', 'error')
        return redirect(url_for('admin_dashboard'))

    try:
        # حذف الملف الرئيسي
        os.remove(file_path)

        # حذف ملف الوصف إذا كان موجوداً
        if os.path.exists(desc_path):
            os.remove(desc_path)

        flash('تم حذف الملف ووصفه بنجاح', 'success')
    except Exception as e:
        flash(f'حدث خطأ أثناء الحذف: {str(e)}', 'error')

    return redirect(url_for('admin_dashboard'))
@app.route('/admin/logout')
@admin_required
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('تم تسجيل الخروج بنجاح', 'success')
    return redirect(url_for('admin_login'))

@bot.message_handler(commands=['start'])
def start_command(message):
    try:
        # التحقق من بيانات المستخدم
        user = message.from_user
        user_info = {
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name or '',
            'username': user.username or '',
            'photo_url': f"https://api.dicebear.com/7.x/avataaars/svg?seed={user.id}"
        }
        
        # حفظ المستخدم في قاعدة البيانات
        save_user_info(user_info)
        
        # إنشاء زر Web App
        keyboard = InlineKeyboardMarkup()
        
        # استخدم رابط التطبيق الحقيقي هنا
        web_app_url = "https://test-bgei.onrender.com"  # ⚠️ غير هذا بالرابط الحقيقي
        
        web_app_button = InlineKeyboardButton(
            "🚀 فتح التطبيق المجاني", 
            web_app=WebAppInfo(url=web_app_url)
        )
        keyboard.add(web_app_button)
        
        welcome_text = f"""
        🎉 أهلاً بك {user.first_name} في بوت الإعدادات المجانية!

        👤 **معلومات حسابك:**
        • الاسم: {user.first_name} {user.last_name or ''}
        • المستخدم: @{user.username or 'غير متوفر'}
        • رقم التعريف: {user.id}

        🔓 **المميزات المتاحة:**
        • تحميل إعدادات VPN مجانية
        • تطبيقات متميزة مجانية
        • خوادم سريعة ومستقرة
        • تحديثات دورية للملفات

        📱 **للبدء، اضغط على الزر أدناه لفتح التطبيق:**
        """
        
        bot.send_message(
            message.chat.id,
            welcome_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        print(f"✅ Sent WebApp button to user {user.id} ({user.first_name})")
        
    except Exception as e:
        print(f"❌ Error in start command: {e}")
        bot.send_message(message.chat.id, "❌ حدث خطأ أثناء تحميل البوت. يرجى المحاولة مرة أخرى.")

@bot.message_handler(commands=['stats'])
def stats_command(message):
    try:
        user_info = get_user_info(message.from_user.id)
        if user_info:
            stats_text = f"""
            📊 **إحصائياتك الشخصية**

            👤 **المعلومات الشخصية:**
            • الاسم: {user_info[2]} {user_info[3]}
            • المستخدم: @{user_info[4] if user_info[4] else 'غير متوفر'}
            • رقم التعريف: {user_info[1]}

            📥 **إحصائيات التنزيل:**
            • عدد التنزيلات: {user_info[7]}
            • آخر تنزيل: {user_info[6] if user_info[6] else 'لم تقم بأي تنزيل بعد'}

            🎯 **لتحميل المزيد من الملفات، استخدم الزر في الأعلى!**
            """
        else:
            stats_text = """
            ❌ **لم نعثر على بياناتك!**
            
            🔧 **لحل المشكلة:**
            1. اضغط على زر 'فتح التطبيق المجاني'
            2. سيتم تسجيل دخولك تلقائياً
            3. عد هنا وشاهد إحصائياتك
            
            📱 **أو أرسل /start لتحديث بياناتك**
            """
        
        bot.send_message(message.chat.id, stats_text, parse_mode='Markdown')
        
    except Exception as e:
        print(f"❌ Error in stats command: {e}")
        bot.send_message(message.chat.id, "❌ حدث خطأ أثناء جلب الإحصائيات.")

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """
    🆘 **مركز المساعدة**

    📋 **الأوامر المتاحة:**
    • /start - بدء استخدام البوت وعرض زر التطبيق
    • /stats - عرض إحصائياتك الشخصية
    • /help - عرض هذه الرسالة

    🔧 **استكشاف الأخطاء:**
    • إذا لم يعمل التطبيق، تأكد من فتحه من خلال الزر
    • للتحديث، أرسل /start مرة أخرى
    • للمساعدة الفورية، راسل الدعم الفني

    📞 **الدعم الفني:**
    @dis102 - قناة التليجرام الرسمية
    """
    
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

def run_bot():
    try:
        print("🤖 جاري تشغيل بوت التليجرام...")
        bot_info = bot.get_me()
        print(f"✅ تم تشغيل البوت بنجاح: @{bot_info.username}")
        print(f"🆔 رقم البوت: {bot_info.id}")
        print(f"👤 اسم البوت: {bot_info.first_name}")
        
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
        
    except Exception as e:
        print(f"❌ خطأ في تشغيل البوت: {e}")
        import time
        time.sleep(10)
        print("🔄 إعادة تشغيل البوت...")
        run_bot()

# تشغيل البوت في thread منفصل
try:
    bot_thread = Thread(target=run_bot, daemon=True)
    bot_thread.start()
    print("✅ تم تشغيل thread البوت بنجاح")
except Exception as e:
    print(f"❌ خطأ في تشغيل thread البوت: {e}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 جاري تشغيل التطبيق على المنفذ {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
