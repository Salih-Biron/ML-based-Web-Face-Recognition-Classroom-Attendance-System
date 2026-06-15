from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from modules.database import get_connection

scheduler = BackgroundScheduler()

def reset_daily():
    """每日0:00重置所有人签到状态和日时长"""
    print(f"[{datetime.now()}] 执行每日重置任务")
    conn = get_connection()
    cursor = conn.cursor()

    # 重置签到状态
    cursor.execute('''
        UPDATE attendance_records
        SET status='not_signed', signin_time=NULL, signout_time=NULL
    ''')

    # 清零日时长
    cursor.execute('UPDATE duration_stats SET daily_duration=0')

    conn.commit()
    conn.close()
    print("每日重置完成")

def reset_weekly():
    """每周一0:00重置周时长"""
    print(f"[{datetime.now()}] 执行每周重置任务")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE duration_stats SET weekly_duration=0')
    conn.commit()
    conn.close()
    print("每周重置完成")

def reset_monthly():
    """每月1日0:00重置月时长"""
    print(f"[{datetime.now()}] 执行每月重置任务")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE duration_stats SET monthly_duration=0')
    conn.commit()
    conn.close()
    print("每月重置完成")

def reset_semester():
    """学期开始时重置学期时长"""
    print(f"[{datetime.now()}] 执行学期重置任务")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE duration_stats SET semester_duration=0')
    conn.commit()
    conn.close()
    print("学期重置完成")

def update_activity_status():
    """每分钟更新活动状态"""
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 更新为pending
    cursor.execute('''
        UPDATE activities
        SET status='pending'
        WHERE start_time > ?
    ''', (now,))

    # 更新为ongoing
    cursor.execute('''
        UPDATE activities
        SET status='ongoing'
        WHERE start_time <= ? AND end_time >= ?
    ''', (now, now))

    # 更新为ended
    cursor.execute('''
        UPDATE activities
        SET status='ended'
        WHERE end_time < ?
    ''', (now,))

    conn.commit()
    conn.close()

def init_scheduler():
    """初始化定时任务"""
    # 每日0:00重置
    scheduler.add_job(reset_daily, 'cron', hour=0, minute=0, id='reset_daily')

    # 每周一0:00重置
    scheduler.add_job(reset_weekly, 'cron', day_of_week='mon', hour=0, minute=0, id='reset_weekly')

    # 每月1日0:00重置
    scheduler.add_job(reset_monthly, 'cron', day=1, hour=0, minute=0, id='reset_monthly')

    # 每分钟更新活动状态
    scheduler.add_job(update_activity_status, 'interval', minutes=1, id='update_activity')

    # 启动调度器
    scheduler.start()
    print("定时任务已启动")
