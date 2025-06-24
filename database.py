import aiosqlite

DB_PATH = "users.db"

# В файле database.py добавим колонку "status" в таблицу пользователей

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE,
                service TEXT,
                status TEXT DEFAULT 'Принят',
                review TEXT,
                rating INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status_changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- Новое поле для даты изменения статуса
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                telegram_id INTEGER PRIMARY KEY
            )
        """)
        await db.commit()




async def add_user(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (telegram_id) VALUES (?)", (telegram_id,))
        await db.commit()

async def update_service(telegram_id: int, service: str):
    async with aiosqlite.connect(DB_PATH) as db:
        # Обновим существующего пользователя или добавим нового
        await db.execute("""
            INSERT INTO users (telegram_id, service, status)
            VALUES (?, ?, 'Принята')
            ON CONFLICT(telegram_id) DO UPDATE SET service = excluded.service, status = 'Принята'
        """, (telegram_id, service))
        await db.commit()


async def add_admin(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                telegram_id INTEGER PRIMARY KEY
            )
        """)
        await db.execute("INSERT OR IGNORE INTO admins (telegram_id) VALUES (?)", (telegram_id,))
        await db.commit()

async def is_admin(telegram_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM admins WHERE telegram_id = ?", (telegram_id,))
        return bool(await cursor.fetchone())

async def get_user_requests(telegram_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT id, service, status FROM requests WHERE user_id = ?
        """, (telegram_id,))
        return await cursor.fetchall()

async def get_all_requests():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            SELECT id, telegram_id, service, status, created_at, status_changed_at
            FROM users
            WHERE service IS NOT NULL
        """)
        return await cursor.fetchall()


async def update_request_status(request_id: int, new_status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE requests SET status = ? WHERE id = ?
        """, (new_status, request_id))
        await db.commit()
