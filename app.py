import os
import socket
from flask import Flask, request, jsonify, render_template, session
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
import config
from modules.database import init_db, get_connection
from modules.face_recognition import FaceRecognizer
from modules.scheduler import init_scheduler

app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

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
    print(f"\n{'='*50}")
    print(f"教师端访问: http://{local_ip}:5000/teacher/login")
    print(f"学生端访问: http://{local_ip}:5000/student/<activity_id>")
    print(f"{'='*50}\n")

    # 启动Flask应用
    app.run(host='0.0.0.0', port=5000, debug=True)
