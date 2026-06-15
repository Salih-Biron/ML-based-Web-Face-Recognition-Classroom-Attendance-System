# 基于机器学习的 Web 人脸识别班级智能考勤系统 - 设计文档

**创建日期**: 2026-06-15
**项目类型**: 期末作业
**目标规模**: 50-200人
**部署环境**: Windows/Linux CPU环境

## 一、项目概述

### 1.1 核心需求

构建一个基于C/S架构的人脸识别考勤系统，支持：
- 教师端：登录管理、活动发布、班级/人员管理、时长统计
- 学生端：无需登录、扫码/链接访问、摄像头签到签退
- **关键特性**：单帧多人脸识别（支持5人同时签到）
- 网络要求：局域网内访问

### 1.2 使用场景

**典型流程**：
1. 教师在电脑上启动Flask服务器（如IP: 192.168.1.100:5000）
2. 教师登录管理页面，创建考勤活动并选择班级
3. 系统生成签到链接和二维码
4. 学生通过手机/电脑浏览器访问链接（需在同一WiFi下）
5. 学生打开摄像头，多人可同时站在镜头前签到
6. 系统实时反馈识别结果："检测到5张人脸，成功识别3人"
7. 学生调整位置重新识别，直到所有人完成签到

## 二、技术栈选型

### 2.1 后端技术

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.10 | 主要开发语言 |
| Flask | 2.x | Web框架 |
| SQLite | 3.x | 轻量级数据库 |
| DeepFace | latest | 人脸识别库（使用ArcFace模型）|
| APScheduler | 3.x | 定时任务调度 |

**选型理由**：
- SQLite无需额外安装数据库服务，适合单机/小规模部署
- DeepFace支持多种预训练模型，ArcFace在CPU上性能较好
- APScheduler轻量级，可在Flask进程内运行定时任务

### 2.2 前端技术

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | 3.x (CDN) | 响应式框架，自动状态管理 |
| Axios | latest (CDN) | HTTP请求库 |
| QRCode.js | latest (CDN) | 生成二维码 |
| MediaDevices API | 原生 | 调用摄像头 |

**选型理由**：
- Vue 3 CDN版本无需构建工具，直接在HTML中引入
- 自动状态管理，简化DOM更新逻辑
- 适合期末作业，代码简洁易懂

## 三、项目结构

```
python人脸识别考勤系统/
├── app.py                          # Flask主程序入口
├── config.py                       # 配置文件（数据库路径、密钥等）
├── requirements.txt                # Python依赖列表
├── database.db                     # SQLite数据库文件
├── CLAUDE.md                       # 项目开发指南
├── docs/                           # 文档目录
│   └── superpowers/
│       └── specs/
│           └── 2026-06-15-face-recognition-attendance-design.md
├── face_db/                        # 人脸库（文件系统存储）
│   ├── 教育技术/
│   │   ├── 张三.jpg
│   │   └── 李四.jpg
│   ├── 大数据/
│   └── 人工智能/
├── face_embeddings_cache/          # 人脸特征向量缓存
│   ├── 教育技术.pkl
│   ├── 大数据_人工智能.pkl         # 多班级组合缓存
│   └── ...
├── static/                         # 前端静态资源
│   ├── css/
│   │   ├── teacher.css
│   │   └── student.css
│   └── js/
│       ├── teacher.js              # 教师端Vue应用
│       └── student.js              # 学生端Vue应用
├── templates/                      # Jinja2 HTML模板
│   ├── teacher_login.html
│   ├── teacher_dashboard.html
│   └── student_checkin.html
└── modules/                        # 后端业务模块
    ├── __init__.py
    ├── face_recognition.py         # 人脸识别核心逻辑
    ├── database.py                 # 数据库操作封装
    └── scheduler.py                # 定时任务（自动重置）
```

## 四、数据库设计

### 4.1 表结构

**teachers（教师账户表）**
```sql
CREATE TABLE teachers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,  -- 存储哈希后的密码
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
-- 默认账户：admin / admin123（密码需哈希存储）
```

**classes（班级表）**
```sql
CREATE TABLE classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**students（学生表）**
```sql
CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    class_id INTEGER NOT NULL,
    image_path TEXT NOT NULL,  -- 如: face_db/教育技术/张三.jpg
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
);
```

**activities（考勤活动表）**
```sql
CREATE TABLE activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    classes TEXT NOT NULL,  -- JSON格式: "[1,2,3]"
    status TEXT DEFAULT 'pending',  -- pending/ongoing/ended
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**attendance_records（签到签退记录表）**
```sql
CREATE TABLE attendance_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    signin_time TIMESTAMP,
    signout_time TIMESTAMP,
    status TEXT DEFAULT 'not_signed',  -- not_signed/signed_in/signed_out
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    UNIQUE(activity_id, student_id)
);
```

**duration_stats（时长统计表）**
```sql
CREATE TABLE duration_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER UNIQUE NOT NULL,
    daily_duration REAL DEFAULT 0,      -- 当日累计时长（小时）
    weekly_duration REAL DEFAULT 0,     -- 本周累计时长
    monthly_duration REAL DEFAULT 0,    -- 本月累计时长
    semester_duration REAL DEFAULT 0,   -- 本学期累计时长
    last_reset_date DATE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);
```

**system_config（系统配置表）**
```sql
CREATE TABLE system_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- 单例模式
    semester_start_date DATE NOT NULL,
    semester_end_date DATE NOT NULL,
    similarity_threshold REAL DEFAULT 0.22,
    capture_interval INTEGER DEFAULT 3,  -- 截图间隔（秒）
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 索引优化

```sql
CREATE INDEX idx_students_class ON students(class_id);
CREATE INDEX idx_attendance_activity ON attendance_records(activity_id);
CREATE INDEX idx_attendance_student ON attendance_records(student_id);
CREATE INDEX idx_activities_status ON activities(status);
```

## 五、核心模块设计

### 5.1 人脸识别模块（face_recognition.py）

**职责**：
- 人脸库加载与缓存管理
- 单帧多人脸检测与识别
- 特征向量提取与相似度计算

**核心函数**：

```python
class FaceRecognizer:
    def __init__(self, db_path='face_db/', cache_dir='face_embeddings_cache/'):
        """初始化人脸识别器"""
        
    def load_face_database(self, class_names: list) -> dict:
        """
        加载人脸库
        Args:
            class_names: 班级名称列表，如['教育技术', '大数据']
        Returns:
            {student_name: embedding_vector, ...}
        """
        # 1. 生成缓存文件名：sorted(class_names)组合
        # 2. 检查缓存是否存在
        # 3. 如果存在：加载.pkl文件
        # 4. 如果不存在：遍历face_db对应班级文件夹，提取特征并缓存
        
    def recognize_faces(self, image_base64: str, face_db: dict, threshold=0.22) -> dict:
        """
        识别图片中的所有人脸
        Args:
            image_base64: Base64编码的图片
            face_db: 人脸库字典
            threshold: 相似度阈值
        Returns:
            {
                'detected': 5,  # 检测到的人脸数
                'recognized': 3,  # 识别成功的人数
                'failed': 2,  # 未识别的人脸数
                'results': [
                    {'student_name': '张三', 'student_id': 1, 'similarity': 0.89, 'success': True},
                    {'student_name': 'Unknown', 'similarity': 0.15, 'success': False},
                    ...
                ]
            }
        """
        # 1. 解码base64图片
        # 2. 使用DeepFace.extract_faces()检测所有人脸
        # 3. 对每个人脸提取特征向量
        # 4. 与face_db中所有人计算余弦相似度
        # 5. 如果最高相似度 >= threshold，标记为识别成功
        
    def invalidate_cache(self, class_names: list):
        """删除指定班级组合的所有缓存文件"""
        # 删除所有包含该班级名称的.pkl文件
```

**DeepFace配置**：
- 模型：`ArcFace`（在CPU上性能较优）
- 检测器：`opencv`（速度快，适合实时场景）
- 距离度量：`cosine`（余弦相似度）

### 5.2 定时任务模块（scheduler.py）

**职责**：自动重置签到状态和时长统计

**任务列表**：

```python
from apscheduler.schedulers.background import BackgroundScheduler

def init_scheduler(app):
    """初始化定时任务"""
    scheduler = BackgroundScheduler()
    
    # 任务1：每日0:00重置
    scheduler.add_job(reset_daily, 'cron', hour=0, minute=0)
    
    # 任务2：每周一0:00重置
    scheduler.add_job(reset_weekly, 'cron', day_of_week='mon', hour=0, minute=0)
    
    # 任务3：每月1日0:00重置
    scheduler.add_job(reset_monthly, 'cron', day=1, hour=0, minute=0)
    
    # 任务4：学期开始时重置（动态配置）
    # 从system_config读取semester_start_date，动态添加job
    
    # 任务5：每分钟更新活动状态
    scheduler.add_job(update_activity_status, 'interval', minutes=1)
    
    scheduler.start()

def reset_daily():
    """每日0:00重置所有人签到状态和日时长"""
    # UPDATE attendance_records SET status='not_signed', signin_time=NULL, signout_time=NULL
    # UPDATE duration_stats SET daily_duration=0
    
def reset_weekly():
    """每周一0:00重置周时长"""
    # UPDATE duration_stats SET weekly_duration=0
    
def reset_monthly():
    """每月1日0:00重置月时长"""
    # UPDATE duration_stats SET monthly_duration=0
    
def reset_semester():
    """学期开始时重置学期时长"""
    # UPDATE duration_stats SET semester_duration=0

def update_activity_status():
    """每分钟检查并更新活动状态"""
    # 根据当前时间与start_time/end_time对比，更新status字段
```

### 5.3 数据库操作模块（database.py）

**职责**：封装所有数据库CRUD操作

**主要函数**：
```python
def init_db():
    """初始化数据库，创建所有表"""

def get_classes():
    """获取所有班级"""

def add_student(name, class_id, image_file):
    """添加学生，保存图片到face_db，删除缓存"""

def delete_student(student_id):
    """删除学生，删除图片文件和相关缓存"""

def create_activity(name, start_time, end_time, class_ids):
    """创建活动，初始化attendance_records"""

def record_signin(activity_id, student_id):
    """记录签到，更新signin_time和status"""

def record_signout(activity_id, student_id):
    """记录签退，计算时长并更新duration_stats"""

def get_rankings(period, class_id=None):
    """获取排名数据"""
```

## 六、API接口设计

### 6.1 教师端接口

**认证接口**
```
POST /api/teacher/login
Request: {username: "admin", password: "admin123"}
Response: {success: true, token: "jwt_token"}
```

**班级管理**
```
GET /api/classes
Response: [{id: 1, name: "教育技术", student_count: 45}, ...]

POST /api/classes
Request: {name: "新班级"}
Response: {success: true, class_id: 4}

DELETE /api/classes/<id>
Response: {success: true}
```

**人员管理**
```
GET /api/students?class_id=1
Response: [{id: 1, name: "张三", class_name: "教育技术", image_path: "..."}, ...]

POST /api/students
Request: FormData(name="张三", class_id=1, image=File)
Response: {success: true, student_id: 10}

PUT /api/students/<id>
Request: {name: "新名字"}
Response: {success: true}

DELETE /api/students/<id>
Response: {success: true}
```

**活动管理**
```
GET /api/activities
Response: [{id: 1, name: "周一考勤", start_time: "...", end_time: "...", status: "ongoing", classes: [1,2]}, ...]

POST /api/activities
Request: {name: "活动名", start_time: "2026-06-15 08:00", end_time: "2026-06-15 18:00", class_ids: [1,2]}
Response: {success: true, activity_id: 5, checkin_url: "http://192.168.1.100:5000/student/5", qrcode_data: "base64..."}

PUT /api/activities/<id>
Request: {name: "新名字", start_time: "...", end_time: "..."}
Response: {success: true}

DELETE /api/activities/<id>
Response: {success: true}
```

**统计查询**
```
GET /api/stats/ranking?period=day&class_id=1
Response: [{student_name: "张三", duration: 8.5, rank: 1}, ...]
```

**系统配置**
```
GET /api/config
Response: {semester_start: "2026-09-01", semester_end: "2027-01-15", threshold: 0.22, interval: 3}

POST /api/config
Request: {semester_start: "2026-09-01", semester_end: "2027-01-15", threshold: 0.25, interval: 5}
Response: {success: true}
```

### 6.2 学生端接口

**活动信息**
```
GET /api/activity/<id>/info
Response: {name: "周一考勤", start_time: "...", end_time: "...", status: "ongoing"}
```

**人脸识别**
```
POST /api/recognize
Request: {activity_id: 5, image_base64: "data:image/jpeg;base64,...", action: "signin"}
Response: {
    detected: 5,
    recognized: 3,
    failed: 2,
    results: [
        {student_name: "张三", student_id: 1, success: true, message: "签到成功"},
        {student_name: "李四", student_id: 2, success: true, message: "签到成功"},
        {student_name: "王五", student_id: 3, success: true, message: "签到成功"},
        {student_name: "Unknown", success: false, message: "未识别"},
        {student_name: "Unknown", success: false, message: "未识别"}
    ]
}
```

**签到列表**
```
GET /api/activity/<id>/attendance
Response: [
    {student_name: "张三", status: "signed_in", signin_time: "09:15:32", signout_time: null},
    {student_name: "李四", status: "signed_out", signin_time: "09:16:10", signout_time: "10:20:15"},
    {student_name: "王五", status: "not_signed", signin_time: null, signout_time: null},
    ...
]
```

**排名查询**
```
GET /api/stats/ranking?activity_id=5&period=day
Response: [{student_name: "张三", duration: 8.5, rank: 1}, ...]
```

## 七、前端设计

### 7.1 教师端（teacher_dashboard.html）

**页面结构**：
```html
<div id="app">
  <!-- 顶部导航 -->
  <header>
    <span>欢迎 {{ username }}</span>
    <button @click="logout">退出</button>
  </header>
  
  <!-- Tab导航 -->
  <nav>
    <button @click="currentTab='activities'" :class="{active: currentTab=='activities'}">活动管理</button>
    <button @click="currentTab='classes'">班级管理</button>
    <button @click="currentTab='students'">人员管理</button>
    <button @click="currentTab='stats'">时长统计</button>
    <button @click="currentTab='config'">系统设置</button>
  </nav>
  
  <!-- 内容区 -->
  <component :is="currentTab"></component>
</div>
```

**Vue组件结构**：
```javascript
const app = Vue.createApp({
  data() {
    return {
      currentTab: 'activities',
      username: 'admin',
      activities: [],
      classes: [],
      students: [],
      selectedClasses: [],
      config: {}
    }
  },
  components: {
    'activities': ActivitiesTab,
    'classes': ClassesTab,
    'students': StudentsTab,
    'stats': StatsTab,
    'config': ConfigTab
  },
  mounted() {
    this.loadData()
  }
})
```

**关键功能**：
- 活动管理：创建活动时生成链接和二维码（使用QRCode.js）
- 班级/人员管理：支持多选、批量上传图片
- 时长统计：支持日/周/月/学期切换，表格显示排名

### 7.2 学生端（student_checkin.html）

**页面结构**：
```html
<div id="app">
  <!-- 活动信息 -->
  <header>
    <h2>{{ activityInfo.name }}</h2>
    <span :class="statusClass">{{ activityInfo.status }}</span>
  </header>
  
  <!-- 摄像头区域 -->
  <section class="camera-section">
    <video ref="video" autoplay playsinline></video>
    <canvas ref="canvas" style="display:none"></canvas>
    
    <div class="controls">
      <button @click="startCamera('signin')" :disabled="cameraActive">签到</button>
      <button @click="startCamera('signout')" :disabled="cameraActive">签退</button>
      <button @click="stopCamera" :disabled="!cameraActive">关闭摄像头</button>
    </div>
  </section>
  
  <!-- 识别结果提示 -->
  <section class="result-section">
    <p>检测到人脸：{{ recognitionResult.detected }}，成功标记：{{ recognitionResult.recognized }}，未识别/低分：{{ recognitionResult.failed }}</p>
    <p class="success-msg">{{ successMessage }}</p>
  </section>
  
  <!-- 签到人员列表 -->
  <section class="attendance-list">
    <h3>签到情况</h3>
    <div v-for="student in attendanceList" :key="student.student_id" :class="'status-' + student.status">
      <span v-if="student.status === 'signed_in'" class="green">
        🟢 {{ student.student_name }} 已签到 {{ student.signin_time }}
      </span>
      <span v-else-if="student.status === 'signed_out'" class="blue">
        🔵 {{ student.student_name }} 已签退 {{ student.signout_time }}
      </span>
      <span v-else class="red">
        🔴 {{ student.student_name }} 未签到
      </span>
    </div>
  </section>
  
  <!-- 时长排名 -->
  <section class="ranking-section">
    <h3>时长排名</h3>
    <nav>
      <button @click="currentPeriod='day'" :class="{active: currentPeriod=='day'}">日</button>
      <button @click="currentPeriod='week'">周</button>
      <button @click="currentPeriod='month'">月</button>
      <button @click="currentPeriod='semester'">学期</button>
    </nav>
    <ol>
      <li v-for="(item, index) in rankings" :key="item.student_id">
        {{ index + 1 }}. {{ item.student_name }} - {{ item.duration.toFixed(1) }}小时
      </li>
    </ol>
  </section>
</div>
```

**Vue逻辑**：
```javascript
const app = Vue.createApp({
  data() {
    return {
      activityId: null,
      activityInfo: {},
      cameraActive: false,
      currentAction: '', // 'signin' or 'signout'
      stream: null,
      captureInterval: null,
      recognitionResult: {detected: 0, recognized: 0, failed: 0},
      successMessage: '',
      attendanceList: [],
      rankings: [],
      currentPeriod: 'day'
    }
  },
  methods: {
    async startCamera(action) {
      this.currentAction = action
      this.stream = await navigator.mediaDevices.getUserMedia({video: true})
      this.$refs.video.srcObject = this.stream
      this.cameraActive = true
      
      // 每3秒截取一帧并识别
      this.captureInterval = setInterval(() => {
        this.captureAndRecognize()
      }, 3000)
    },
    
    stopCamera() {
      if (this.stream) {
        this.stream.getTracks().forEach(track => track.stop())
      }
      clearInterval(this.captureInterval)
      this.cameraActive = false
    },
    
    async captureAndRecognize() {
      const canvas = this.$refs.canvas
      const video = this.$refs.video
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      canvas.getContext('2d').drawImage(video, 0, 0)
      
      const imageBase64 = canvas.toDataURL('image/jpeg')
      
      // 发送到后端识别
      const response = await axios.post('/api/recognize', {
        activity_id: this.activityId,
        image_base64: imageBase64,
        action: this.currentAction
      })
      
      this.recognitionResult = response.data
      this.updateSuccessMessage(response.data.results)
      this.loadAttendanceList()
    },
    
    updateSuccessMessage(results) {
      const successNames = results.filter(r => r.success).map(r => r.student_name)
      if (successNames.length > 0) {
        this.successMessage = `${successNames.join('、')} ${this.currentAction === 'signin' ? '签到' : '签退'}成功。`
      }
    }
  },
  mounted() {
    this.activityId = new URLSearchParams(window.location.search).get('id')
    this.loadActivityInfo()
    this.loadAttendanceList()
    this.loadRankings()
    
    // 每5秒刷新一次签到列表
    setInterval(() => this.loadAttendanceList(), 5000)
  }
})
```

## 八、关键业务逻辑

### 8.1 签到签退逻辑

**签到流程**：
```
1. 前端每3秒发送图片到 /api/recognize (action='signin')
2. 后端识别图片中的所有人脸
3. 对每个识别成功的学生：
   - 查询 attendance_records 表
   - 如果 status='not_signed'：插入签到记录，设置 signin_time
   - 如果 status='signed_in'：更新 signin_time 为最新时间（不提示重复）
   - 如果 status='signed_out'：更新为 signed_in，更新 signin_time
4. 返回识别结果给前端
```

**签退流程**：
```
1. 前端发送图片到 /api/recognize (action='signout')
2. 后端识别图片中的所有人脸
3. 对每个识别成功的学生：
   - 查询 attendance_records 表
   - 如果 status='not_signed'：返回错误 "${student_name}未签到，此次签退无效"
   - 如果 status='signed_in'：
     a. 设置 signout_time 为当前时间
     b. 计算时长 = (signout_time - signin_time) / 3600
     c. 更新 duration_stats 表：
        - daily_duration += 时长
        - weekly_duration += 时长
        - monthly_duration += 时长
        - semester_duration += 时长
     d. 设置 status='signed_out'
   - 如果 status='signed_out'：更新 signout_time 为最新时间，重新计算时长
4. 返回识别结果给前端
```

### 8.2 人脸库缓存机制

**缓存文件命名**：
```python
# 单班级
cache_file = "教育技术.pkl"

# 多班级（按名称排序）
selected_classes = ["人工智能", "大数据", "教育技术"]
cache_file = "_".join(sorted(selected_classes)) + ".pkl"
# 结果: "人工智能_大数据_教育技术.pkl"
```

**缓存失效规则**：
```
触发条件：
1. 添加学生 → 删除该学生所在班级的所有缓存文件
2. 删除学生 → 删除该学生所在班级的所有缓存文件
3. 修改学生姓名 → 删除该学生所在班级的所有缓存文件

删除策略：
- 遍历 face_embeddings_cache/ 目录
- 删除所有包含该班级名称的 .pkl 文件
- 例如：班级"教育技术"被修改，则删除：
  - 教育技术.pkl
  - 教育技术_大数据.pkl
  - 人工智能_教育技术.pkl
  等所有相关缓存
```

### 8.3 自动重置机制

**重置任务执行时间**：
```
每日 0:00 → 重置所有人签到状态 + 清零日时长
每周一 0:00 → 清零周时长
每月1日 0:00 → 清零月时长
学期开始日 0:00 → 清零学期时长
```

**实现细节**：
```python
# 使用APScheduler的cron触发器
scheduler.add_job(reset_daily, 'cron', hour=0, minute=0)

def reset_daily():
    with db.get_connection() as conn:
        # 重置签到状态
        conn.execute("""
            UPDATE attendance_records 
            SET status='not_signed', signin_time=NULL, signout_time=NULL
        """)
        # 清零日时长
        conn.execute("UPDATE duration_stats SET daily_duration=0")
        conn.commit()
```

## 九、部署与运行

### 9.1 依赖安装

**requirements.txt**：
```
Flask==2.3.2
deepface==0.0.79
APScheduler==3.10.1
Pillow==10.0.0
opencv-python==4.8.0.74
```

安装命令：
```bash
pip install -r requirements.txt
```

### 9.2 启动流程

```bash
# 1. 初始化数据库
python -c "from modules.database import init_db; init_db()"

# 2. 创建face_db目录（如果不存在）
mkdir -p face_db face_embeddings_cache

# 3. 启动Flask应用
python app.py
```

服务器启动后：
- 教师端访问：`http://localhost:5000/teacher/login`
- 学生端访问：`http://localhost:5000/student/<activity_id>`

### 9.3 局域网访问配置

```python
# app.py
if __name__ == '__main__':
    # 监听所有网络接口，允许局域网访问
    app.run(host='0.0.0.0', port=5000, debug=True)
```

获取本机IP：
```python
import socket
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip
```

学生端访问链接示例：`http://192.168.1.100:5000/student/5`

## 十、安全与性能考虑

### 10.1 安全措施

1. **密码存储**：使用werkzeug.security的`generate_password_hash`和`check_password_hash`
2. **会话管理**：使用Flask的session机制，设置SECRET_KEY
3. **文件上传限制**：
   - 限制文件大小（如5MB）
   - 验证文件类型（仅允许jpg/jpeg/png/bmp/webp）
   - 使用安全的文件名（werkzeug.utils.secure_filename）

### 10.2 性能优化

1. **人脸库缓存**：避免每次请求都重新提取特征
2. **批量识别**：单次请求处理多张人脸，减少HTTP往返
3. **异步加载**：前端使用Vue的响应式更新，提升用户体验
4. **数据库索引**：在外键和查询频繁的字段上建立索引

### 10.3 已知限制

1. **CPU性能**：50-200人规模下，单次识别可能需要2-5秒
2. **摄像头兼容性**：不同浏览器对MediaDevices API支持不同
3. **光线影响**：弱光环境下识别率会下降
4. **HTTPS要求**：部分浏览器在非HTTPS环境下无法调用摄像头（localhost除外）

## 十一、测试建议

### 11.1 单元测试

- 测试人脸识别模块的准确率（使用测试图片集）
- 测试缓存机制的正确性
- 测试时长计算逻辑

### 11.2 集成测试

- 测试签到签退完整流程
- 测试多人同时签到场景
- 测试定时任务的触发

### 11.3 用户测试

- 不同光线条件下的识别效果
- 不同距离和角度的识别效果
- 多人拥挤场景的识别效果

## 十二、开发阶段规划

### 阶段一：核心功能（第1-2周）
1. 搭建Flask框架和数据库
2. 实现人脸识别核心模块
3. 实现人脸库加载与缓存机制

### 阶段二：教师端（第3周）
4. 教师登录功能
5. 班级管理CRUD
6. 人员管理（关联face_db文件夹）
7. 活动管理与链接生成

### 阶段三：学生端（第4周）
8. 摄像头调用与3秒间隔截图
9. 签到签退接口对接
10. 实时状态显示

### 阶段四：统计与优化（第5周）
11. 时长计算逻辑
12. 排名展示
13. 定时任务实现
14. UI优化与测试

---

**文档版本**: v1.0
**最后更新**: 2026-06-15

