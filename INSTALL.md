# 安装指南

## 使用 Conda 虚拟环境（推荐）

### 1. 创建虚拟环境（推荐Python 3.10-3.12）
```bash
# 推荐使用Python 3.10（最稳定）
conda create -n face_attendance python=3.10 -y

# 或使用Python 3.11
# conda create -n face_attendance python=3.11 -y

# 或使用Python 3.12
# conda create -n face_attendance python=3.12 -y
```

**注意：** 如果你当前使用Python 3.14，建议降级到3.10-3.12，因为深度学习库对新版本Python的支持有延迟。

### 2. 激活环境
```bash
conda activate face_attendance
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 初始化数据库
```bash
python -c "from modules.database import init_db; init_db()"
```

### 5. 创建必要目录
```bash
mkdir face_db
mkdir face_embeddings_cache
```

### 6. 启动服务
```bash
python app.py
```

### 7. 退出环境（使用完毕后）
```bash
conda deactivate
```

---

## 使用 UV 虚拟环境

### 1. 指定Python版本创建虚拟环境

**使用Python 3.10（推荐）：**
```bash
uv venv --python 3.10
```

**使用Python 3.11：**
```bash
uv venv --python 3.11
```

**使用Python 3.12：**
```bash
uv venv --python 3.12
```

**注意：** uv会自动下载指定版本的Python（如果本地没有）

### 2. 删除现有虚拟环境（如果已创建）
```bash
# Windows
rmdir /s .venv

# Linux/Mac
rm -rf .venv
```

### 3. 重新创建虚拟环境（指定Python版本）
```bash
uv venv --python 3.10
```

### 3. 激活环境

**Windows PowerShell:**
```powershell
.venv\Scripts\Activate.ps1
```

**Windows CMD:**
```cmd
.venv\Scripts\activate.bat
```

**Linux/Mac:**
```bash
source .venv/bin/activate
```

### 4. 使用 uv 安装依赖
```bash
uv pip install -r requirements.txt
```

### 5. 初始化数据库
```bash
python -c "from modules.database import init_db; init_db()"
```

### 6. 创建必要目录
```bash
mkdir face_db
mkdir face_embeddings_cache
```

### 7. 启动服务
```bash
python app.py
```

### 8. 退出环境（使用完毕后）
```bash
deactivate
```

---

## 使用标准 venv（不需要额外工具）

### 1. 创建虚拟环境
```bash
python -m venv venv
```

### 2. 激活环境

**Windows PowerShell:**
```powershell
venv\Scripts\Activate.ps1
```

**Windows CMD:**
```cmd
venv\Scripts\activate.bat
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

### 3. 安装依赖
```bash
python -m pip install -r requirements.txt
```

### 4. 初始化数据库
```bash
python -c "from modules.database import init_db; init_db()"
```

### 5. 创建必要目录
```bash
mkdir face_db
mkdir face_embeddings_cache
```

### 6. 启动服务
```bash
python app.py
```

### 7. 退出环境（使用完毕后）
```bash
deactivate
```

---

## 启动成功标志

启动成功后，你会看到类似输出：

```
初始化数据库...
定时任务已启动
==================================================
教师端访问: http://192.168.x.x:5000/teacher/login
学生端访问: http://192.168.x.x:5000/student/<activity_id>
==================================================

 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://0.0.0.0:5000
```

然后在浏览器访问 `http://localhost:5000/teacher/login`

---

## 常见问题

### Q: 激活虚拟环境时提示"无法加载文件，因为在此系统上禁止运行脚本"

**Windows PowerShell解决方案：**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Q: 依赖安装失败，报错"Microsoft Visual C++ 14.0 is required"

**解决方案：**
1. 下载并安装 Visual Studio Build Tools
2. 或使用预编译的wheel文件
3. 或使用conda安装（conda会自动处理依赖）

### Q: TensorFlow/Keras相关错误

**解决方案：**
```bash
pip install tensorflow==2.16.1
```

### Q: 启动时没有任何输出

**排查步骤：**
1. 确认虚拟环境已激活（命令提示符前会显示环境名）
2. 确认Python版本：`python --version`（应该是3.10+）
3. 确认依赖已安装：`pip list`
4. 手动初始化数据库：`python -c "from modules.database import init_db; init_db()"`
5. 尝试运行：`python app.py`

### Q: 端口5000已被占用

**解决方案：**
修改 `app.py` 最后一行：
```python
app.run(host='0.0.0.0', port=5001, debug=True)  # 改为5001或其他端口
```

---

## 推荐环境选择

- **学习/开发**：使用 `venv`（Python自带，简单可靠）
- **数据科学项目**：使用 `conda`（处理复杂依赖更好）
- **现代Python项目**：使用 `uv`（速度快，但需要额外安装）
