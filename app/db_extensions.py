"""
Database extensions for TMA functionality
"""
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

def add_bonus_capsules(conn: sqlite3.Connection, user_id: int, amount: int):
    """Add bonus capsules to user"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET daily_capsules_available = daily_capsules_available + ?
            WHERE user_id = ?
        """, (amount, user_id))
        conn.commit()
        logging.info(f"Added {amount} bonus capsules to user {user_id}")
    except Exception as e:
        logging.error(f"Error adding bonus capsules: {e}")
        conn.rollback()

def remove_quarantine(conn: sqlite3.Connection, user_id: int):
    """Remove quarantine status from user"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET quarantine_until = NULL
            WHERE user_id = ?
        """, (user_id,))
        conn.commit()
        logging.info(f"Removed quarantine for user {user_id}")
    except Exception as e:
        logging.error(f"Error removing quarantine: {e}")
        conn.rollback()

def set_vip_status(conn: sqlite3.Connection, user_id: int, duration_days: int):
    """Set VIP status for user"""
    try:
        cursor = conn.cursor()
        vip_until = datetime.now() + timedelta(days=duration_days)
        
        cursor.execute("""
            UPDATE users 
            SET vip_until = ?, vip_status = 1
            WHERE user_id = ?
        """, (vip_until.isoformat(), user_id))
        conn.commit()
        logging.info(f"Set VIP status for user {user_id} until {vip_until}")
    except Exception as e:
        logging.error(f"Error setting VIP status: {e}")
        conn.rollback()

def record_purchase(conn: sqlite3.Connection, user_id: int, product_id: str, stars_amount: int):
    """Record Stars purchase in database"""
    try:
        cursor = conn.cursor()
        
        # Create purchases table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS star_purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_id TEXT,
                stars_amount INTEGER,
                purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        cursor.execute("""
            INSERT INTO star_purchases (user_id, product_id, stars_amount)
            VALUES (?, ?, ?)
        """, (user_id, product_id, stars_amount))
        
        conn.commit()
        logging.info(f"Recorded Stars purchase: user {user_id}, product {product_id}, {stars_amount} stars")
    except Exception as e:
        logging.error(f"Error recording purchase: {e}")
        conn.rollback()

def extend_database_methods():
    """Add TMA methods to Database class"""
    from app.db import Database
    
    def add_bonus_capsules_method(self, user_id: int, amount: int):
        add_bonus_capsules(self.conn, user_id, amount)
    
    def remove_quarantine_method(self, user_id: int):
        remove_quarantine(self.conn, user_id)
    
    def set_vip_status_method(self, user_id: int, duration_days: int):
        set_vip_status(self.conn, user_id, duration_days)
    
    def record_purchase_method(self, user_id: int, product_id: str, stars_amount: int):
        record_purchase(self.conn, user_id, product_id, stars_amount)
    
    # Add methods to Database class
    Database.add_bonus_capsules = add_bonus_capsules_method
    Database.remove_quarantine = remove_quarantine_method
    Database.set_vip_status = set_vip_status_method
    Database.record_purchase = record_purchase_method
    
    logging.info("✅ Extended Database with TMA methods")