import os

# 基础配置
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'database.db')
FACE_DB_PATH = os.path.join(BASE_DIR, 'face_db')
CACHE_DIR = os.path.join(BASE_DIR, 'face_embeddings_cache')

# Flask配置
SECRET_KEY = 'dev-secret-key-change-in-production'
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB文件上传限制

# 人脸识别配置
SIMILARITY_THRESHOLD = 0.22
DEEPFACE_MODEL = 'ArcFace'
DEEPFACE_DETECTOR = 'opencv'
DEEPFACE_DISTANCE_METRIC = 'cosine'

# 签到配置
CAPTURE_INTERVAL = 3  # 秒

# 允许的图片格式
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'bmp', 'webp'}
