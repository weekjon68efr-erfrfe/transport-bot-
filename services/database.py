"""
Database service with connection pooling and transactions
"""
import sqlite3
import json
from contextlib import contextmanager
from typing import Optional, Dict, List, Any, Generator
from datetime import datetime
import threading

from config import Config
from utils.logger import logger


class DatabaseError(Exception):
    """Database error"""
    pass


class Database:
    """Thread-safe database service with connection pooling"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.db_path = Config.DATABASE_URL.replace('sqlite:///', '')
        self._local = threading.local()
        self.init_db()
        self._initialized = True
        logger.info("✅ Database service initialized")
    
    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Get thread-safe database connection"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path,
                timeout=30,
                check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row
        
        try:
            yield self._local.connection
        except Exception as e:
            logger.error(f"Database error: {e}")
            raise DatabaseError(str(e))
    
    @contextmanager
    def transaction(self):
        """Transaction context manager"""
        with self.get_connection() as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Transaction failed: {e}")
                raise DatabaseError(str(e))
    
    def init_db(self):
        """Initialize database schema"""
        with self.transaction() as conn:
            cursor = conn.cursor()
            
            # Drivers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS drivers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone TEXT UNIQUE NOT NULL,
                    full_name TEXT,
                    personal_phone TEXT,
                    truck_number TEXT,
                    is_registered BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Vehicles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vehicles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    truck_number TEXT UNIQUE NOT NULL,
                    last_weight REAL DEFAULT 0,
                    last_station TEXT,
                    last_weighing_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Weighings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS weighings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    driver_phone TEXT NOT NULL,
                    truck_number TEXT NOT NULL,
                    driver_name TEXT,
                    client_name TEXT,
                    previous_weight REAL,
                    current_weight REAL NOT NULL,
                    weight_difference REAL,
                    station_name TEXT,
                    photo_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (driver_phone) REFERENCES drivers (phone),
                    FOREIGN KEY (truck_number) REFERENCES vehicles (truck_number)
                )
            ''')
            
            # User states table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_states (
                    phone TEXT PRIMARY KEY,
                    state TEXT,
                    step TEXT,
                    temp_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Indexes for performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_weighings_truck ON weighings(truck_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_weighings_driver ON weighings(driver_phone)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_drivers_phone ON drivers(phone)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_vehicles_truck ON vehicles(truck_number)')
        
        logger.info("✅ Database schema initialized")
    
    # Driver methods
    def get_driver(self, phone: str) -> Optional[Dict]:
        """Get driver by phone"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM drivers WHERE phone = ?",
                (phone,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def is_driver_registered(self, phone: str) -> bool:
        """Check if driver is registered"""
        driver = self.get_driver(phone)
        return driver and driver.get('is_registered', 0) == 1
    
    def register_driver(self, phone: str, full_name: str, personal_phone: str, truck_number: str) -> bool:
        """Register new driver"""
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                
                # Check if driver exists
                cursor.execute("SELECT id FROM drivers WHERE phone = ?", (phone,))
                exists = cursor.fetchone()
                
                if exists:
                    # Update existing
                    cursor.execute('''
                        UPDATE drivers 
                        SET full_name = ?, personal_phone = ?, truck_number = ?, 
                            is_registered = 1, updated_at = CURRENT_TIMESTAMP
                        WHERE phone = ?
                    ''', (full_name, personal_phone, truck_number, phone))
                else:
                    # Insert new
                    cursor.execute('''
                        INSERT INTO drivers 
                        (phone, full_name, personal_phone, truck_number, is_registered)
                        VALUES (?, ?, ?, ?, 1)
                    ''', (phone, full_name, personal_phone, truck_number))
                
                # Also create/update vehicle
                cursor.execute('''
                    INSERT OR IGNORE INTO vehicles (truck_number)
                    VALUES (?)
                ''', (truck_number,))
            
            logger.info(f"Driver registered: {phone} -> {truck_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register driver {phone}: {e}")
            return False
    
    def update_driver_truck(self, phone: str, truck_number: str) -> bool:
        """Update driver's truck number"""
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE drivers 
                    SET truck_number = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE phone = ?
                ''', (truck_number, phone))
                
                # Also ensure vehicle exists
                cursor.execute('''
                    INSERT OR IGNORE INTO vehicles (truck_number)
                    VALUES (?)
                ''', (truck_number,))
            
            logger.info(f"Driver {phone} truck updated to {truck_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update driver {phone}: {e}")
            return False
    
    # Weighing methods
    def get_last_weight(self, truck_number: str) -> float:
        """Get last weight for truck"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT current_weight FROM weighings 
                WHERE truck_number = ? 
                ORDER BY created_at DESC LIMIT 1
            ''', (truck_number,))
            row = cursor.fetchone()
            return row['current_weight'] if row else 0
    
    def save_weighing(self, data: Dict) -> Optional[Dict]:
        """Save weighing report"""
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                
                # Get previous weight
                previous_weight = self.get_last_weight(data['truck_number'])
                weight_difference = data['current_weight'] - previous_weight
                
                # Insert weighing
                cursor.execute('''
                    INSERT INTO weighings 
                    (driver_phone, truck_number, driver_name, client_name, 
                     previous_weight, current_weight, weight_difference, 
                     station_name, photo_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data['driver_phone'],
                    data['truck_number'],
                    data.get('driver_name', ''),
                    data.get('client_name', ''),
                    previous_weight,
                    data['current_weight'],
                    weight_difference,
                    data.get('station_name', ''),
                    data.get('photo_path', '')
                ))
                
                # Update vehicle last weight
                cursor.execute('''
                    UPDATE vehicles 
                    SET last_weight = ?, last_weighing_date = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE truck_number = ?
                ''', (data['current_weight'], data['truck_number']))
                
                # Get inserted record
                cursor.execute(
                    "SELECT * FROM weighings WHERE rowid = last_insert_rowid()"
                )
                result = dict(cursor.fetchone())
                
                logger.info(f"Weighing saved for {data['truck_number']}: {data['current_weight']} kg")
                return result
                
        except Exception as e:
            logger.error(f"Failed to save weighing: {e}")
            return None

    def get_statistics(self, start_date: Optional[datetime] = None) -> Dict[str, List[Dict]]:
        """Get aggregated statistics by driver and by truck from start_date to now.

        Returns dict with keys 'by_driver' and 'by_truck', each a list of dicts.
        """
        params: List[Any] = []
        where_clause = ""
        if start_date:
            where_clause = "WHERE created_at >= ?"
            params.append(start_date.strftime('%Y-%m-%d %H:%M:%S'))

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # By driver
            query_driver = f"""
                SELECT driver_phone, driver_name, COUNT(*) as cnt, 
                       SUM(current_weight) as total, AVG(current_weight) as avg
                FROM weighings
                {where_clause}
                GROUP BY driver_phone
                ORDER BY cnt DESC
            """
            cursor.execute(query_driver, params)
            by_driver = []
            for row in cursor.fetchall():
                by_driver.append({
                    'driver_phone': row['driver_phone'],
                    'driver_name': row['driver_name'],
                    'count': row['cnt'],
                    'total': row['total'] or 0,
                    'avg': row['avg'] or 0
                })

            # By truck
            query_truck = f"""
                SELECT truck_number, COUNT(*) as cnt, 
                       SUM(current_weight) as total, AVG(current_weight) as avg
                FROM weighings
                {where_clause}
                GROUP BY truck_number
                ORDER BY cnt DESC
            """
            cursor.execute(query_truck, params)
            by_truck = []
            for row in cursor.fetchall():
                by_truck.append({
                    'truck_number': row['truck_number'],
                    'count': row['cnt'],
                    'total': row['total'] or 0,
                    'avg': row['avg'] or 0
                })

        return {'by_driver': by_driver, 'by_truck': by_truck}
    
    # User state methods
    def get_user_state(self, phone: str) -> Optional[Dict]:
        """Get user state"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM user_states WHERE phone = ?",
                (phone,)
            )
            row = cursor.fetchone()
            
            if row:
                state = dict(row)
                if state['temp_data']:
                    try:
                        state['temp_data'] = json.loads(state['temp_data'])
                    except:
                        state['temp_data'] = {}
                return state
            return None
    
    def set_user_state(self, phone: str, state: str, temp_data: Dict = None) -> bool:
        """Set user state"""
        try:
            temp_data_str = json.dumps(temp_data or {}, ensure_ascii=False)
            
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO user_states 
                    (phone, state, temp_data, created_at, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (phone, state, temp_data_str))
            
            logger.debug(f"User state set: {phone} -> {state}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set user state: {e}")
            return False
    
    def clear_user_state(self, phone: str) -> bool:
        """Clear user state"""
        try:
            with self.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM user_states WHERE phone = ?", (phone,))
            return True
        except Exception as e:
            logger.error(f"Failed to clear user state: {e}")
            return False