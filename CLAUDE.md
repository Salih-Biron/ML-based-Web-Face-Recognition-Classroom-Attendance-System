# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

基于机器学习的 Web 人脸识别班级智能考勤系统 (ML-based Web Face Recognition Classroom Attendance System)

A C/S architecture face recognition attendance system designed for classroom settings (50-200 students), supporting flexible attendance scheduling without fixed cycles. The system runs on CPU-only Windows/Linux environments.

## Technical Stack

**Server-side (Python):**
- Flask for web framework
- DeepFace with ArcFace model for face recognition
- Face embeddings with L2 normalization
- Cosine similarity matching (default threshold: 0.22)
- Python 3.10 (recommended)

**Client-side (JavaScript):**
- Two interfaces: Teacher management page (requires login) and Student check-in page
- Real-time camera capture with 3-second intervals for face recognition
- QR code generation for mobile access

## Architecture

### Face Recognition Pipeline

```
Camera Frame → DeepFace (ArcFace) → Embedding (L2 normalized) → Cosine Similarity → Threshold (0.22) → Known/Unknown
```

### Face Database Structure

The system uses a file-based face database under `face_db/`:

```
face_db/
├── 教育技术/          # Class name (first level)
│   ├── 张三1.jpg      # Person name as filename (second level)
│   ├── 李四1.jpg
│   └── 王五1.jpg
├── 大数据/
└── 人工智能/
```

- **First level**: Class/group folders
- **Second level**: Face images (filename = person's name)
- **Supported formats**: jpg, jpeg, png, bmp, webp
- The system supports selecting single, multiple, or all classes for training and recognition

### Face Embeddings Cache Strategy

**Critical**: The system maintains class-specific embedding cache files to avoid recomputing face embeddings:

- When a single class is selected: cache filename = class name
- When multiple classes are selected: cache filename = sorted combination of selected class names
- Cache is automatically invalidated when:
  - A person is added to a class
  - A person is deleted from a class
  - A person is renamed in a class

**When implementing**: Always check for existing cache before rebuilding embeddings. This is essential for performance with 50-200 person datasets on CPU.

## Key Features & Logic

### Teacher Management Page

- **Authentication**: Default credentials `admin`/`admin123` (no registration)
- **Activity Management**: CRUD operations for attendance activities with automatic URL/QR code generation
- **Class Management**: Select single/multiple/all classes for activities
- **Person Management**: Add (single/batch upload), delete, rename people per class
- **Statistics**: View attendance duration rankings (daily, weekly, monthly, semester)
- **Semester Configuration**: Start/end dates configurable by teachers

### Student Check-in Page

**Camera Operation**: Three states - Sign In, Sign Out, Close Camera

**Recognition Logic**:
- Captures frame every 3 seconds when camera is active
- Processes ALL faces in a single frame
- Display format: `检测到人脸：X，成功标记：Y，未识别/低分：Z`

**Sign-in/Sign-out Rules**:
- **Re-sign-in**: Updates sign-in time to latest (no duplicate warning)
- **Sign-out without sign-in**: Show `${person_id}未签到，此次签退无效`
- **Normal flow**: Sign-in → Sign-out → Status changes accordingly

**Display Conventions**:
- 🟢 Green: Signed in + sign-in time
- 🔵 Blue: Signed out + sign-out time  
- 🔴 Red: Not signed in

### Duration Statistics & Auto-reset

**Calculation**: Accumulate time between each sign-out and sign-in timestamp pair (converted to hours)

**Auto-reset Schedule**:
- Daily 0:00 → Reset all to "未签到", clear daily duration
- Monday 0:00 → Clear weekly duration
- 1st of month 0:00 → Clear monthly duration
- Semester start date → Clear semester duration

## Development Guidelines

### Face Recognition Performance

- System must run on CPU (no GPU required)
- Optimize for 50-200 person recognition
- Leverage embedding cache aggressively
- Consider batch processing during initial embedding generation

### Camera & Browser Security

- Camera access requires HTTPS or localhost
- Handle user permission prompts gracefully
- Ensure cross-browser compatibility (desktop + mobile)
- Mobile responsive design required for student page

### Database Considerations

When implementing the database schema:
- Track sign-in/sign-out timestamps separately
- Store duration calculations for each time dimension (day/week/month/semester)
- Index by class, person, and timestamp for statistics queries
- Consider time-series data structure for efficient duration aggregation

### Multi-face Detection

The system MUST support detecting and recognizing multiple faces in a single camera frame. This is explicitly required in section 3.2.2: "支持识别单帧图片中的所有人脉".

## Important Constraints

- **No GPU**: All ML operations must run efficiently on CPU
- **Threshold**: Default cosine similarity threshold is 0.22 (adjustable)
- **Scale**: Design for 50-200 concurrent users per class
- **Network**: Teacher and student clients communicate via local network (LAN)
- **Time Interval**: 3-second capture interval for face recognition (non-negotiable)
