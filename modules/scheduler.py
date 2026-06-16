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
    print(f"[更新活动状态] 当前时间: {now}")

    # 获取所有活动用于调试
    cursor.execute('SELECT id, name, start_time, end_time, status FROM activities')
    activities = cursor.fetchall()

    for activity in activities:
        print(f"  活动: {activity['name']}, 开始: {activity['start_time']}, 结束: {activity['end_time']}, 当前状态: {activity['status']}")

    # 使用datetime函数进行时间比较，兼容多种格式
    # 更新为pending
    cursor.execute('''
        UPDATE activities
        SET status='pending'
        WHERE datetime(start_time) > datetime(?)
    ''', (now,))
    pending_count = cursor.rowcount

    # 更新为ongoing
    cursor.execute('''
        UPDATE activities
        SET status='ongoing'
        WHERE datetime(start_time) <= datetime(?) AND datetime(end_time) >= datetime(?)
    ''', (now, now))
    ongoing_count = cursor.rowcount

    # 更新为ended
    cursor.execute('''
        UPDATE activities
        SET status='ended'
        WHERE datetime(end_time) < datetime(?)
    ''', (now,))
    ended_count = cursor.rowcount

    print(f"  更新结果: pending={pending_count}, ongoing={ongoing_count}, ended={ended_count}")

    conn.commit()
    conn.close()

def init_scheduler():
    """初始化定时任务"""
    # 立即执行一次活动状态更新
    update_activity_status()

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
