import sqlite3
import json
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import config

def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库，创建所有表"""
    conn = get_connection()
    cursor = conn.cursor()

    # teachers表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # classes表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # students表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            class_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
        )
    ''')

    # activities表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP NOT NULL,
            classes TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # attendance_records表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id INTEGER NOT NULL,
            student_id INTEGER NOT NULL,
            signin_time TIMESTAMP,
            signout_time TIMESTAMP,
            status TEXT DEFAULT 'not_signed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
            UNIQUE(activity_id, student_id)
        )
    ''')

    # duration_stats表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS duration_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER UNIQUE NOT NULL,
            daily_duration REAL DEFAULT 0,
            weekly_duration REAL DEFAULT 0,
            monthly_duration REAL DEFAULT 0,
            semester_duration REAL DEFAULT 0,
            last_reset_date DATE,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
        )
    ''')

    # system_config表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            semester_start_date DATE NOT NULL,
            semester_end_date DATE NOT NULL,
            similarity_threshold REAL DEFAULT 0.22,
            capture_interval INTEGER DEFAULT 3,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_students_class ON students(class_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_activity ON attendance_records(activity_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance_records(student_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_activities_status ON activities(status)')

    # 插入默认教师账户 admin/admin123
    try:
        hashed_password = generate_password_hash('admin123')
        cursor.execute('INSERT INTO teachers (username, password) VALUES (?, ?)',
                      ('admin', hashed_password))
    except sqlite3.IntegrityError:
        pass  # 账户已存在

    # 插入默认系统配置
    try:
        cursor.execute('''
            INSERT INTO system_config (id, semester_start_date, semester_end_date)
            VALUES (1, '2026-09-01', '2027-01-15')
        ''')
    except sqlite3.IntegrityError:
        pass  # 配置已存在

    conn.commit()
    conn.close()
    print("数据库初始化成功！")

if __name__ == '__main__':
    init_db()
