#!/usr/bin/env python3
"""
Инициализация единой базы данных с UID системой для Render.com
"""

import os
import sqlite3

def init_database():
    """Создает единую базу данных с UID системой"""
    # Создаем папку data если не существует
    os.makedirs('data', exist_ok=True)
    
    conn = sqlite3.connect('data/unified.db')
    cursor = conn.cursor()
    
    # Таблица пользователей с UID системой
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT UNIQUE NOT NULL,
            telegram_id TEXT UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            phone TEXT,
            balance_stars INTEGER DEFAULT 0,
            balance_rub REAL DEFAULT 0,
            balance_uah REAL DEFAULT 0,
            successful_deals INTEGER DEFAULT 0,
            verified BOOLEAN DEFAULT FALSE,
            session_file TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица сделок
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deals (
            id TEXT PRIMARY KEY,
            seller_id TEXT,
            buyer_id TEXT,
            nft_link TEXT,
            nft_username TEXT,
            amount REAL,
            currency TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            paid_at TIMESTAMP,
            completed_at TIMESTAMP,
            description TEXT
        )
    ''')
    
    # Таблица верификационных кодов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verification_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT NOT NULL,
            code TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT FALSE
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Единая база данных с UID системой инициализирована")

if __name__ == '__main__':
    init_database()