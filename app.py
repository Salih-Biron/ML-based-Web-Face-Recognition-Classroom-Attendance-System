import os
import socket
from flask import Flask, request, jsonify, render_template, session, redirect
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
import config
from modules.database import init_db, get_connection
from modules.face_recognition import FaceRecognizer
from modules.scheduler import init_scheduler

app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

# 修改Jinja2分隔符，避免与Vue冲突
app.jinja_env.variable_start_string = '[['
app.jinja_env.variable_end_string = ']]'

# 初始化人脸识别器
face_recognizer = FaceRecognizer()

def get_local_ip():
    """获取本机IP地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return '127.0.0.1'

def allowed_file(filename):
    """检查文件扩展名"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS

# ==================== 基础路由 ====================

@app.route('/')
def index():
    return jsonify({"message": "Face Recognition Attendance System API", "version": "1.0"})

# ==================== 教师端路由 ====================

@app.route('/teacher/login', methods=['GET'])
def teacher_login_page():
    """教师登录页面"""
    return render_template('teacher_login.html')

@app.route('/api/teacher/login', methods=['POST'])
def teacher_login():
    """教师登录API"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'success': False, 'message': '用户名和密码不能为空'}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM teachers WHERE username = ?', (username,))
    teacher = cursor.fetchone()
    conn.close()

    if teacher and check_password_hash(teacher['password'], password):
        session['teacher_id'] = teacher['id']
        session['username'] = teacher['username']
        return jsonify({'success': True, 'message': '登录成功'})
    else:
        return jsonify({'success': False, 'message': '用户名或密码错误'}), 401

@app.route('/api/teacher/logout', methods=['POST'])
def teacher_logout():
    """教师登出API"""
    session.clear()
    return jsonify({'success': True, 'message': '已退出登录'})

@app.route('/teacher/dashboard')
def teacher_dashboard():
    """教师管理页面"""
    if 'teacher_id' not in session:
        return redirect('/teacher/login')
    return render_template('teacher_dashboard.html')

# ==================== 班级管理API ====================

@app.route('/api/classes', methods=['GET'])
def get_classes():
    """获取所有班级"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*, COUNT(s.id) as student_count
        FROM classes c
        LEFT JOIN students s ON c.id = s.class_id
        GROUP BY c.id
    ''')
    classes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(classes)

@app.route('/api/classes', methods=['POST'])
def create_class():
    """创建班级"""
    data = request.get_json()
    name = data.get('name')

    if not name:
        return jsonify({'success': False, 'message': '班级名称不能为空'}), 400

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO classes (name) VALUES (?)', (name,))
        conn.commit()
        class_id = cursor.lastrowid

        # 创建班级文件夹
        class_dir = os.path.join(config.FACE_DB_PATH, name)
        os.makedirs(class_dir, exist_ok=True)

        conn.close()
        return jsonify({'success': True, 'class_id': class_id})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/classes/<int:class_id>', methods=['DELETE'])
def delete_class(class_id):
    """删除班级"""
    conn = get_connection()
    cursor = conn.cursor()

    # 获取班级名称
    cursor.execute('SELECT name FROM classes WHERE id = ?', (class_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return jsonify({'success': False, 'message': '班级不存在'}), 404

    class_name = result['name']

    # 删除数据库记录
    cursor.execute('DELETE FROM classes WHERE id = ?', (class_id,))
    conn.commit()
    conn.close()

    # 删除班级文件夹
    class_dir = os.path.join(config.FACE_DB_PATH, class_name)
    if os.path.exists(class_dir):
        import shutil
        shutil.rmtree(class_dir)

    # 删除相关缓存
    face_recognizer.invalidate_cache(class_name)

    return jsonify({'success': True})

# ==================== 学生管理API ====================

@app.route('/api/students', methods=['GET'])
def get_students():
    """获取学生列表"""
    class_id = request.args.get('class_id')

    conn = get_connection()
    cursor = conn.cursor()

    if class_id:
        cursor.execute('''
            SELECT s.*, c.name as class_name
            FROM students s
            JOIN classes c ON s.class_id = c.id
            WHERE s.class_id = ?
            ORDER BY s.created_at DESC
        ''', (class_id,))
    else:
        cursor.execute('''
            SELECT s.*, c.name as class_name
            FROM students s
            JOIN classes c ON s.class_id = c.id
            ORDER BY s.created_at DESC
        ''')

    students = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(students)

@app.route('/api/students', methods=['POST'])
def create_student():
    """添加学生"""
    name = request.form.get('name')
    class_id = request.form.get('class_id')
    image = request.files.get('image')

    if not name or not class_id or not image:
        return jsonify({'success': False, 'message': '参数不完整'}), 400

    if not allowed_file(image.filename):
        return jsonify({'success': False, 'message': '不支持的图片格式'}), 400

    conn = get_connection()
    cursor = conn.cursor()

    # 获取班级名称
    cursor.execute('SELECT name FROM classes WHERE id = ?', (class_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return jsonify({'success': False, 'message': '班级不存在'}), 404

    class_name = result['name']

    # 保存图片
    filename = secure_filename(f"{name}.{image.filename.rsplit('.', 1)[1].lower()}")
    class_dir = os.path.join(config.FACE_DB_PATH, class_name)
    os.makedirs(class_dir, exist_ok=True)

    image_path = os.path.join(class_dir, filename)
    image.save(image_path)

    # 保存到数据库
    cursor.execute('INSERT INTO students (name, class_id, image_path) VALUES (?, ?, ?)',
                  (name, class_id, image_path))
    conn.commit()
    student_id = cursor.lastrowid

    # 初始化时长统计
    cursor.execute('INSERT INTO duration_stats (student_id) VALUES (?)', (student_id,))
    conn.commit()
    conn.close()

    # 删除班级缓存
    face_recognizer.invalidate_cache(class_name)

    return jsonify({'success': True, 'student_id': student_id})

@app.route('/api/students/<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    """删除学生"""
    conn = get_connection()
    cursor = conn.cursor()

    # 获取学生信息
    cursor.execute('''
        SELECT s.*, c.name as class_name
        FROM students s
        JOIN classes c ON s.class_id = c.id
        WHERE s.id = ?
    ''', (student_id,))
    result = cursor.fetchone()

    if not result:
        conn.close()
        return jsonify({'success': False, 'message': '学生不存在'}), 404

    image_path = result['image_path']
    class_name = result['class_name']

    # 删除数据库记录
    cursor.execute('DELETE FROM students WHERE id = ?', (student_id,))
    conn.commit()
    conn.close()

    # 删除图片文件
    if os.path.exists(image_path):
        os.remove(image_path)

    # 删除班级缓存
    face_recognizer.invalidate_cache(class_name)

    return jsonify({'success': True})

@app.route('/api/students/batch-import/<int:class_id>', methods=['POST'])
def batch_import_students(class_id):
    """批量导入学生（从face_db文件夹扫描）"""
    conn = get_connection()
    cursor = conn.cursor()

    # 获取班级信息
    cursor.execute('SELECT name FROM classes WHERE id = ?', (class_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return jsonify({'success': False, 'message': '班级不存在'}), 404

    class_name = result['name']
    class_dir = os.path.join(config.FACE_DB_PATH, class_name)

    if not os.path.exists(class_dir):
        conn.close()
        return jsonify({'success': False, 'message': f'班级文件夹不存在: {class_dir}'}), 404

    # 扫描文件夹中的图片
    imported_count = 0
    skipped_count = 0
    error_list = []

    for filename in os.listdir(class_dir):
        if not allowed_file(filename):
            continue

        # 从文件名提取学生姓名（去除扩展名）
        student_name = os.path.splitext(filename)[0]
        image_path = os.path.join(class_dir, filename)

        # 检查学生是否已存在
        cursor.execute('SELECT id FROM students WHERE name = ? AND class_id = ?', (student_name, class_id))
        existing = cursor.fetchone()

        if existing:
            skipped_count += 1
            continue

        try:
            # 添加到数据库
            cursor.execute('INSERT INTO students (name, class_id, image_path) VALUES (?, ?, ?)',
                          (student_name, class_id, image_path))
            student_id = cursor.lastrowid

            # 初始化时长统计
            cursor.execute('INSERT INTO duration_stats (student_id) VALUES (?)', (student_id,))

            imported_count += 1
        except Exception as e:
            error_list.append(f'{student_name}: {str(e)}')

    conn.commit()
    conn.close()

    # 删除班级缓存
    face_recognizer.invalidate_cache(class_name)

    return jsonify({
        'success': True,
        'imported': imported_count,
        'skipped': skipped_count,
        'errors': error_list
    })

# ==================== 活动管理API ====================

@app.route('/api/activities', methods=['GET'])
def get_activities():
    """获取所有活动"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM activities ORDER BY created_at DESC')
    activities = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(activities)

@app.route('/api/activities', methods=['POST'])
def create_activity():
    """创建活动"""
    data = request.get_json()
    name = data.get('name')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    class_ids = data.get('class_ids', [])

    if not name or not start_time or not end_time or not class_ids:
        return jsonify({'success': False, 'message': '参数不完整'}), 400

    import json
    conn = get_connection()
    cursor = conn.cursor()

    # 创建活动
    cursor.execute('''
        INSERT INTO activities (name, start_time, end_time, classes, status)
        VALUES (?, ?, ?, ?, 'pending')
    ''', (name, start_time, end_time, json.dumps(class_ids)))
    conn.commit()
    activity_id = cursor.lastrowid

    # 为所有相关学生创建签到记录
    for class_id in class_ids:
        cursor.execute('SELECT id FROM students WHERE class_id = ?', (class_id,))
        students = cursor.fetchall()
        for student in students:
            cursor.execute('''
                INSERT INTO attendance_records (activity_id, student_id, status)
                VALUES (?, ?, 'not_signed')
            ''', (activity_id, student['id']))

    conn.commit()
    conn.close()

    return jsonify({'success': True, 'activity_id': activity_id})

@app.route('/api/activities/<int:activity_id>', methods=['DELETE'])
def delete_activity(activity_id):
    """删除活动"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM activities WHERE id = ?', (activity_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/activities/<int:activity_id>/link', methods=['GET'])
def get_activity_link(activity_id):
    """获取活动签到链接"""
    local_ip = get_local_ip()
    url = f"http://{local_ip}:5000/student/{activity_id}"
    return jsonify({'url': url})

# ==================== 统计API ====================

@app.route('/api/stats/ranking', methods=['GET'])
def get_ranking():
    """获取时长排名"""
    period = request.args.get('period', 'day')
    class_id = request.args.get('class_id')

    period_map = {
        'day': 'daily_duration',
        'week': 'weekly_duration',
        'month': 'monthly_duration',
        'semester': 'semester_duration'
    }

    duration_field = period_map.get(period, 'daily_duration')

    conn = get_connection()
    cursor = conn.cursor()

    if class_id:
        cursor.execute(f'''
            SELECT s.id as student_id, s.name as student_name, c.name as class_name,
                   d.{duration_field} as duration
            FROM students s
            JOIN classes c ON s.class_id = c.id
            LEFT JOIN duration_stats d ON s.id = d.student_id
            WHERE s.class_id = ?
            ORDER BY duration DESC
        ''', (class_id,))
    else:
        cursor.execute(f'''
            SELECT s.id as student_id, s.name as student_name, c.name as class_name,
                   d.{duration_field} as duration
            FROM students s
            JOIN classes c ON s.class_id = c.id
            LEFT JOIN duration_stats d ON s.id = d.student_id
            ORDER BY duration DESC
        ''')

    stats = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(stats)

# ==================== 系统配置API ====================

@app.route('/api/config', methods=['GET'])
def get_config():
    """获取系统配置"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM system_config WHERE id = 1')
    config_data = dict(cursor.fetchone())
    conn.close()
    return jsonify(config_data)

@app.route('/api/config', methods=['POST'])
def save_config():
    """保存系统配置"""
    data = request.get_json()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE system_config
        SET semester_start_date = ?, semester_end_date = ?,
            similarity_threshold = ?, capture_interval = ?
        WHERE id = 1
    ''', (data.get('semester_start_date'), data.get('semester_end_date'),
          data.get('similarity_threshold'), data.get('capture_interval')))
    conn.commit()
    conn.close()

    return jsonify({'success': True})

# ==================== 学生端路由 ====================

@app.route('/student/<int:activity_id>')
def student_checkin(activity_id):
    """学生签到页面"""
    return render_template('student_checkin.html', activity_id=activity_id)

@app.route('/api/activity/<int:activity_id>/info', methods=['GET'])
def get_activity_info(activity_id):
    """获取活动信息"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM activities WHERE id = ?', (activity_id,))
    activity = cursor.fetchone()

    if not activity:
        conn.close()
        return jsonify({'success': False, 'message': '活动不存在'}), 404

    # 获取系统配置
    cursor.execute('SELECT capture_interval FROM system_config WHERE id = 1')
    config = cursor.fetchone()
    conn.close()

    return jsonify({
        'success': True,
        'activity': dict(activity),
        'capture_interval': config['capture_interval']
    })

@app.route('/api/recognize', methods=['POST'])
def recognize_face():
    """人脸识别API"""
    data = request.get_json()
    activity_id = data.get('activity_id')
    image_data = data.get('image')

    if not activity_id or not image_data:
        return jsonify({'success': False, 'message': '参数不完整'}), 400

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # 获取活动信息
        cursor.execute('SELECT * FROM activities WHERE id = ?', (activity_id,))
        activity = cursor.fetchone()

        if not activity:
            return jsonify({'success': False, 'message': '活动不存在'}), 404

        # 检查活动状态
        if activity['status'] != 'ongoing':
            return jsonify({'success': False, 'message': '活动未进行中'}), 400

        # 获取活动班级列表
        import json
        class_ids = json.loads(activity['classes'])

        # 获取班级名称列表
        class_names = []
        for class_id in class_ids:
            cursor.execute('SELECT name FROM classes WHERE id = ?', (class_id,))
            result = cursor.fetchone()
            if result:
                class_names.append(result['name'])

        if not class_names:
            return jsonify({'success': False, 'message': '活动未关联任何班级'}), 400

        # 人脸识别
        results = face_recognizer.recognize_faces(image_data, class_names)

        if not results:
            return jsonify({'success': False, 'message': '未识别到人脸或未匹配到学生'})

        # 更新签到记录
        recognized_students = []
        from datetime import datetime
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        for result in results:
            student_name = result['name']

            # 查找学生ID（通过name查找可能不够准确，应该直接用result中的student_id）
            # 但为了兼容性保留name查询
            cursor.execute('SELECT id FROM students WHERE name = ?', (student_name,))
            student = cursor.fetchone()

            if not student:
                continue

            student_id = student['id']

            # 检查签到记录
            cursor.execute('''
                SELECT * FROM attendance_records
                WHERE activity_id = ? AND student_id = ?
            ''', (activity_id, student_id))
            record = cursor.fetchone()

            if not record:
                # 如果没有记录，说明该学生不在此活动的班级中
                continue

            # 签到逻辑
            if record['status'] == 'not_signed':
                cursor.execute('''
                    UPDATE attendance_records
                    SET status='signed_in', signin_time=?
                    WHERE activity_id=? AND student_id=?
                ''', (now, activity_id, student_id))
                recognized_students.append({
                    'name': student_name,
                    'status': 'signed_in',
                    'confidence': result['confidence']
                })
            elif record['status'] == 'signed_in':
                # 计算时长（分钟）
                signin_dt = datetime.strptime(record['signin_time'], '%Y-%m-%d %H:%M:%S')
                signout_dt = datetime.strptime(now, '%Y-%m-%d %H:%M:%S')
                duration = int((signout_dt - signin_dt).total_seconds() / 60)

                # 防止时长为负数或异常值
                if duration < 0:
                    duration = 0

                cursor.execute('''
                    UPDATE attendance_records
                    SET status='signed_out', signout_time=?, duration=?
                    WHERE activity_id=? AND student_id=?
                ''', (now, duration, activity_id, student_id))

                # 更新时长统计
                cursor.execute('''
                    UPDATE duration_stats
                    SET daily_duration = daily_duration + ?,
                        weekly_duration = weekly_duration + ?,
                        monthly_duration = monthly_duration + ?,
                        semester_duration = semester_duration + ?
                    WHERE student_id = ?
                ''', (duration, duration, duration, duration, student_id))

                recognized_students.append({
                    'name': student_name,
                    'status': 'signed_out',
                    'confidence': result['confidence'],
                    'duration': duration
                })
            else:
                # 已完成签到签退
                recognized_students.append({
                    'name': student_name,
                    'status': 'already_completed',
                    'confidence': result['confidence']
                })

        conn.commit()

        if not recognized_students:
            return jsonify({'success': False, 'message': '识别到人脸但未匹配到活动中的学生'})

        return jsonify({
            'success': True,
            'recognized': recognized_students
        })

    except Exception as e:
        conn.rollback()
        print(f"识别错误: {e}")
        return jsonify({'success': False, 'message': f'识别失败: {str(e)}'}), 500
    finally:
        conn.close()

@app.route('/api/activity/<int:activity_id>/attendance', methods=['GET'])
def get_attendance_list(activity_id):
    """获取活动考勤列表"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT s.name as student_name, c.name as class_name,
               ar.status, ar.signin_time, ar.signout_time, ar.duration
        FROM attendance_records ar
        JOIN students s ON ar.student_id = s.id
        JOIN classes c ON s.class_id = c.id
        WHERE ar.activity_id = ?
        ORDER BY
            CASE ar.status
                WHEN 'signed_out' THEN 1
                WHEN 'signed_in' THEN 2
                WHEN 'not_signed' THEN 3
            END,
            ar.signin_time DESC
    ''', (activity_id,))

    records = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify(records)

# ==================== 后续任务中添加更多路由 ====================

if __name__ == '__main__':
    # 初始化数据库
    if not os.path.exists(config.DATABASE_PATH):
        print("初始化数据库...")
        init_db()

    # 启动定时任务
    init_scheduler()

    # 获取本机IP
    local_ip = get_local_ip()

    # 检查是否存在SSL证书
    cert_dir = os.path.join(os.path.dirname(__file__), 'certs')
    cert_file = os.path.join(cert_dir, 'cert.pem')
    key_file = os.path.join(cert_dir, 'key.pem')

    use_https = os.path.exists(cert_file) and os.path.exists(key_file)

    protocol = 'https' if use_https else 'http'
    print(f"\n{'='*50}")
    print(f"教师端访问: {protocol}://{local_ip}:5000/teacher/login")
    print(f"学生端访问: {protocol}://{local_ip}:5000/student/<activity_id>")
    if not use_https:
        print(f"\n⚠️  当前使用HTTP，摄像头可能无法在非localhost环境使用")
        print(f"💡 生成HTTPS证书: python generate_cert.py")
    else:
        print(f"\n✅ HTTPS已启用，摄像头可正常使用")
        print(f"⚠️  首次访问时浏览器会提示不安全，点击'高级'->'继续访问'")
    print(f"{'='*50}\n")

    # 启动Flask应用
    if use_https:
        app.run(host='0.0.0.0', port=5000, debug=True, ssl_context=(cert_file, key_file))
    else:
        app.run(host='0.0.0.0', port=5000, debug=True)
