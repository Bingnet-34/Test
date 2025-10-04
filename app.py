import os
import secrets
import json
from datetime import datetime
from functools import wraps
from threading import Thread, Lock
from urllib.parse import parse_qs

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

# ملفات JSON للتخزين
USERS_JSON = os.path.join(BASE_DIR, 'users.json')
FILES_JSON = os.path.join(BASE_DIR, 'files.json')

# قفل للتعامل الآمن مع الملفات
json_lock = Lock()

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

# نظام إدارة المستخدمين المبسط والفعال
def init_json_storage():
    """تهيئة ملفات JSON إذا لم تكن موجودة"""
    with json_lock:
        if not os.path.exists(USERS_JSON):
            with open(USERS_JSON, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
        
        if not os.path.exists(FILES_JSON):
            with open(FILES_JSON, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)

def read_users():
    """قراءة بيانات المستخدمين من ملف JSON"""
    with json_lock:
        try:
            with open(USERS_JSON, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

def write_users(users_data):
    """كتابة بيانات المستخدمين إلى ملف JSON"""
    with json_lock:
        with open(USERS_JSON, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, ensure_ascii=False, indent=2)

def get_user_info(telegram_id):
    """الحصول على معلومات المستخدم"""
    users = read_users()
    return users.get(str(telegram_id))

def save_user_info(user_data):
    """حفظ معلومات المستخدم"""
    users = read_users()
    telegram_id = str(user_data['id'])
    
    if telegram_id not in users:
        users[telegram_id] = {
            'telegram_id': user_data['id'],
            'first_name': user_data['first_name'],
            'last_name': user_data.get('last_name', ''),
            'username': user_data.get('username', ''),
            'photo_url': user_data.get('photo_url', f"https://api.dicebear.com/7.x/bottts/svg?seed={user_data['id']}"),
            'last_download': None,
            'download_count': 0,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    else:
        # تحديث البيانات الأساسية وآخر تسجيل دخول
        users[telegram_id].update({
            'first_name': user_data['first_name'],
            'last_name': user_data.get('last_name', ''),
            'username': user_data.get('username', ''),
            'photo_url': user_data.get('photo_url', users[telegram_id].get('photo_url', f"https://api.dicebear.com/7.x/bottts/svg?seed={user_data['id']}")),
            'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    
    write_users(users)

def update_user_download(telegram_id, filename):
    """تحديث إحصائيات تنزيل المستخدم"""
    users = read_users()
    telegram_id_str = str(telegram_id)
    
    if telegram_id_str in users:
        users[telegram_id_str]['last_download'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        users[telegram_id_str]['download_count'] = users[telegram_id_str].get('download_count', 0) + 1
        write_users(users)

def get_all_users():
    """الحصول على جميع المستخدمين (للوحة الإدارة)"""
    return read_users()

# تهيئة التخزين
init_json_storage()

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

# نظام المصادقة المبسط والفعال
def validate_session():
    """التحقق من صحة جلسة المستخدم - مبسط"""
    telegram_id = session.get('telegram_id')
    
    if not telegram_id:
        return False
    
    # التحقق من أن المستخدم موجود في قاعدة البيانات
    user_info = get_user_info(telegram_id)
    if not user_info:
        return False
    
    return True

def get_current_user():
    """الحصول على بيانات المستخدم الحالي"""
    telegram_id = session.get('telegram_id')
    if not telegram_id:
        return None
    
    return get_user_info(telegram_id)

def create_secure_session(user_data):
    """إنشاء جلسة آمنة جديدة - مبسط"""
    # مسح أي جلسة موجودة أولاً
    session.clear()
    
    # حفظ بيانات الجلسة مباشرة باستخدام telegram_id كمفتاح
    session['telegram_id'] = user_data['id']
    session['first_name'] = user_data['first_name']
    session['last_name'] = user_data.get('last_name', '')
    session['username'] = user_data.get('username', '')
    session['photo_url'] = user_data.get('photo_url', f"https://api.dicebear.com/7.x/bottts/svg?seed={user_data['id']}")
    session['session_created'] = datetime.now().isoformat()
    session.permanent = True
    
    return True

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FREE INTERNET🔌</title>
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
                box-shadow: 0 10px 30px rgba(255, 107, 0, 0.1);
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
            <h1> FREE INTERNET🔌</h1>
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
                
                // إنشاء بيانات المستخدم
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
                        setTimeout(() => {
                            window.location.reload();
                        }, 3000);
                    }
                })
                .catch(error => {
                    document.getElementById('status').innerHTML = 
                        '❌ خطأ في الاتصال<br>' + error;
                    setTimeout(() => {
                        window.location.reload();
                    }, 3000);
                });
            } else {
                document.getElementById('status').innerHTML = 
                    '❌ لم يتم العثور على بيانات المستخدم<br>⚠️ يجب فتح التطبيق من خلال بوت تليجرام';
                
                setTimeout(() => {
                    window.location.reload();
                }, 3000);
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
        
        # التحقق من أن البيانات تحتوي على معرف التليجرام
        telegram_id = user_data['id']
        if not telegram_id:
            return jsonify({'success': False, 'error': 'معرف التليجرام مطلوب'})
        
        # إنشاء جلسة آمنة جديدة
        if not create_secure_session(user_data):
            return jsonify({'success': False, 'error': 'فشل في إنشاء الجلسة'})
        
        # حفظ/تحديث بيانات المستخدم في قاعدة البيانات
        save_user_info(user_data)
        
        return jsonify({
            'success': True, 
            'message': 'تم إنشاء الجلسة بنجاح',
            'telegram_id': telegram_id
        })
        
    except Exception as e:
        print(f"Error in auth: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/main')
def main():
    # التحقق من صحة الجلسة أولاً
    if not validate_session():
        print("Session validation failed, redirecting to index")
        session.clear()
        return redirect('/')
    
    # الحصول على بيانات المستخدم الحالي
    user_info = get_current_user()
    
    if not user_info:
        print("User info not found, redirecting to index")
        session.clear()
        return redirect('/')
    
    print(f"User {user_info['telegram_id']} accessed main page")
    
    config_files = get_config_files()
    
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta name="theme-color" content="#0a192f">
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>FREE INTERNET DZ</title>
        <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <meta name="robots" content="noindex,nofollow">
        <style>
            :root {
                --primary: #ff6b00;
                --secondary: #8B4513;
                --dark: #1a1a1a;
                --light: #f8f9fa;
            }
            body {
                font-family: 'Cairo', sans-serif;
                background-size: cover;
                color: white;
                background-color: #0a192f;
                margin: 0;
                padding: 0;
                min-height: 100vh;
                margin-top: 30px;
            }
            .container {
                position: relative;
                flex-direction: column;
                align-items: center;
                max-width: 800px;
                margin: 30px auto;
                padding: 20px;
                background: rgba(0, 0, 0, 0.7);
                border-radius: 15px;
                border: 1px solid rgba(255, 107, 0, 0.5);
            }
            .header {
                font-size: 2.5rem;
                font-weight: bold;
                text-align: center;
                margin-bottom: 20px;
                color: var(--primary);
                animation: glow 1.2s ease-in-out infinite alternate;
            }
            @keyframes glow {
                from { text-shadow: 0 0 5px var(--primary); }
                to { text-shadow: 0 0 15px var(--primary), 0 0 20px var(--primary); }
            }
            .user-section {
                text-align: center;
                margin: 20px 0;
            }
            .avatar-img {
                width: 120px;
                height: 120px;
                border-radius: 50%;
                border: 3px solid var(--primary);
                transition: all 0.3s ease;
                object-fit: cover;
            }
            .avatar-name {
                font-size: 1.5rem;
                font-weight: bold;
                margin-top: 10px;
                color: orange;
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
                border: 1px solid rgba(255, 107, 0, 0.3);
                text-align: center;
            }
            .stat-value {
                font-size: 1.2rem;
                font-weight: bold;
                color: #ff8c00;
            }
            .file-select {
                margin: 20px 0;
                width: 100%;
            }
            .file-select select {
                width: 100%;
                padding: 12px 15px;
                border-radius: 8px;
                border: 2px solid var(--primary);
                background-color: rgba(0, 0, 0, 0.5);
                color: white;
                font-size: 1rem;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            .file-list {
                margin-top: 20px;
                display: none;
                width: 100%;
            }
            .file-list-group {
                display: none;
                animation: fadeIn 0.5s ease-out;
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .file-item {
                padding: 15px;
                margin: 15px 0;
                border-radius: 8px;
                display: flex;
                flex-direction: column;
                transition: all 0.3s ease;
                border-left: 4px solid var(--primary);
                box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
                background: rgba(244, 67, 54, 0.2);
            }
            .file-item:hover {
                transform: scale(1.02);
            }
            .file-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                width: 100%;
            }
            .file-info {
                display: flex;
                flex-direction: column;
                gap: 5px;
                flex-grow: 1;
            }
            .file-meta {
                display: flex;
                justify-content: space-between;
                font-size: 0.85em;
                color: #aaa;
                margin-top: 5px;
            }
            .file-description {
                margin-top: 12px;
                padding: 10px;
                background: rgba(76, 175, 80, 0.2);
                border-radius: 8px;
                font-size: 0.95em;
                border-left: 3px solid #4CAF50;
            }
            .file-item button {
                background: var(--primary);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 15px;
                cursor: pointer;
                font-weight: bold;
                transition: all 0.3s ease;
                display: flex;
                align-items: center;
                gap: 5px;
                margin-top: 10px;
                width: 100%;
                justify-content: center;
            }
            .file-item button:hover {
                background: #ff5500;
                transform: scale(1.05);
            }
            .active-dot {
                display: inline-block;
                width: 10px;
                height: 10px;
                background: radial-gradient(circle at 30% 30%, #66ff66, #00cc00 60%, #006600);
                border-radius: 50%;
                margin-left: 8px;
                box-shadow: 0 0 10px #00ff00;
                animation: pulseGlow 2s infinite ease-in-out;
            }
            @keyframes pulseGlow {
                0%, 100% { transform: scale(1); opacity: 1; }
                50% { transform: scale(1.2); opacity: 0.8; }
            }
            .telegram-icon-container {
                display: flex;
                justify-content: center;
            }
            .telegram-icon {
                width: 40px;
                height: 40px;
                margin: 20px auto;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
                border-radius: 50%;
                background-color: #0088cc;
                padding: 5px;
                display: block;
            }
            .telegram-icon:hover {
                transform: scale(1.1);
            }
            .animated-name {
                font-size: 2rem;
                font-weight: bold;
                text-align: center;
                margin-top: 15px;
                animation: colorShift 4s infinite;
            }
            @keyframes colorShift {
                0% { color: #ff3300; }
                25% { color: #ff6600; }
                50% { color: #ffcc00; }
                75% { color: #ff4500; }
                100% { color: #ff3300; }
            }
            .admin-btn {
                position: absolute;
                top: 20px;
                left: 20px;
                background: var(--primary);
                color: white;
                padding: 10px 15px;
                border-radius: 30px;
                text-decoration: none;
                font-weight: bold;
                display: flex;
                align-items: center;
                gap: 8px;
                transition: all 0.3s ease;
                z-index: 10;
            }
            .admin-btn:hover {
                transform: scale(1.05);
            }
            #toggle-music {
                position: absolute;
                top: 20px;
                right: 20px;
                background: var(--primary);
                width: 50px;
                height: 50px;
                border-radius: 50%;
                display: flex;
                justify-content: center;
                align-items: center;
                border: none;
                cursor: pointer;
                transition: all 0.3s ease;
                z-index: 10;
            }
            #toggle-music:hover {
                transform: scale(1.1);
            }
            .music-icon {
                color: white;
                font-size: 1.5rem;
            }
            hr {
                width: 100%;
                border: none;
                border-top: 1px solid var(--primary);
                opacity: 0.5;
                margin: 10px 0;
                position: relative;
                z-index: 5;
            }
            .copyright-section {
                margin: 40px 0 20px;
                padding: 0 20px;
            }
            .copyright-content {
                max-width: 1200px;
                margin: 0 auto;
                padding: 18px 30px;
                background: rgba(0, 0, 0, 0.9);
                border: 0.5px solid #ff6b08;
                border-radius: 15px;
                box-shadow: 0 4px 20px rgba(255, 107, 8, 0.15);
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-family: 'Arial', sans-serif;
                position: relative;
                overflow: hidden;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            .copyright-content::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: linear-gradient(45deg, transparent 0%, rgba(255, 107, 8, 0.1) 50%, transparent 100%);
                pointer-events: none;
            }
            .copyright-logo {
                font-weight: 700;
                font-size: 1.3em;
                color: #ff6b08;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .copyright-info {
                color: #ffffff;
                font-size: 0.95em;
                display: flex;
                align-items: center;
                gap: 12px;
                background: rgba(255, 107, 8, 0.1);
                padding: 8px 20px;
                border-radius: 25px;
                border: 1px solid rgba(255, 107, 8, 0.3);
            }
            .modal {
                display: none;
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: #1a1a1a;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 0 25px rgba(255, 165, 0, 0.3);
                z-index: 1000;
                width: 70%;
                max-width: 400px;
                text-align: center;
                border: 1px solid #ff8c00;
                animation: pulseBorder 2s infinite;
            }
            .overlay {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.7);
                z-index: 999;
            }
            .accept-btn {
                background: linear-gradient(45deg, #ff8c00, #ff6b00);
                color: white;
                padding: 10px 25px;
                border: none;
                border-radius: 20px;
                cursor: pointer;
                font-size: 16px;
                transition: 0.3s;
                margin: 15px 0;
                border: 1px solid #ffa500;
            }
            .accept-btn:hover {
                transform: scale(1.05);
                box-shadow: 0 0 15px #ff8c00;
            }
            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                background: #4CAF50;
                color: white;
                padding: 15px 20px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                z-index: 1001;
                display: flex;
                align-items: center;
                gap: 10px;
                animation: slideIn 0.3s ease-out;
                max-width: 400px;
            }
            .notification-warning {
                background: #ff9800;
            }
            .notification-error {
                background: #f44336;
            }
            .notification-info {
                background: #2196F3;
            }
            .notification-content {
                display: flex;
                align-items: center;
                gap: 10px;
                flex-grow: 1;
            }
            .notification-close {
                background: none;
                border: none;
                color: white;
                cursor: pointer;
                padding: 5px;
                border-radius: 4px;
                transition: background 0.3s ease;
            }
            .notification-close:hover {
                background: rgba(255,255,255,0.2);
            }
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes pulseBorder {
                0% { border-color: #ff8c00; }
                50% { border-color: #ff6b00; }
                100% { border-color: #ff8c00; }
            }
            .download-modal {
                display: none;
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: rgba(0,0,0,0.9);
                padding: 30px;
                border-radius: 15px;
                border: 2px solid #ff6b00;
                z-index: 1002;
                text-align: center;
                min-width: 300px;
            }
            .download-spinner {
                border: 4px solid rgba(255, 107, 0, 0.3);
                border-radius: 50%;
                border-top: 4px solid #ff6b00;
                width: 50px;
                height: 50px;
                animation: spin 1s linear infinite;
                margin: 20px auto;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            @media (max-width: 768px) {
                .container {
                    margin: 15px;
                    padding: 15px;
                }
                .header {
                    font-size: 2rem;
                }
                .admin-btn {
                    top: 3px;
                    left: 3px;
                    padding: 8px 15px;
                    font-size: 0.9rem;
                }
                #toggle-music {
                    top: 3px;
                    right: 3px;
                    width: 40px;
                    height: 40px;
                }
                .copyright-content {
                    flex-direction: column;
                    gap: 12px;
                    padding: 15px;
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
        <div class="overlay"></div>
        <div class="modal" id="welcomeModal">
            <h2>🛡️ أهلًا وسهلًا 🛡️</h2>
            <p>مرحبًا بكم في <span style="color: #ff8c00">موقع ملفات VPN 🔒</span></p>
            <ul>
                <li>تحميلات VPN مجانية وآمنة</li>
                <li>إعدادات خوادم مدفوعة عالية السرعة</li>
                <li>تحديث ملفات بشكل دوري</li>
            </ul>
            <p style="color: #ff8c00; font-size: 14px;">
                "اللهم انفعنا بما علمتنا وعلمنا ما ينفعنا"
            </p>
            <button class="accept-btn" onclick="closeModal()">الدخول إلى الموقع</button>
        </div>
        
        <div class="download-modal" id="downloadModal">
            <h3>📤 جاري إرسال الملف</h3>
            <div class="download-spinner"></div>
            <p id="downloadMessage">يرجى الانتظار جاري تجهيز الملف...</p>
        </div>

        <div class="container">
            {% if not session.admin_logged_in %}
            <a href="{{ url_for('admin_login') }}" class="admin-btn">
                <i class="fas fa-user-shield"></i> PANEL
            </a>
            {% endif %}
            
            <button id="toggle-music" onclick="toggleMusic()">
                <i class="music-icon fas fa-music"></i>
            </button>
            
            <div class="user-section">
                <img src="{{ user_info.photo_url }}" alt="Avatar" class="avatar-img" onerror="this.src='https://api.dicebear.com/7.x/bottts/svg?seed={{ user_info.telegram_id }}'">
                <div class="avatar-name">
                    {{ user_info.first_name }} {{ user_info.last_name }}
                    {% if user_info.username %}
                        <br><small>@{{ user_info.username }}</small>
                    {% endif %}
                    <br><small style="font-size: 0.8rem; color: #ccc;">ID: {{ user_info.telegram_id }}</small>
                </div>
                
                <div class="user-stats">
                    <div class="stat-card">
                        <div>عدد التنزيلات</div>
                        <div class="stat-value">{{ user_info.download_count }}</div>
                    </div>
                    <div class="stat-card">
                        <div>آخر تنزيل</div>
                        <div class="stat-value">{{ user_info.last_download if user_info.last_download else 'لم يقم بتنزيل' }}</div>
                    </div>
                </div>
            </div>

            <h1 class="header">
                <i class="fas fa-globe"></i> 𝐹𝑅𝐸𝐸 𝐼𝑁𝑇𝐸𝑅𝑁𝐸𝑇
            </h1>
            <hr>
            <div class="file-select">
                <label for="config-type" style="display: block; margin-bottom: 10px; font-weight: bold;">
                    <i class="fas fa-list"></i> اختر نوع VPN
                </label>
                <select id="config-type" onchange="toggleFileList()">
                    <option value="">اختر نوع التطبيق...</option>
                    {% for config_type in config_files %}
                        <option value="{{ config_type }}">{{ config_type }}</option>
                    {% endfor %}
                </select>
            </div>
            <div id="file-options" class="file-list">
                {% for config_type, files in config_files.items() %}
                    <div id="{{ config_type }}-files" class="file-list-group">
                        <h3 style="margin: 15px 0 10px; display: flex; align-items: center;">
                            <img src="{% if config_type == 'HTTP_CUSTOM' %}https://images.squarespace-cdn.com/content/v1/5b7257d68ab7222baffba243/93300b11-86f1-48f3-8a05-6b197b0f710b/HeroLightLogo.png
                                     {% elif config_type == 'Dark_Tunnel' %}https://play-lh.googleusercontent.com/Ax34UpElSZmCPzKIIzf0m_vqMPQmAartTHzkMx3dZ3c5a3wWCfA6CcsJgOi4ob36PSmG
                                     {% elif config_type == 'HTTP_INJECTOR' %}https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSJoyDR3s4jWD14faLAy9V4U8TXp-kp4OggynXcCpJF1A&s
                                     {% else %}https://cdn-icons-png.flaticon.com/512/2965/2965300.png{% endif %}"
                                 alt="{{ config_type }} Icon" style="width: 30px; height: 30px; margin-left: 10px;">
                            {{ config_type }}
                        </h3>
                        {% for file in files %}
                            <div class="file-item" data-active="true">
                                <div class="file-header">
                                    <div class="file-info">
                                        <div>
                                            <span class="active-dot"></span>
                                            <strong>{{ file.name }}</strong>
                                        </div>
                                        <div class="file-meta">
                                            <span>الحجم: {{ file.size }}</span>
                                            <span>التاريخ: {{ file.mod_time }}</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="file-description">
                                    {{ file.description }}
                                </div>
                                <button onclick="downloadFile('{{ config_type }}', '{{ file.name }}')">
                                    <i class="fas fa-download"></i> تنزيل الملف
                                </button>
                            </div>
                        {% endfor %}
                    </div>
                {% endfor %}
            </div>
            <div class="telegram-icon-container">
                <a href="https://t.me/dis102" target="_blank">
                    <img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg"
                         alt="Telegram Icon" class="telegram-icon">
                </a>
            </div>
            <div class="animated-name">
                <i class="fas fa-star"></i>انضم لقناة تليجرام<i class="fas fa-star"></i>
            </div>
        </div>
        <audio id="background-music">
            <source src="https://mp4.shabakngy.com/m/m/yJg-Y5byMMw.mp3" type="audio/mpeg">
            متصفحك لا يدعم تشغيل الصوت.
        </audio>
        
        <div class="copyright-section">
            <div class="copyright-content">
                <span class="copyright-logo">
                    <i class="fas fa-copyright"></i> 𝐊𝐡𝐚𝐥𝐢𝐥
                </span>
                <span class="copyright-info">
                    <span id="currentYear"></span> | جميع الحقوق محفوظة
                    <i class="fas fa-shield-alt"></i>
                </span>
            </div>
        </div>

        <script>
            function toggleFileList() {
                var selectedType = document.getElementById("config-type").value;
                var fileOptions = document.getElementById("file-options");
                var fileListGroups = document.querySelectorAll(".file-list-group");
                fileListGroups.forEach(function(group) {
                    group.style.display = "none";
                });
                if (selectedType) {
                    fileOptions.style.display = "block";
                    document.getElementById(selectedType + "-files").style.display = "block";
                } else {
                    fileOptions.style.display = "none";
                }
            }

            function toggleMusic() {
                var music = document.getElementById("background-music");
                var icon = document.querySelector(".music-icon");
                if (music.paused) {
                    music.volume = 0.3;
                    music.play().then(function() {
                        icon.classList.remove("fa-volume-mute");
                        icon.classList.add("fa-music");
                    }).catch(function(error) {
                        console.log("خطأ في تشغيل الصوت:", error);
                    });
                } else {
                    music.pause();
                    icon.classList.remove("fa-music");
                    icon.classList.add("fa-volume-mute");
                }
            }

            function downloadFile(configType, fileName) {
                document.getElementById('downloadModal').style.display = 'block';
                document.querySelector('.overlay').style.display = 'block';
                document.getElementById('downloadMessage').textContent = 'جاري إرسال الملف عبر البوت...';
                
                fetch(`/download/${configType}/${encodeURIComponent(fileName)}`)
                    .then(response => {
                        if (response.ok) {
                            return response.text();
                        } else {
                            throw new Error('خطأ في الخادم');
                        }
                    })
                    .then(message => {
                        document.getElementById('downloadMessage').innerHTML = '✅ ' + message;
                        setTimeout(() => {
                            document.getElementById('downloadModal').style.display = 'none';
                            document.querySelector('.overlay').style.display = 'none';
                            setTimeout(() => {
                                window.location.reload();
                            }, 2000);
                        }, 2000);
                    })
                    .catch(error => {
                        document.getElementById('downloadMessage').innerHTML = '❌ ' + error.message;
                        setTimeout(() => {
                            document.getElementById('downloadModal').style.display = 'none';
                            document.querySelector('.overlay').style.display = 'none';
                        }, 2000);
                    });
            }

            document.getElementById('currentYear').textContent = new Date().getFullYear();

            window.onload = function() {
                document.querySelector('.overlay').style.display = 'block';
                document.getElementById('welcomeModal').style.display = 'block';
            }

            function closeModal() {
                document.querySelector('.overlay').style.display = 'none';
                document.getElementById('welcomeModal').style.display = 'none';
            }

            document.querySelector('.overlay').addEventListener('click', function() {
                document.getElementById('downloadModal').style.display = 'none';
                this.style.display = 'none';
            });
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
    return config_files

@app.route('/download/<config_type>/<path:filename>')
def download(config_type, filename):
    if not validate_session():
        return "يجب تسجيل الدخول أولاً", 403
    
    current_user = get_current_user()
    if not current_user:
        return "لم يتم العثور على بيانات المستخدم", 404
    
    telegram_id = current_user['telegram_id']
    
    update_user_download(telegram_id, filename)
    
    try:
        file_path = safe_join(DOWNLOAD_FOLDER, config_type, filename)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as file:
                bot.send_document(telegram_id, file, caption=f"🦋")
            return "تم إرسال الملف بنجاح عبر البوت! ✅"
        else:
            return "الملف غير موجود", 404
    except Exception as e:
        print(f"Error sending file via bot: {e}")
        return f"حدث خطأ في إرسال الملف: {str(e)}", 500

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if (request.form['username'] == ADMIN_CREDENTIALS['username'] and
            request.form['password'] == ADMIN_CREDENTIALS['password']):
            session['admin_logged_in'] = True
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
        <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <meta name="robots" content="noindex,nofollow">
        <style>
            body {
                font-family: 'Cairo', sans-serif;
                background-color: #0a192f;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                color: white;
            }
            .login-container {
                background: rgba(0, 0, 0, 0.8);
                padding: 30px;
                border-radius: 15px;
                max-width: 400px;
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
                backdrop-filter: blur(5px);
                border: 1px solid rgba(255, 107, 0, 0.3);
            }
            .login-header {
                text-align: center;
                margin-bottom: 30px;
            }
            .login-header h2 {
                color: #ff6b00;
                font-size: 1.8rem;
                margin-bottom: 10px;
            }
            .login-header i {
                font-size: 2.5rem;
                color: #ff6b00;
            }
            .form-group {
                margin-bottom: 20px;
            }
            .form-group label {
                display: block;
                margin-bottom: 8px;
                font-weight: bold;
            }
            .form-group input {
                width: 100%;
                padding: 12px 10px;
                border-radius: 8px;
                border: 2px solid #ff6b00;
                background: rgba(0, 0, 0, 0.5);
                color: white;
                font-size: 1rem;
            }
            .login-btn {
                width: 100%;
                padding: 12px;
                background: #ff6b00;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 1rem;
                font-weight: bold;
                cursor: pointer;
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 10px;
            }
            .login-btn:hover {
                background: #ff5500;
            }
            .alert {
                padding: 12px;
                border-radius: 8px;
                margin-top: 20px;
                text-align: center;
                background: #ff4444;
                color: white;
            }
            .back-btn {
                background: #6c757d;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 8px;
                margin-top: 15px;
                cursor: pointer;
                transition: all 0.3s ease;
                width: 100%;
                justify-content: center;
            }
            .back-btn:hover {
                background: #5a6268;
            }
        </style>
        {{ protection_script|safe }}
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
            <button class="back-btn" onclick="goBack()">
                <i class="fas fa-arrow-right"></i> رجوع للصفحة الرئيسية
            </button>
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert">
                            <i class="fas fa-exclamation-circle"></i> {{ message }}
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
        </div>
        <script>
            function goBack() {
                window.location.href = '/main';
            }
        </script>
    </body>
    </html>
    ''', protection_script=template_protection_script)

@app.route('/admin/dashboard', methods=['GET', 'POST'])
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

    # الحصول على إحصائيات المستخدمين
    users = get_all_users()
    total_users = len(users)
    total_downloads = sum(user.get('download_count', 0) for user in users.values())
    
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
                max-width: 1200px;
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
            .stats-section {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: rgba(255, 107, 0, 0.1);
                padding: 20px;
                border-radius: 10px;
                border: 1px solid rgba(255, 107, 0, 0.3);
                text-align: center;
            }
            .stat-number {
                font-size: 2rem;
                font-weight: bold;
                color: #ff8c00;
                margin: 10px 0;
            }
            .stat-label {
                font-size: 0.9rem;
                color: #ccc;
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
            .users-section {
                margin-top: 30px;
            }
            .users-table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }
            .users-table th,
            .users-table td {
                padding: 12px;
                text-align: right;
                border-bottom: 1px solid rgba(255, 107, 0, 0.3);
            }
            .users-table th {
                background: rgba(255, 107, 0, 0.2);
                color: #ff8c00;
                font-weight: bold;
            }
            .users-table tr:hover {
                background: rgba(255, 107, 0, 0.1);
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
                .stats-section {
                    grid-template-columns: 1fr;
                }
                .users-table {
                    font-size: 0.8rem;
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
            
            <!-- إحصائيات -->
            <div class="stats-section">
                <div class="stat-card">
                    <div class="stat-label">إجمالي المستخدمين</div>
                    <div class="stat-number">{{ total_users }}</div>
                    <i class="fas fa-users"></i>
                </div>
                <div class="stat-card">
                    <div class="stat-label">إجمالي التنزيلات</div>
                    <div class="stat-number">{{ total_downloads }}</div>
                    <i class="fas fa-download"></i>
                </div>
                <div class="stat-card">
                    <div class="stat-label">أنواع الملفات</div>
                    <div class="stat-number">{{ config_types|length }}</div>
                    <i class="fas fa-folder"></i>
                </div>
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
            
            <div class="users-section">
                <h2 style="color: #ff6b00; margin-top: 30px;"><i class="fas fa-users"></i> إدارة المستخدمين</h2>
                <div class="config-type-section">
                    {% if users %}
                        <table class="users-table">
                            <thead>
                                <tr>
                                    <th>رقم التعريف</th>
                                    <th>الاسم</th>
                                    <th>المستخدم</th>
                                    <th>عدد التنزيلات</th>
                                    <th>آخر تنزيل</th>
                                    <th>تاريخ التسجيل</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for user_id, user in users.items() %}
                                <tr>
                                    <td>{{ user_id }}</td>
                                    <td>{{ user.first_name }} {{ user.last_name }}</td>
                                    <td>@{{ user.username if user.username else 'لا يوجد' }}</td>
                                    <td>{{ user.download_count }}</td>
                                    <td>{{ user.last_download if user.last_download else 'لم يقم بتنزيل' }}</td>
                                    <td>{{ user.created_at }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    {% else %}
                        <p>لا يوجد مستخدمين مسجلين بعد.</p>
                    {% endif %}
                </div>
            </div>
        </div>
    </body>
    </html>
    ''', config_types=CONFIG_TYPES, config_files=config_files, users=users, 
    total_users=total_users, total_downloads=total_downloads, protection_script=template_protection_script)

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
            "🚀 فتح التطبيق", 
            web_app=WebAppInfo(url=web_app_url)
        )
        
        stats_button = InlineKeyboardButton(
            "📊 إحصائياتي",
            callback_data="stats"
        )
        
        keyboard.add(web_app_button)
        keyboard.add(stats_button)
        
        welcome_text = f"""
        🎉 أهلاً بك {user.first_name} في بوت الإعدادات المجانية

        👤 **معلومات حسابك:**
        • الاسم: {user.first_name} {user.last_name or ''}
        • المستخدم: @{user.username or 'غير متوفر'}
        • رقم التعريف: {user.id}

        🔌 **المميزات المتاحة:**
        • تحميل إعدادات VPN مجانية
        • تطبيقات متميزة مجانية
        • خوادم سريعة ومستقرة
        • تحديثات دورية للملفات

        📱 **للبدء، اضغط على الزر أدناه لفتح التطبيق:**
        """
        
        # إرسال صورة ترحيبية مع الأزرار
        try:
            bot.send_photo(
                message.chat.id,
                photo="https://www.tech-mag.net/techmag/uploads/2024/02/smartphone-5623402_1280-1.jpg",
                caption=welcome_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        except:
            # إذا فشل إرسال الصورة، أرسل الرسالة فقط
            bot.send_message(
                message.chat.id,
                welcome_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        
        print(f"✅ Sent WebApp button to user {user.id} ({user.first_name})")
        
    except Exception as e:
        print(f"Error in start command: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "stats")
def stats_callback(call):
    try:
        user_info = get_user_info(call.from_user.id)
        if user_info:
            stats_text = f"""
            📊 **إحصائياتك الشخصية**

            👤 **الاسم:** {user_info['first_name']} {user_info['last_name']}
            📧 **المستخدم:** @{user_info['username'] if user_info['username'] else 'لا يوجد'}
            📥 **عدد التنزيلات:** {user_info['download_count']}
            🕒 **آخر تنزيل:** {user_info['last_download'] if user_info['last_download'] else 'لم تقم بأي تنزيل بعد'}

            🔌 **استمر في استخدام التطبيق لتحميل المزيد**
           """
        else:
            stats_text = """
            ❌ **لم نعثر على بياناتك**
            
            🔧 **الحل:**
            1. اضغط على زر 'فتح التطبيق' 
            2. سجل الدخول تلقائياً
            3. عد هنا وشاهد إحصائياتك
            """
        
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, stats_text, parse_mode="Markdown")
    except Exception as e:
        print(f"Error in stats callback: {e}")

@bot.message_handler(commands=['stats'])
def stats_command(message):
    try:
        user_info = get_user_info(message.from_user.id)
        if user_info:
            stats_text = f"""
            📊 **إحصائياتك الشخصية**

            👤 **الاسم:** {user_info['first_name']} {user_info['last_name']}
            📧 **المستخدم:** @{user_info['username'] if user_info['username'] else 'لا يوجد'}
            📥 **عدد التنزيلات:** {user_info['download_count']}
            🕒 **آخر تنزيل:** {user_info['last_download'] if user_info['last_download'] else 'لم تقم بأي تنزيل بعد'}

            🔓 **استمر في استخدام التطبيق لتحميل المزيد**
            """
        else:
            stats_text = """
            ❌ **لم نعثر على بياناتك**
            
            🔧 **الحل:**
            1. اضغط على زر 'فتح التطبيق' 
            2. سجل الدخول تلقائياً
            3. عد هنا وشاهد إحصائياتك
            """
        
        bot.send_message(message.chat.id, stats_text, parse_mode="Markdown")
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
