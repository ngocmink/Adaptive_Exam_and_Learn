# Adaptive Exam and Learn (VISE)

Nền tảng học tập, quản lý kho tài liệu và thi trắc nghiệm trực tuyến với Flask, SQLAlchemy, PostgreSQL 16 và Supabase Storage.

## Công nghệ chính

- **Backend**: Flask 3, Flask-SQLAlchemy, Flask-Migrate (Alembic), Flask-Login, Flask-WTF (CSRF), Gunicorn.
- **Database**: PostgreSQL 16 (`unaccent`, `pg_trgm`).
- **Storage**: Supabase Storage (`materials` bucket, cấp Signed URL ngắn hạn phía server).
- **Frontend**: HTML5/Jinja2, CSS, Vanilla JS, SB Admin 2-inspired Admin Portal, Chart.js 4, MathJax 3.

## Cấu trúc chính

- `app/`: Application factory (`app/__init__.py`), auth (`app/auth/`), learner & exam (`app/library/`), admin CRUD & analytics (`app/admin/`), models (`app/models/`), seed/import CLI (`app/seed/`).
- `migrations/`: Alembic database migrations (13 bảng chuẩn ERD + Lesson hierarchy + Material storage).
- `templates/`, `asset/`, `js/`: Giao diện học viên, làm bài thi, xem kết quả, lịch sử làm bài và cổng quản trị `/admin`.
- `tests/`: Bộ kiểm thử Pytest (`test_deva.py`, `test_material_storage.py`, `test_admin_and_exam.py`, `test_sprint_acceptance_criteria.py`).

## Cài đặt & chạy local

### 1. Chuẩn bị môi trường Python

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Cấu hình biến môi trường

Sao chép `.env.example` thành `.env` và điền các giá trị phù hợp:

```powershell
Copy-Item .env.example .env
```

Các biến quan trọng:
- `DATABASE_URL`: Chuỗi kết nối PostgreSQL cho môi trường dev/staging.
- `TEST_DATABASE_URL`: Chuỗi kết nối PostgreSQL riêng cho DB test (`exam_test`).
- `SECRET_KEY`: Khóa bí mật Flask session.
- `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `SUPABASE_STORAGE_BUCKET`: Dùng cho đọc PDF riêng tư (tùy chọn khi chạy local với file URL tĩnh).

### 3. Khởi tạo PostgreSQL bằng Docker (tùy chọn)

```powershell
docker compose up -d db
```

### 4. Chạy migration & nạp dữ liệu mẫu

```powershell
# Tạo/cập nhật schema lên PostgreSQL
.\.venv\Scripts\flask.exe db upgrade

# Nạp tài khoản mẫu (admin / teacher / student) khi có biến DEMO_*_PASSWORD trong .env
.\.venv\Scripts\flask.exe seed

# Import dữ liệu môn học, bài học, tài liệu, câu hỏi, đề thi từ Excel
.\.venv\Scripts\flask.exe import-db --clean
```

### 5. Khởi động máy chủ phát triển

```powershell
.\.venv\Scripts\flask.exe run --debug
```

Truy cập `http://127.0.0.1:5000`:
- Học viên: `/login` → `/account`, `/reading?id=...`, `/quiz?id=...`, `/history`
- Admin / Giảng viên: `/login` → `/admin`

## Chạy kiểm thử tự động (Pytest)

Bộ test chỉ cho phép reset database tên `exam_test` và yêu cầu tách biệt hoàn toàn với `DATABASE_URL`:

```powershell
$env:ALLOW_TEST_DB_RESET='yes'
.\.venv\Scripts\pytest.exe -q
```

## Triển khai Staging (Render)

Cấu hình triển khai chuẩn nằm ở `render.yaml` và `Dockerfile` (PostgreSQL 16 Managed DB + Docker Web Service với health check `/health`). Các biến bí mật (`DATABASE_URL`, `SECRET_KEY`, `SUPABASE_SECRET_KEY`, `DEMO_*_PASSWORD`) được quản lý trên môi trường triển khai, không lưu trong repository.
