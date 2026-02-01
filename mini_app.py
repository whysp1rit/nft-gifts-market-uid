from flask import Flask, render_template, request, jsonify, session, make_response
import sqlite3
import uuid
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'nft-gifts-mini-app-secret-key'

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
    conn = sqlite3.connect('data/unified.db')
    cursor = conn.cursor()
    
    # Таблицы уже созданы в unified_database.py
    # Просто проверяем подключение
    cursor.execute('SELECT COUNT(*) FROM users')
    user_count = cursor.fetchone()[0]
    print(f"📊 Подключение к единой базе: {user_count} пользователей")
    
    conn.close()

# Главная страница Mini App
@app.route('/')
def index():
    response = make_response(render_template('mini_app/index.html'))
    return response

# Тестовая страница для отладки UID
@app.route('/test-uid')
def test_uid():
    try:
        with open('test_uid_display.html', 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        return "<h1>UID Test Page</h1><p>Файл не найден, но UID система работает!</p>"
    except Exception as e:
        return f"<h1>UID Test Page</h1><p>Ошибка: {str(e)}</p>"

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
    return render_template('mini_app/admin.html')

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
            # Создаем нового пользователя с 0 баланса
            cursor.execute('''
                INSERT INTO users (telegram_id, username, first_name, balance_stars, balance_rub, successful_deals)
                VALUES (?, ?, ?, 0, 0, 0)
            ''', (telegram_id, username, first_name))
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
            INSERT INTO deals (id, seller_id, nft_link, nft_username, amount, currency, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (deal_id, telegram_id, data.get('nft_link'), data.get('nft_username'), 
              data.get('amount'), data.get('currency'), data.get('description')))
        
        conn.commit()
        conn.close()
        
        # Получаем текущий хост для создания ссылки
        base_url = request.host_url.rstrip('/')
        
        # Создаем ссылку для Mini App в Telegram
        deal_url = f"https://t.me/noscamnftrobot/app?startapp=deal_{deal_id}"
        
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