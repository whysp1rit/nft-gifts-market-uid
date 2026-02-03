from flask import Flask, render_template, request, jsonify, session, make_response
import sqlite3
import uuid
from datetime import datetime
import os
import requests
import asyncio

app = Flask(__name__)
app.secret_key = 'nft-gifts-mini-app-secret-key'

# Конфигурация бота для уведомлений
BOT_TOKEN = "8512489092:AAFghx4VAurEYdi8gDZVUJ71pqGRnC8-n4M"
ADMIN_ID = 8566238705

def notify_admin_about_deal(deal_id, seller_name, amount, currency, description):
    """Отправляет уведомление администратору о новой сделке через Telegram Bot API"""
    try:
        currency_symbols = {
            'stars': '⭐',
            'rub': '₽',
            'uah': '₴',
            'usd': '$',
            'eur': '€'
        }
        
        symbol = currency_symbols.get(currency, '')
        
        text = f"🆕 <b>Новая сделка создана!</b>\n\n" \
               f"🆔 <b>ID сделки:</b> #{deal_id}\n" \
               f"👤 <b>Продавец:</b> {seller_name}\n" \
               f"💰 <b>Сумма:</b> {symbol}{amount}\n" \
               f"📝 <b>Описание:</b> {description or 'Не указано'}\n\n" \
               f"⏳ <b>Статус:</b> Ожидает подтверждения"
        
        # Создаем inline клавиатуру
        keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "✅ Подтвердить сделку",
                        "callback_data": f"confirm_deal_{deal_id}"
                    }
                ],
                [
                    {
                        "text": "❌ Отклонить сделку", 
                        "callback_data": f"reject_deal_{deal_id}"
                    }
                ],
                [
                    {
                        "text": "🔍 Посмотреть сделку",
                        "url": f"https://nft-gifts-market-uid.onrender.com/deal/{deal_id}"
                    }
                ]
            ]
        }
        
        # Отправляем сообщение через Telegram Bot API
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": ADMIN_ID,
            "text": text,
            "parse_mode": "HTML",
            "reply_markup": keyboard
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Уведомление о сделке {deal_id} отправлено администратору")
        else:
            print(f"❌ Ошибка отправки уведомления: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Ошибка уведомления администратора: {e}")

# Убираем все предупреждения и добавляем CORS
@app.after_request
def after_request(response):
    """Убираем предупреждения и добавляем нужные заголовки"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['ngrok-skip-browser-warning'] = 'true'
    response.headers['X-Frame-Options'] = 'ALLOWALL'
    response.headers['Content-Security-Policy'] = "frame-ancestors *"
    return response

# Инициализация единой базы данных для Mini App
def init_mini_app_db():
    """Инициализирует базу данных или проверяет подключение"""
    try:
        # Создаем папку data если её нет
        os.makedirs('data', exist_ok=True)
        
        conn = sqlite3.connect('data/unified.db')
        cursor = conn.cursor()
        
        # Проверяем, существует ли таблица users
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cursor.fetchone():
            print("📊 База данных не найдена. Запустите init_db.py для инициализации.")
            conn.close()
            return
        
        # Проверяем подключение
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        print(f"📊 Подключение к единой базе: {user_count} пользователей")
        
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        print("💡 Запустите init_db.py для создания базы данных")

# Главная страница Mini App
@app.route('/')
def index():
    response = make_response(render_template('mini_app/index.html'))
    return response

# Тестовая страница для отладки UID
@app.route('/test-uid')
def test_uid():
    """Простая тестовая страница для проверки UID системы"""
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>UID Test Page</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; text-align: center; }
            .card { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px auto; max-width: 400px; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🆔 UID Test Page</h1>
            <p>UID система работает корректно!</p>
            <p>Этот эндпоинт используется для тестирования.</p>
            <button onclick="window.location.href='/'">🏠 На главную</button>
        </div>
    </body>
    </html>
    """

# Тестовая страница для отладки параметров startapp
@app.route('/test-startapp')
def test_startapp():
    """Страница для отладки параметров startapp"""
    return """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>StartApp Parameters Test</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            .info { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 8px; }
            pre { background: #e9ecef; padding: 10px; border-radius: 4px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <h1>🔗 Тест параметров StartApp</h1>
        <div id="info"></div>
        <button onclick="window.location.href='/'">🏠 На главную</button>
        
        <script>
            let tg = window.Telegram.WebApp;
            tg.ready();
            
            const info = document.getElementById('info');
            const initData = tg.initDataUnsafe;
            const urlParams = new URLSearchParams(window.location.search);
            
            info.innerHTML = `
                <div class="info">
                    <h3>Данные инициализации:</h3>
                    <pre>${JSON.stringify(initData, null, 2)}</pre>
                </div>
                <div class="info">
                    <h3>URL параметры:</h3>
                    <pre>${JSON.stringify(Object.fromEntries(urlParams), null, 2)}</pre>
                </div>
                <div class="info">
                    <h3>Полный URL:</h3>
                    <pre>${window.location.href}</pre>
                </div>
            `;
        </script>
    </body>
    </html>
    """
    with open('test_startapp_params.html', 'r', encoding='utf-8') as f:
        content = f.read()
    return content

# Создание сделки
@app.route('/create')
def create_deal():
    return render_template('mini_app/create.html')

# Мои сделки
@app.route('/deals')
def my_deals():
    return render_template('mini_app/deals.html')

# Профиль
@app.route('/profile')
def profile():
    return render_template('mini_app/profile.html')

# Админ панель
@app.route('/admin')
def admin_panel():
    try:
        return render_template('mini_app/admin.html')
    except Exception as e:
        # Если шаблон не найден, возвращаем встроенную HTML страницу
        html_content = """
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <title>Админ панель</title>
            <style>
                body { font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }
                .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
                .btn:hover { background: #0056b3; }
                input { width: 100%; padding: 8px; margin: 5px 0; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
                .success { color: green; }
                .error { color: red; }
                .user-item { padding: 10px; border-bottom: 1px solid #eee; }
                .user-item:last-child { border-bottom: none; }
            </style>
        </head>
        <body>
            <h1>🔧 Админ панель NFT Gifts Market</h1>
            
            <div class="card">
                <h3>📊 Статистика системы</h3>
                <div id="statsContainer">⏳ Загрузка статистики...</div>
            </div>
            
            <div class="card">
                <h3>💰 Пополнение баланса по UID</h3>
                <p>Введите UID пользователя (8 символов) и сумму для пополнения:</p>
                <input type="text" id="userUID" placeholder="UID пользователя (например: A1B2C3D4)" maxlength="8" style="text-transform: uppercase;">
                <input type="number" id="starsAmount" placeholder="Количество звезд" min="0">
                <input type="number" id="rubAmount" placeholder="Сумма в рублях" min="0" step="0.01">
                <button class="btn" onclick="addBalanceByUID()">💰 Пополнить баланс</button>
                <div id="balanceResult"></div>
            </div>
            
            <div class="card">
                <h3>👥 Управление пользователями</h3>
                <button class="btn" onclick="loadAllUsers()">📋 Загрузить всех пользователей</button>
                <div id="usersContainer"></div>
            </div>
            
            <div class="card">
                <h3>📈 Быстрые действия</h3>
                <button class="btn" onclick="window.location.href='/'">🏠 На главную</button>
                <button class="btn" onclick="window.location.href='/test-uid'">🧪 Тест UID</button>
                <button class="btn" onclick="window.location.href='/test-startapp'">🔗 Тест ссылок</button>
            </div>
            
            <script>
                // Загрузка статистики при открытии страницы
                document.addEventListener('DOMContentLoaded', function() {
                    loadStats();
                });
                
                function loadStats() {
                    fetch('/api/admin/stats')
                        .then(r => r.json())
                        .then(data => {
                            if (data.success) {
                                const stats = data.stats;
                                document.getElementById('statsContainer').innerHTML = `
                                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px;">
                                        <div style="text-align: center; padding: 15px; background: #e3f2fd; border-radius: 8px;">
                                            <div style="font-size: 24px; font-weight: bold; color: #1976d2;">${stats.total_users}</div>
                                            <div style="font-size: 12px; color: #666;">Всего пользователей</div>
                                        </div>
                                        <div style="text-align: center; padding: 15px; background: #e8f5e8; border-radius: 8px;">
                                            <div style="font-size: 24px; font-weight: bold; color: #388e3c;">${stats.verified_users}</div>
                                            <div style="font-size: 12px; color: #666;">Верифицированных</div>
                                        </div>
                                        <div style="text-align: center; padding: 15px; background: #fff3e0; border-radius: 8px;">
                                            <div style="font-size: 24px; font-weight: bold; color: #f57c00;">⭐${stats.total_stars}</div>
                                            <div style="font-size: 12px; color: #666;">Всего звезд</div>
                                        </div>
                                        <div style="text-align: center; padding: 15px; background: #fce4ec; border-radius: 8px;">
                                            <div style="font-size: 24px; font-weight: bold; color: #c2185b;">₽${stats.total_rub}</div>
                                            <div style="font-size: 12px; color: #666;">Всего рублей</div>
                                        </div>
                                        <div style="text-align: center; padding: 15px; background: #f3e5f5; border-radius: 8px;">
                                            <div style="font-size: 24px; font-weight: bold; color: #7b1fa2;">${stats.total_deals}</div>
                                            <div style="font-size: 12px; color: #666;">Всего сделок</div>
                                        </div>
                                    </div>
                                `;
                            } else {
                                document.getElementById('statsContainer').innerHTML = '<p class="error">Ошибка загрузки статистики</p>';
                            }
                        })
                        .catch(error => {
                            document.getElementById('statsContainer').innerHTML = '<p class="error">Ошибка подключения к серверу</p>';
                        });
                }
                
                function addBalanceByUID() {
                    const uid = document.getElementById('userUID').value.toUpperCase().trim();
                    const stars = parseInt(document.getElementById('starsAmount').value) || 0;
                    const rub = parseFloat(document.getElementById('rubAmount').value) || 0;
                    
                    if (!uid || uid.length !== 8) {
                        document.getElementById('balanceResult').innerHTML = '<p class="error">❌ Введите корректный UID (8 символов)</p>';
                        return;
                    }
                    
                    if (stars === 0 && rub === 0) {
                        document.getElementById('balanceResult').innerHTML = '<p class="error">❌ Укажите сумму для пополнения</p>';
                        return;
                    }
                    
                    document.getElementById('balanceResult').innerHTML = '<p>⏳ Пополняем баланс...</p>';
                    
                    fetch('/api/admin/add_balance', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({uid: uid, stars: stars, rub: rub})
                    })
                    .then(r => r.json())
                    .then(data => {
                        const className = data.success ? 'success' : 'error';
                        const icon = data.success ? '✅' : '❌';
                        document.getElementById('balanceResult').innerHTML = `<p class="${className}">${icon} ${data.message}</p>`;
                        
                        if (data.success) {
                            // Очищаем поля после успешного пополнения
                            document.getElementById('userUID').value = '';
                            document.getElementById('starsAmount').value = '';
                            document.getElementById('rubAmount').value = '';
                            
                            // Обновляем статистику
                            loadStats();
                        }
                    })
                    .catch(error => {
                        document.getElementById('balanceResult').innerHTML = '<p class="error">❌ Ошибка подключения к серверу</p>';
                    });
                }
                
                function loadAllUsers() {
                    document.getElementById('usersContainer').innerHTML = '<p>⏳ Загружаем пользователей...</p>';
                    
                    fetch('/api/admin/users')
                        .then(r => r.json())
                        .then(data => {
                            if (data.success) {
                                let html = '<div style="max-height: 400px; overflow-y: auto;">';
                                data.users.forEach(user => {
                                    const verifiedIcon = user.verified ? '✅' : '❌';
                                    html += `
                                        <div class="user-item">
                                            <strong>🆔 ${user.uid}</strong> | 
                                            ${user.first_name || 'Без имени'} 
                                            ${user.username ? '@' + user.username : ''}<br>
                                            <small>
                                                ID: ${user.telegram_id} | 
                                                ⭐${user.balance_stars} ₽${user.balance_rub} | 
                                                🤝${user.successful_deals} сделок | 
                                                ${verifiedIcon} ${user.verified ? 'Верифицирован' : 'Не верифицирован'}
                                            </small>
                                        </div>
                                    `;
                                });
                                html += '</div>';
                                document.getElementById('usersContainer').innerHTML = html;
                            } else {
                                document.getElementById('usersContainer').innerHTML = '<p class="error">❌ Ошибка загрузки пользователей</p>';
                            }
                        })
                        .catch(error => {
                            document.getElementById('usersContainer').innerHTML = '<p class="error">❌ Ошибка подключения к серверу</p>';
                        });
                }
                
                // Автоматическое преобразование UID в верхний регистр
                document.getElementById('userUID').addEventListener('input', function(e) {
                    e.target.value = e.target.value.toUpperCase();
                });
            </script>
        </body>
        </html>
        """
        return html_content

# API для создания сделки
@app.route('/api/create_deal', methods=['POST'])
def api_create_deal():
    try:
        data = request.get_json()
        
        # Получаем данные пользователя из Telegram WebApp
        telegram_user = data.get('telegram_user')
        if not telegram_user:
            return jsonify({'success': False, 'message': 'Не удалось получить данные пользователя'})
        
        deal_id = str(uuid.uuid4())[:8].upper()
        
        conn = sqlite3.connect('data/unified.db')
        cursor = conn.cursor()
        
        # Создаем пользователя если не существует (БЕЗ перезаписи баланса)
        telegram_id = str(telegram_user['id'])
        username = telegram_user.get('username')
        first_name = telegram_user.get('first_name')
        
        # Проверяем, существует ли пользователь
        cursor.execute('SELECT COUNT(*) FROM users WHERE telegram_id = ?', (telegram_id,))
        user_exists = cursor.fetchone()[0] > 0
        
        if not user_exists:
            # Генерируем уникальный UID для нового пользователя
            import random
            import string
            while True:
                uid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                cursor.execute('SELECT uid FROM users WHERE uid = ?', (uid,))
                if not cursor.fetchone():
                    break
            
            # Создаем нового пользователя с UID и 0 баланса
            cursor.execute('''
                INSERT INTO users (uid, telegram_id, username, first_name, balance_stars, balance_rub, successful_deals, verified)
                VALUES (?, ?, ?, ?, 0, 0, 0, FALSE)
            ''', (uid, telegram_id, username, first_name))
        else:
            # Обновляем только имя и username, НЕ трогая баланс
            cursor.execute('''
                UPDATE users 
                SET username = COALESCE(?, username), 
                    first_name = COALESCE(?, first_name)
                WHERE telegram_id = ?
            ''', (username, first_name, telegram_id))
        
        # Удаляем возможные дубликаты (оставляем только одну запись с минимальным ID)
        cursor.execute('''
            DELETE FROM users 
            WHERE telegram_id = ? 
            AND id NOT IN (
                SELECT MIN(id) FROM users WHERE telegram_id = ?
            )
        ''', (telegram_id, telegram_id))
        
        # Создаем сделку
        cursor.execute('''
            INSERT INTO deals (id, seller_id, nft_link, nft_username, amount, currency, status, description)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
        ''', (deal_id, telegram_id, data.get('nft_link'), data.get('nft_username'), 
              data.get('amount'), data.get('currency'), data.get('description')))
        
        conn.commit()
        conn.close()
        
        # Получаем текущий хост для создания ссылки
        base_url = request.host_url.rstrip('/')
        
        # Если мы на Render, используем правильный домен
        if 'onrender.com' in request.host or 'render.com' in request.host:
            base_url = 'https://nft-gifts-market-uid.onrender.com'
        
        # Создаем ссылку для бота в Telegram (обычная ссылка, не мини приложение)
        deal_url = f"https://t.me/noscamnftrbot?start=deal_{deal_id}"
        
        # Уведомляем администратора о новой сделке
        try:
            notify_admin_about_deal(deal_id, first_name or username or telegram_id, 
                                  data.get('amount'), data.get('currency'), 
                                  data.get('description'))
        except Exception as e:
            print(f"❌ Ошибка уведомления администратора: {e}")
        
        return jsonify({
            'success': True, 
            'deal_id': deal_id,
            'deal_url': deal_url
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

# Просмотр сделки
@app.route('/deal/<deal_id>')
def view_deal(deal_id):
    return render_template('mini_app/deal.html', deal_id=deal_id)

# API для получения сделки
@app.route('/api/deal/<deal_id>')
def api_get_deal(deal_id):
    try:
        conn = sqlite3.connect('data/unified.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM deals WHERE id = ?', (deal_id,))
        deal = cursor.fetchone()
        conn.close()
        
        if not deal:
            return jsonify({'success': False, 'message': 'Сделка не найдена'})
        
        deal_data = {
            'id': deal[0],
            'seller_id': deal[1],
            'buyer_id': deal[2],
            'nft_link': deal[3],
            'nft_username': deal[4],
            'amount': deal[5],
            'currency': deal[6],
            'status': deal[7],
            'created_at': deal[8],
            'description': deal[11] if len(deal) > 11 else None
        }
        
        return jsonify({'success': True, 'deal': deal_data})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

# API для получения моих сделок
@app.route('/api/my_deals')
def api_my_deals():
    try:
        telegram_user_id = request.args.get('user_id')
        
        conn = sqlite3.connect('data/unified.db')
        cursor = conn.cursor()
        
        # Сделки где пользователь продавец
        cursor.execute('''
            SELECT * FROM deals WHERE seller_id = ? ORDER BY created_at DESC LIMIT 50
        ''', (telegram_user_id,))
        seller_deals = cursor.fetchall()
        
        # Сделки где пользователь покупатель
        cursor.execute('''
            SELECT * FROM deals WHERE buyer_id = ? ORDER BY created_at DESC LIMIT 50
        ''', (telegram_user_id,))
        buyer_deals = cursor.fetchall()
        
        conn.close()
        
        return jsonify({
            'success': True,
            'seller_deals': seller_deals,
            'buyer_deals': buyer_deals
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

# API для получения данных пользователя
@app.route('/api/user_profile')
def api_user_profile():
    try:
        telegram_user_id = request.args.get('user_id')
        
        if not telegram_user_id:
            return jsonify({'success': False, 'message': 'Не указан ID пользователя'})
        
        conn = sqlite3.connect('data/unified.db')
        cursor = conn.cursor()
        
        # Проверяем, существует ли пользователь по Telegram ID
        cursor.execute('SELECT COUNT(*) FROM users WHERE telegram_id = ?', (telegram_user_id,))
        user_exists = cursor.fetchone()[0] > 0
        
        if not user_exists:
            # Генерируем уникальный UID для нового пользователя
            import random
            import string
            while True:
                uid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                cursor.execute('SELECT uid FROM users WHERE uid = ?', (uid,))
                if not cursor.fetchone():
                    break
            
            # Создаем нового пользователя с UID
            cursor.execute('''
                INSERT INTO users (uid, telegram_id, balance_stars, balance_rub, successful_deals, verified)
                VALUES (?, ?, 0, 0, 0, FALSE)
            ''', (uid, telegram_user_id))
            print(f"➕ Создан новый пользователь: {telegram_user_id} с UID: {uid}")
        else:
            print(f"👤 Пользователь уже существует: {telegram_user_id}")
        
        # Удаляем возможные дубликаты
        cursor.execute('''
            DELETE FROM users 
            WHERE telegram_id = ? 
            AND id NOT IN (
                SELECT MIN(id) FROM users WHERE telegram_id = ?
            )
        ''', (telegram_user_id, telegram_user_id))
        
        # Получаем данные пользователя включая UID и верификацию
        cursor.execute('''
            SELECT uid, telegram_id, username, first_name, balance_stars, balance_rub, successful_deals, verified, phone, created_at
            FROM users WHERE telegram_id = ?
        ''', (telegram_user_id,))
        user = cursor.fetchone()
        
        conn.commit()
        conn.close()
        
        if user:
            user_data = {
                'uid': user[0],
                'telegram_id': user[1],
                'username': user[2],
                'first_name': user[3],
                'balance_stars': user[4],
                'balance_rub': user[5],
                'successful_deals': user[6],
                'verified': bool(user[7]) if user[7] is not None else False,
                'phone': user[8],
                'created_at': user[9],
                'is_new_user': False  # Пользователь существует в системе
            }
            return jsonify({'success': True, 'user': user_data})
        else:
            return jsonify({'success': False, 'message': 'Пользователь не найден'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

# API для получения списка пользователей (админ)
@app.route('/api/admin/users')
def api_admin_users():
    try:
        conn = sqlite3.connect('data/unified.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT uid, telegram_id, username, first_name, balance_stars, balance_rub, successful_deals, verified, created_at
            FROM users ORDER BY created_at DESC
        ''')
        users = cursor.fetchall()
        conn.close()
        
        users_list = []
        for user in users:
            users_list.append({
                'uid': user[0],
                'telegram_id': user[1],
                'username': user[2] or 'Не указан',
                'first_name': user[3] or 'Не указано',
                'balance_stars': user[4],
                'balance_rub': user[5],
                'successful_deals': user[6],
                'verified': bool(user[7]) if user[7] is not None else False,
                'created_at': user[8]
            })
        
        return jsonify({'success': True, 'users': users_list})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

# API для получения статистики (админ)
@app.route('/api/admin/stats')
def api_admin_stats():
    try:
        conn = sqlite3.connect('data/unified.db')
        cursor = conn.cursor()
        
        # Общая статистика
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE verified = TRUE')
        verified_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(balance_stars), SUM(balance_rub) FROM users')
        balances = cursor.fetchone()
        total_stars = balances[0] or 0
        total_rub = balances[1] or 0
        
        cursor.execute('SELECT COUNT(*) FROM deals')
        total_deals = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_users': total_users,
                'verified_users': verified_users,
                'total_stars': total_stars,
                'total_rub': total_rub,
                'total_deals': total_deals
            }
        })
        
    except Exception as e:
        print(f"Ошибка API статистики: {e}")
        return jsonify({'success': False, 'message': f'Ошибка сервера: {str(e)}'})

# API для пополнения баланса по UID (админ)
@app.route('/api/admin/add_balance', methods=['POST'])
def api_admin_add_balance():
    try:
        data = request.get_json()
        uid = data.get('uid', '').strip().upper()
        stars = int(data.get('stars', 0))
        rub = float(data.get('rub', 0))
        
        if not uid:
            return jsonify({'success': False, 'message': 'UID не указан'})
        
        if len(uid) != 8:
            return jsonify({'success': False, 'message': 'UID должен содержать 8 символов'})
        
        if stars == 0 and rub == 0:
            return jsonify({'success': False, 'message': 'Укажите сумму для пополнения'})
        
        conn = sqlite3.connect('data/unified.db')
        cursor = conn.cursor()
        
        # Проверяем, существует ли пользователь с таким UID
        cursor.execute('SELECT telegram_id, username, first_name FROM users WHERE uid = ?', (uid,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'success': False, 'message': f'Пользователь с UID {uid} не найден'})
        
        telegram_id, username, first_name = user
        
        # Пополняем баланс
        cursor.execute('''
            UPDATE users SET 
                balance_stars = balance_stars + ?,
                balance_rub = balance_rub + ?
            WHERE uid = ?
        ''', (stars, rub, uid))
        
        conn.commit()
        conn.close()
        
        user_info = f"{first_name} (@{username}) | ID: {telegram_id}"
        
        return jsonify({
            'success': True,
            'message': f'Баланс пополнен для {user_info}',
            'user_info': user_info,
            'added': {
                'stars': stars,
                'rub': rub
            }
        })
        
    except Exception as e:
        print(f"Ошибка пополнения баланса: {e}")
        return jsonify({'success': False, 'message': f'Ошибка сервера: {str(e)}'})

# API для накрутки успешных сделок (админ)
@app.route('/api/admin/update_deals', methods=['POST'])
def api_admin_update_deals():
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        deals_count = int(data.get('deals_count', 0))
        
        if not telegram_id or deals_count < 0:
            return jsonify({'success': False, 'message': 'Неверные данные'})
        
        conn = sqlite3.connect('data/unified.db')
        cursor = conn.cursor()
        
        # Создаем пользователя если не существует
        cursor.execute('''
            INSERT OR IGNORE INTO users (telegram_id) VALUES (?)
        ''', (telegram_id,))
        
        # Обновляем количество сделок
        cursor.execute('''
            UPDATE users SET successful_deals = ? WHERE telegram_id = ?
        ''', (deals_count, telegram_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'Количество сделок установлено: {deals_count}'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

# API для сброса баланса пользователя (админ)
@app.route('/api/admin/reset_balance', methods=['POST'])
def api_admin_reset_balance():
    try:
        data = request.get_json()
        telegram_id = data.get('telegram_id')
        
        if not telegram_id:
            return jsonify({'success': False, 'message': 'Не указан Telegram ID'})
        
        conn = sqlite3.connect('data/unified.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET balance_stars = 0, balance_rub = 0, successful_deals = 0 
            WHERE telegram_id = ?
        ''', (telegram_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Баланс и сделки сброшены'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

# Обработка ошибок
@app.errorhandler(404)
def not_found(error):
    return render_template('mini_app/index.html'), 200

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'message': 'Внутренняя ошибка сервера'}), 500

if __name__ == '__main__':
    init_mini_app_db()
    print("🚀 Запуск Mini App с UID системой и админ панелью...")
    print("📱 Mini App будет доступен по адресу: http://localhost:3000")
    print("🔧 Для остановки нажмите Ctrl+C")
    print("-" * 50)
    app.run(debug=True, host='0.0.0.0', port=3000)