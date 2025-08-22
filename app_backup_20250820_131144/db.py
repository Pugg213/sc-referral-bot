import sqlite3
import logging
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для работы с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init(self):
        """Инициализация базы данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица пользователей
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    referrer_id INTEGER,
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    subscription_checked BOOLEAN DEFAULT FALSE,
                    subscription_date TIMESTAMP,
                    banned BOOLEAN DEFAULT FALSE,
                    ban_reason TEXT,
                    wallet_address TEXT,
                    total_earnings REAL DEFAULT 0,
                    pending_balance REAL DEFAULT 0,
                    paid_balance REAL DEFAULT 0,
                    captcha_score REAL DEFAULT 0,
                    risk_score REAL DEFAULT 0,
                    quarantine_until TIMESTAMP,
                    last_capsule_date DATE,
                    daily_capsules_opened INTEGER DEFAULT 0,
                    total_capsules_opened INTEGER DEFAULT 0,
                    total_referrals INTEGER DEFAULT 0,
                    validated_referrals INTEGER DEFAULT 0,
                    bonus_capsules INTEGER DEFAULT 0,
                    luck_multiplier REAL DEFAULT 1.0,
                    luck_expires TIMESTAMP
                )
            """)
            
            # Таблица капч
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS captcha_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    captcha_value TEXT,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    solve_time REAL,
                    solved BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблица рефералов для валидации
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS referral_validations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER,
                    referred_id INTEGER,
                    validation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    validated BOOLEAN DEFAULT FALSE,
                    risk_flags TEXT,
                    FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                    FOREIGN KEY (referred_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблица открытий капсул
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS capsule_openings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    reward_name TEXT,
                    reward_amount REAL,
                    opening_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблица выплат
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payouts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount REAL,
                    admin_id INTEGER,
                    payout_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Таблица запросов на вывод
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS withdrawal_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    admin_id INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            
            # Таблица заданий
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    reward_capsules INTEGER DEFAULT 1,
                    partner_name TEXT,
                    partner_url TEXT,
                    requirements TEXT,
                    expires_at TIMESTAMP,
                    max_completions INTEGER,
                    current_completions INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица выполнения заданий пользователями
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_task_completions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    task_id INTEGER,
                    completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reward_capsules INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (task_id) REFERENCES tasks (id),
                    UNIQUE(user_id, task_id)
                )
            """)
            
            conn.commit()
            
            # Проверяем что таблицы созданы
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            logging.info(f"Database tables created successfully: {tables}")
            
            if 'users' not in tables:
                raise Exception("Critical table 'users' was not created!")

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить пользователя по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_user(self, user_id: int, username: str = None, first_name: str = None, 
                   referrer_id: int = None) -> bool:
        """Создать нового пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (user_id, username, first_name, referrer_id)
                    VALUES (?, ?, ?, ?)
                """, (user_id, username, first_name or "Unknown", referrer_id))
                
                # Увеличиваем счетчик рефералов у реферера
                if referrer_id:
                    cursor.execute("""
                        UPDATE users SET total_referrals = total_referrals + 1 
                        WHERE user_id = ?
                    """, (referrer_id,))
                    
                    # Добавляем запись для валидации реферала
                    cursor.execute("""
                        INSERT INTO referral_validations (referrer_id, referred_id)
                        VALUES (?, ?)
                    """, (referrer_id, user_id))
                
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False

    def update_subscription_status(self, user_id: int, checked: bool = True):
        """Обновить статус проверки подписки"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET subscription_checked = ?, subscription_date = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (checked, user_id))
            conn.commit()

    def ban_user(self, user_id: int, reason: str = None):
        """Забанить пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET banned = TRUE, ban_reason = ? WHERE user_id = ?
            """, (reason, user_id))
            conn.commit()

    def unban_user(self, user_id: int):
        """Разбанить пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET banned = FALSE, ban_reason = NULL WHERE user_id = ?
            """, (user_id,))
            conn.commit()

    def update_wallet(self, user_id: int, wallet_address: str):
        """Обновить адрес кошелька"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET wallet_address = ? WHERE user_id = ?
            """, (wallet_address, user_id))
            conn.commit()

    def add_balance(self, user_id: int, amount: float):
        """Добавить к балансу пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET pending_balance = pending_balance + ?, 
                    balance = balance + ?,
                    total_earnings = total_earnings + ?
                WHERE user_id = ?
            """, (amount, amount, amount, user_id))
            conn.commit()

    def process_payout(self, user_id: int, amount: float, admin_id: int, notes: str = None):
        """Обработать выплату"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Перевести из pending в paid
            cursor.execute("""
                UPDATE users 
                SET pending_balance = pending_balance - ?, paid_balance = paid_balance + ?
                WHERE user_id = ? AND pending_balance >= ?
            """, (amount, amount, user_id, amount))
            
            if cursor.rowcount > 0:
                # Записать выплату
                cursor.execute("""
                    INSERT INTO payouts (user_id, amount, admin_id, notes)
                    VALUES (?, ?, ?, ?)
                """, (user_id, amount, admin_id, notes))
                conn.commit()
                return True
            return False

    def get_top_users(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получить топ пользователей по заработку"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT user_id, username, first_name, total_earnings, validated_referrals
                FROM users 
                WHERE banned = FALSE
                ORDER BY total_earnings DESC 
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> Dict[str, Any]:
        """Получить общую статистику"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Общие статистики
            cursor.execute("SELECT COUNT(*) as total_users FROM users")
            total_users = cursor.fetchone()['total_users']
            
            cursor.execute("SELECT COUNT(*) as active_users FROM users WHERE subscription_checked = TRUE AND banned = FALSE")
            active_users = cursor.fetchone()['active_users']
            
            cursor.execute("SELECT SUM(total_earnings) as total_earned FROM users")
            total_earned = cursor.fetchone()['total_earned'] or 0
            
            cursor.execute("SELECT SUM(pending_balance) as pending_balance FROM users")
            pending_balance = cursor.fetchone()['pending_balance'] or 0
            
            cursor.execute("SELECT COUNT(*) as total_capsules FROM capsule_openings")
            total_capsules = cursor.fetchone()['total_capsules']
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'total_earned': total_earned,
                'pending_balance': pending_balance,
                'total_capsules': total_capsules
            }

    def reset_daily_capsules(self):
        """Сброс дневного лимита капсул (вызывается ежедневно)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET daily_capsules_opened = 0
                WHERE last_capsule_date < DATE('now')
            """)
            conn.commit()

    def can_open_capsule(self, user_id: int, daily_limit: int) -> bool:
        """Проверить, может ли пользователь открыть капсулу"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT daily_capsules_opened, last_capsule_date, validated_referrals
                FROM users WHERE user_id = ?
            """, (user_id,))
            row = cursor.fetchone()
            if not row:
                return False
            
            # Базовая капсула + по 1 за каждого реферала
            referral_bonus = row['validated_referrals'] if row['validated_referrals'] else 0
            total_daily_limit = 1 + referral_bonus  # 1 базовая + рефералы
            
            # Если дата не сегодня, сбрасываем счетчик
            today = datetime.now().date()
            last_date = datetime.strptime(row['last_capsule_date'], '%Y-%m-%d').date() if row['last_capsule_date'] else None
            
            if last_date != today:
                return True
                
            return row['daily_capsules_opened'] < total_daily_limit

    def record_capsule_opening(self, user_id: int, reward_name: str, reward_amount: float):
        """Записать открытие капсулы"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Записать открытие
            cursor.execute("""
                INSERT INTO capsule_openings (user_id, reward_name, reward_amount)
                VALUES (?, ?, ?)
            """, (user_id, reward_name, reward_amount))
            
            # Обновить счетчики пользователя
            cursor.execute("""
                UPDATE users 
                SET daily_capsules_opened = daily_capsules_opened + 1,
                    total_capsules_opened = total_capsules_opened + 1,
                    last_capsule_date = DATE('now')
                WHERE user_id = ?
            """, (user_id,))
            
            conn.commit()
    
    def create_withdrawal_request(self, user_id: int, amount: float) -> int:
        """Создать запрос на вывод средств"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO withdrawal_requests (user_id, amount, status)
                VALUES (?, ?, 'pending')
            """, (user_id, amount))
            conn.commit()
            return cursor.lastrowid
    
    def get_withdrawal_requests(self, status: str = 'pending') -> List[Dict[str, Any]]:
        """Получить запросы на вывод средств"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT wr.id, wr.user_id, wr.amount, wr.status, wr.created_at,
                       u.username, u.first_name, u.wallet_address, u.pending_balance
                FROM withdrawal_requests wr
                JOIN users u ON wr.user_id = u.user_id
                WHERE wr.status = ?
                ORDER BY wr.created_at ASC
            """, (status,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_user_withdrawal_requests(self, user_id: int) -> List[Dict[str, Any]]:
        """Получить активные запросы пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, amount, status, created_at
                FROM withdrawal_requests
                WHERE user_id = ? AND status = 'pending'
                ORDER BY created_at DESC
            """, (user_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def process_withdrawal_request(self, request_id: int, admin_id: int) -> bool:
        """Обработать запрос на вывод"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получить детали запроса
            cursor.execute("""
                SELECT user_id, amount FROM withdrawal_requests 
                WHERE id = ? AND status = 'pending'
            """, (request_id,))
            request = cursor.fetchone()
            
            if not request:
                return False
            
            user_id, amount = request['user_id'], request['amount']
            
            # Проверить баланс пользователя
            cursor.execute("SELECT pending_balance FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()
            
            if not user or user['pending_balance'] < amount:
                return False
            
            # Обновить балансы
            cursor.execute("""
                UPDATE users 
                SET pending_balance = pending_balance - ?, 
                    paid_balance = paid_balance + ?
                WHERE user_id = ?
            """, (amount, amount, user_id))
            
            # Отметить запрос как выполненный
            cursor.execute("""
                UPDATE withdrawal_requests 
                SET status = 'completed', processed_at = CURRENT_TIMESTAMP, admin_id = ?
                WHERE id = ?
            """, (admin_id, request_id))
            
            # Записать в историю выплат
            cursor.execute("""
                INSERT INTO payouts (user_id, amount, admin_id, notes)
                VALUES (?, ?, ?, ?)
            """, (user_id, amount, admin_id, f"Withdrawal request #{request_id}"))
            
            conn.commit()
            return True

    def save_captcha_session(self, user_id: int, captcha_value: str) -> int:
        """Сохранить сессию капчи"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO captcha_sessions (user_id, captcha_value)
                VALUES (?, ?)
            """, (user_id, captcha_value))
            conn.commit()
            return cursor.lastrowid

    def complete_captcha(self, session_id: int, solve_time: float) -> bool:
        """Завершить решение капчи"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE captcha_sessions 
                SET solved = TRUE, solve_time = ?
                WHERE id = ? AND solved = FALSE
            """, (solve_time, session_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_captcha_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Получить сессию капчи"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM captcha_sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_task_completions(self, task_id: int) -> List[Dict[str, Any]]:
        """Получить список пользователей, выполнивших задание"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.user_id, u.username, u.first_name, ut.completed_at, ut.reward_capsules
                FROM user_tasks ut
                JOIN users u ON ut.user_id = u.user_id
                WHERE ut.task_id = ?
                ORDER BY ut.completed_at DESC
            """, (task_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def deactivate_task(self, task_id: int) -> bool:
        """Деактивировать задание"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE tasks SET status = 'inactive' WHERE id = ?
            """, (task_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Получить задание по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_user_scores(self, user_id: int, captcha_score: float = None, risk_score: float = None):
        """Обновить скоры пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            updates = []
            params = []
            
            if captcha_score is not None:
                updates.append("captcha_score = ?")
                params.append(captcha_score)
                
            if risk_score is not None:
                updates.append("risk_score = ?")
                params.append(risk_score)
                
            if updates:
                params.append(user_id)
                cursor.execute(f"""
                    UPDATE users SET {', '.join(updates)} WHERE user_id = ?
                """, params)
                conn.commit()

    def set_quarantine(self, user_id: int, hours: int):
        """Установить карантин пользователю"""
        quarantine_until = datetime.now() + timedelta(hours=hours)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET quarantine_until = ? WHERE user_id = ?
            """, (quarantine_until, user_id))
            conn.commit()

    def is_in_quarantine(self, user_id: int) -> bool:
        """Проверить, находится ли пользователь в карантине"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT quarantine_until FROM users WHERE user_id = ?
            """, (user_id,))
            row = cursor.fetchone()
            if not row or not row['quarantine_until']:
                return False
                
            quarantine_until = datetime.fromisoformat(row['quarantine_until'])
            return datetime.now() < quarantine_until

    def get_pending_validations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Получить список рефералов для валидации"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT rv.*, u.user_id, u.username, u.first_name, u.registration_date,
                       u.subscription_checked, u.captcha_score, u.risk_score
                FROM referral_validations rv
                JOIN users u ON rv.referred_id = u.user_id
                WHERE rv.validated = FALSE
                ORDER BY rv.validation_date ASC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def validate_referral(self, validation_id: int, validated: bool, risk_flags: str = None):
        """Подтвердить или отклонить реферала"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Обновить статус валидации
            cursor.execute("""
                UPDATE referral_validations 
                SET validated = ?, risk_flags = ?
                WHERE id = ?
            """, (validated, risk_flags, validation_id))
            
            if validated:
                # Увеличить счетчик валидированных рефералов
                # Получить referrer_id для награды
                cursor.execute("SELECT referrer_id FROM referral_validations WHERE id = ?", (validation_id,))
                referrer_result = cursor.fetchone()
                
                if referrer_result:
                    referrer_id = referrer_result['referrer_id']
                    
                    # Обновить счетчик валидированных рефералов
                    cursor.execute("""
                        UPDATE users 
                        SET validated_referrals = validated_referrals + 1
                        WHERE user_id = ?
                    """, (referrer_id,))
                    
                    # ДОБАВИТЬ НАГРАДУ ЗА РЕФЕРАЛА: 1.0 SC
                    referral_reward = 1.0
                    cursor.execute("""
                        UPDATE users 
                        SET balance = balance + ?, 
                            pending_balance = pending_balance + ?,
                            total_earnings = total_earnings + ?
                        WHERE user_id = ?
                    """, (referral_reward, referral_reward, referral_reward, referrer_id))
            
            conn.commit()
    
    # Методы для системы заданий
    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Получить активные задания"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tasks 
                WHERE status = 'active' 
                AND (expires_at IS NULL OR expires_at > datetime('now'))
                ORDER BY created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        """Получить задание по ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_user_completed_tasks(self, user_id: int) -> List[Dict[str, Any]]:
        """Получить выполненные пользователем задания"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT utc.*, t.title, t.description, t.partner_name
                FROM user_task_completions utc
                JOIN tasks t ON utc.task_id = t.id
                WHERE utc.user_id = ?
                ORDER BY utc.completed_at DESC
            """, (user_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def is_task_completed(self, user_id: int, task_id: int) -> bool:
        """Проверить выполнено ли задание пользователем"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM user_task_completions 
                WHERE user_id = ? AND task_id = ?
            """, (user_id, task_id))
            return cursor.fetchone() is not None
    
    def complete_user_task(self, user_id: int, task_id: int, reward_capsules: int = 1):
        """Отметить задание как выполненное"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_task_completions (user_id, task_id, reward_capsules)
                VALUES (?, ?, ?)
            """, (user_id, task_id, reward_capsules))
            
            # Увеличить счетчик выполнений задания
            cursor.execute("""
                UPDATE tasks SET current_completions = current_completions + 1
                WHERE id = ?
            """, (task_id,))
            
            conn.commit()
    
    def add_task(self, title: str, description: str, task_type: str, reward_capsules: int = 1,
                 partner_name: str = "", partner_url: str = "", requirements: str = "",
                 expires_at: str = None, max_completions: int = None) -> int:
        """Добавить новое задание"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks (title, description, task_type, reward_capsules, 
                                 partner_name, partner_url, requirements, expires_at, max_completions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (title, description, task_type, reward_capsules, partner_name, 
                  partner_url, requirements, expires_at, max_completions))
            
            task_id = cursor.lastrowid
            conn.commit()
            return task_id
    
    def add_bonus_capsules(self, user_id: int, amount: int):
        """Добавить бонусные капсулы пользователю"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET bonus_capsules = bonus_capsules + ?
                WHERE user_id = ?
            """, (amount, user_id))
            conn.commit()

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Получить все задания (включая неактивные)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks ORDER BY id DESC")
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_task(self, task_id: int) -> bool:
        """Удалить задание из базы данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0
