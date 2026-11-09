# TỔNG HỢP NHIỆM VỤ DEV SPRINT 1 (FOUNDATION) - NHÓM 18
> **Dự án**: Adaptive Exam and Learn  
> **Cơ sở dữ liệu**: PostgreSQL 16 (chạy qua Docker)  
> **Backend Framework**: Python Flask + SQLAlchemy + Flask-Migrate  
> **Frontend**: HTML5, CSS3, JavaScript (Fetch API / AJAX) + Jinja2 Templates  
> **Quy ước API**: Tất cả API trả về JSON chuẩn: `{ success: true/false, message: "...", data: ..., pagination: ... }`

---

## MỤC LỤC
0. [⚡ NHỮNG PHẦN VIỆC ĐÃ THIẾT LẬP SẴN TRONG DỰ ÁN](#0-những-phần-việc-đã-thiết-lập-sẵn-trong-dự-án)
1. [👤 DEV 1: DATABASE ENGINEER (DBA / DB LEAD)](#1-dev-1-database-engineer-dba--db-lead---task-14)
2. [👤 DEV 2: BACKEND DEV 1 (AUTH & PHÂN QUYỀN RBAC)](#2-dev-2-backend-dev-1-auth--phân-quyền-rbac---task-16)
3. [👤 DEV 3: BACKEND DEV 2 (KHO TÀI LIỆU & ĐỀ THI - PUBLIC/STUDENT API)](#3-dev-3-backend-dev-2-kho-tài-liệu--đề-thi---task-17)
4. [👤 DEV 4: BACKEND DEV 3 (QUẢN TRỊ ADMIN / GIẢNG VIÊN CRUD)](#4-dev-4-backend-dev-3-quản-trị-admingiảng-viên-crud---task-18)
5. [🎨 DEV 5 & 6: FRONTEND DEVS (GIAO DIỆN & TÍCH HỢP)](#5-dev-5--6-frontend-devs-giao-diện--tích-hợp---task-12-16-17-18)
6. [⚙️ DEV 7: DEVOPS (MÔI TRƯỜNG & CI/CD)](#6-dev-7-devops-môi-trường--cicd---task-15)
7. [QUY TRÌNH PHỐI HỢP GIT ĐỂ KHÔNG BỊ XUNG ĐỘT](#7-quy-trình-phối-hợp-git-để-không-bị-xung-đột)

---

## 0. NHỮNG PHẦN VIỆC ĐÃ THIẾT LẬP SẴN TRONG DỰ ÁN

Để các dev không phải tạo lại từ đầu, các phần móng sau đây **ĐÃ ĐƯỢC SETUP SẴN TRONG REPO**:

1. **Môi trường PostgreSQL & pgAdmin**:
   - File `docker-compose.yml` đã tạo sẵn (chạy image `postgres:16-alpine` và `dpage/pgadmin4`).
   - File `.env.example` đã có sẵn chuỗi kết nối `DATABASE_URL`.
2. **Cấu hình & Driver**:
   - `requirements.txt` đã cập nhật: `Flask`, `Flask-SQLAlchemy`, `Flask-Migrate`, `psycopg2-binary`, `python-dotenv`.
   - `config.py` đã cấu hình connection pool và đọc biến môi trường.
   - `app/extensions.py` đã khởi tạo `db = SQLAlchemy()` và `migrate = Migrate()`.
3. **Đầy đủ 10 Models SQLAlchemy (theo đúng ERD v1)**:
   - `app/models/user.py`: Model `User` (password hashing, role `student`/`teacher`/`admin`, `study_type`).
   - `app/models/subject.py`: Model `Subject` (môn học).
   - `app/models/material.py`: Model `Material` (tài liệu học tập).
   - `app/models/question.py`: Model `Question` & `QuestionOption` (ngân hàng câu hỏi trắc nghiệm & đáp án).
   - `app/models/assessment.py`: Model `Assessment`, `AssessmentQuestion`, `Attempt`, `AttemptAnswer`, `LearningRule`.
   - `app/models/__init__.py`: Đã export toàn bộ models.
4. **Bộ Utils dùng chung**:
   - `app/utils/response_helpers.py`: Chuẩn hóa JSON response (`success_response`, `error_response`).
   - `app/utils/auth_helpers.py`: Đã viết sẵn khung decorator `@login_required`, `@role_required(['admin', 'teacher'])`, `get_current_user()`.

---

## 1. DEV 1: DATABASE ENGINEER (DBA / DB LEAD) - Task 1.4

### 📌 Trách nhiệm chính:
Thiết kế Schema CSDL chuẩn PostgreSQL với đầy đủ 10 thực thể, viết script chuyển đổi dữ liệu từ các file Excel cũ sang PostgreSQL, và tạo dữ liệu mẫu (Seed Data).

### 📁 Các file phụ trách:
- `docker-compose.yml`
- `config.py`
- `app/extensions.py`
- `app/models/` (`user.py`, `subject.py`, `material.py`, `question.py`, `assessment.py`, `__init__.py`)
- `scripts/migrate_excel_to_db.py`
- `scripts/seed_data.py`

### ✅ Checklist công việc cần code:
- [ ] **Bước 1: Khởi động PostgreSQL Local**:
  - Chạy `docker compose up -d` để bật PostgreSQL trên cổng `5432` và pgAdmin trên cổng `5050`.
- [ ] **Bước 2: Hoàn thiện 10 Models trong `app/models/`**:
  - `User`: `id`, `email` (unique, lowercase), `password_hash`, `full_name`, `phone`, `role` (`student`/`teacher`/`admin`), `study_type`, `created_at`.
  - `Subject`: `id`, `code` (unique), `name`, `description`, `is_active`.
  - `Material`: `id`, `subject_id` (FK), `title`, `description`, `file_url`, `difficulty` (`easy`/`medium`/`hard`), `author_id` (FK), `is_active`.
  - `Question`: `id`, `subject_id` (FK), `topic`, `content`, `difficulty`, `explanation`, `is_active`.
  - `QuestionOption`: `id`, `question_id` (FK), `content`, `is_correct` (boolean).
  - `Assessment`: `id`, `subject_id` (FK), `title`, `description`, `type` (`quiz`/`exam`/`practice`), `duration_minutes`, `pass_score`, `created_by` (FK), `is_active`.
  - `AssessmentQuestion`: `id`, `assessment_id` (FK), `question_id` (FK), `order_num`, `points`.
  - `Attempt`: `id`, `user_id` (FK), `assessment_id` (FK), `score`, `total_questions`, `correct_answers`, `study_time_minutes`, `exam_time_minutes`, `status`, `start_time`, `submit_time`.
  - `AttemptAnswer`: `id`, `attempt_id` (FK), `question_id` (FK), `selected_option_id` (FK), `is_correct`.
  - `LearningRule`: `id`, `subject_id` (FK), `trigger_condition`, `recommended_action`, `target_material_id` (FK).
- [ ] **Bước 3: Code script `scripts/migrate_excel_to_db.py`**:
  - Đọc dữ liệu từ `users.xlsx` $\rightarrow$ Thêm vào bảng `users`.
  - Đọc dữ liệu từ `tailieu.xlsx` $\rightarrow$ Thêm vào bảng `subjects` và `materials`.
  - Đọc dữ liệu từ `quiz.xlsx` $\rightarrow$ Tách câu hỏi vào `questions`, 4 đáp án vào `question_options` (đánh dấu đúng theo `Correct Answer`).
  - Tự động gom các câu hỏi tạo thành 1 bài `Assessment` mẫu cho mỗi môn học.
  - **Quan trọng trên PostgreSQL**: Thêm lệnh reset sequence sau khi import để ID tự tăng không bị trùng:
    ```sql
    SELECT setval(pg_get_serial_sequence('users', 'id'), coalesce(max(id)+1, 1), false) FROM users;
    SELECT setval(pg_get_serial_sequence('questions', 'id'), coalesce(max(id)+1, 1), false) FROM questions;
    ```
- [ ] **Bước 4: Code script `scripts/seed_data.py`**:
  - Tạo sẵn 3 tài khoản mặc định để team kiểm thử:
    - Admin: `admin@gmail.com` / `admin123` (`role='admin'`)
    - Giảng viên: `teacher@gmail.com` / `teacher123` (`role='teacher'`)
    - Học sinh: `student@gmail.com` / `student123` (`role='student'`)

### 🎯 Tiêu chí nghiệm thu (DoD):
Chạy `python scripts/migrate_excel_to_db.py` và `python scripts/seed_data.py` thành công; mở pgAdmin kiểm tra thấy đủ 10 bảng với dữ liệu hoàn chỉnh.

---

## 2. DEV 2: BACKEND DEV 1 (AUTH & PHÂN QUYỀN RBAC) - Task 1.6

### 📌 Trách nhiệm chính:
Xây dựng toàn bộ hệ thống xác thực, quản lý phiên làm việc (Session), băm mật khẩu bảo mật và kiểm tra phân quyền truy cập cho 3 vai trò: `student`, `teacher`, `admin`.

### 📁 Các file phụ trách:
- `app/utils/auth_helpers.py`
- `app/routes/auth_routes.py`

### ✅ Checklist công việc cần code:
- [ ] **Hàm & Decorator bảo mật (`app/utils/auth_helpers.py`)**:
  - `@login_required`: Kiểm tra `session.get('user_id')`. Nếu request từ API $\rightarrow$ trả JSON 401; nếu từ Web Browser $\rightarrow$ redirect về `/login`.
  - `@role_required(['admin', 'teacher'])`: Kiểm tra `session.get('role')`. Nếu user không đủ quyền $\rightarrow$ trả JSON 403 Forbidden.
  - `get_current_user()`: Trả về đối tượng `User` hiện tại từ DB.
- [ ] **API Đăng ký (`POST /api/auth/register`)**:
  - Request body: `{ email, password, full_name, phone, study_type }`.
  - Xử lý:
    - Validate email hợp lệ, chuyển thành chữ thường (`email.strip().lower()`).
    - Kiểm tra email đã tồn tại trong DB chưa $\rightarrow$ Báo lỗi nếu trùng.
    - Băm mật khẩu bằng `werkzeug.security.generate_password_hash`.
    - Tạo `User` với role mặc định là `student`.
- [ ] **API Đăng nhập (`POST /api/auth/login`)**:
  - Request body: `{ email, password }`.
  - Xử lý:
    - Tìm user theo email.
    - Kiểm tra mật khẩu bằng `check_password_hash`.
    - Lưu thông tin vào phiên: `session['user_id'] = user.id`, `session['role'] = user.role`, `session['email'] = user.email`, `session['full_name'] = user.full_name`.
    - Phân luồng chuyển hướng (`redirect_url`):
      - Nếu `role in ['admin', 'teacher']` $\rightarrow$ `redirect_url = '/admin'`
      - Nếu `role == 'student'` $\rightarrow$ `redirect_url = '/account'`
- [ ] **API Đăng xuất (`POST /api/auth/logout`)**:
  - Xóa sạch session (`session.clear()`).
- [ ] **API Thông tin cá nhân (`GET /api/auth/me`)**:
  - Đính kèm `@login_required`, trả về thông tin user đang đăng nhập (id, email, full_name, role, study_type).

### 🎯 Tiêu chí nghiệm thu (DoD):
Đăng ký và đăng nhập được; mật khẩu được hash trong DB; tài khoản học sinh bị chặn 403 khi gọi API admin; tài khoản admin/giảng viên được cấp phép.

---

## 3. DEV 3: BACKEND DEV 2 (KHO TÀI LIỆU & ĐỀ THI) - Task 1.7

### 📌 Trách nhiệm chính:
Xây dựng các API phục vụ trang người học: tìm kiếm tài liệu/đề thi theo từ khóa, lọc theo môn học/độ khó, và phân trang chuẩn PostgreSQL.

### 📁 Các file phụ trách:
- `app/routes/library_routes.py`

### ✅ Checklist công việc cần code:
- [ ] **API Danh sách Môn học (`GET /api/subjects`)**:
  - Lấy danh sách môn học có `is_active = True`.
  - Trả về: `id`, `code`, `name`, `description`, số lượng tài liệu và đề thi đi kèm.
- [ ] **API Kho Tài liệu (`GET /api/materials`)**:
  - Query parameters:
    - `search` (từ khóa tìm kiếm)
    - `subject_id` (lọc theo môn)
    - `difficulty` (lọc theo: `easy`, `medium`, `hard`)
    - `page` (trang hiện tại, default = 1)
    - `limit` (số bản ghi/trang, default = 9)
  - **Lưu ý PostgreSQL**: Sử dụng `.ilike()` để tìm kiếm không phân biệt hoa thường:
    ```python
    query = Material.query.filter(Material.is_active == True)
    if search:
        query = query.filter(Material.title.ilike(f"%{search}%"))
    if subject_id:
        query = query.filter(Material.subject_id == subject_id)
    if difficulty:
        query = query.filter(Material.difficulty == difficulty)
    pagination = query.order_by(Material.id.desc()).paginate(page=page, per_page=limit, error_out=False)
    ```
  - Trả về danh sách tài liệu kèm object phân trang: `{ page, limit, total_records, total_pages }`.
- [ ] **API Chi tiết Tài liệu (`GET /api/materials/<int:id>`)**:
  - Trả về chi tiết tài liệu, đường dẫn `file_url` để Frontend nhúng vào PDF Viewer.
- [ ] **API Kho Đề thi / Bài test (`GET /api/assessments`)**:
  - Hỗ trợ lọc theo `subject_id`, `type` (`quiz`, `exam`, `practice`), `search`, kèm phân trang.
  - Trả về metadata: Tên đề, môn học, thời lượng làm bài, số lượng câu hỏi, điểm đạt.
- [ ] **API Chi tiết Đề thi (`GET /api/assessments/<int:id>`)**:
  - Trả về thông tin mô tả, số câu, thời lượng (chưa trả đáp án để bảo mật).

### 🎯 Tiêu chí nghiệm thu (DoD):
Tìm kiếm đúng từ khóa (kể cả chữ hoa/thường); lọc chính xác theo môn và độ khó; phân trang trả về đúng `total_pages` và `total_records`.

---

## 4. DEV 4: BACKEND DEV 3 (QUẢN TRỊ ADMIN/GIẢNG VIÊN CRUD) - Task 1.8

### 📌 Trách nhiệm chính:
Xây dựng toàn bộ các API quản trị nội dung (Thêm, Sửa, Xóa, Bật/Tắt) cho Môn học, Tài liệu, Câu hỏi trắc nghiệm và Đề thi. Bắt buộc kiểm tra quyền Admin/Giảng viên.

### 📁 Các file phụ trách:
- `app/routes/admin_routes.py`

### ✅ Checklist công việc cần code:
- [ ] **Bảo vệ toàn bộ Blueprint**:
  - Áp dụng `@role_required(['admin', 'teacher'])` cho tất cả các endpoint bên dưới.
- [ ] **Quản lý Tài liệu (Material CRUD)**:
  - `POST /api/admin/materials`: Tạo tài liệu mới (nhận `subject_id`, `title`, `description`, `file_url`, `difficulty`).
  - `PUT /api/admin/materials/<int:id>`: Cập nhật thông tin tài liệu.
  - `DELETE /api/admin/materials/<int:id>`: Xóa mềm (`material.is_active = False`) hoặc xóa hẳn nếu chưa có ai truy cập.
- [ ] **Quản lý Ngân hàng Câu hỏi (Question & Option CRUD)**:
  - `GET /api/admin/questions`: Danh sách câu hỏi kèm phân trang và lọc theo `subject_id`, `difficulty`, `topic`.
  - `POST /api/admin/questions`: Tạo câu hỏi mới kèm **4 options** trong 1 Database Transaction:
    ```python
    try:
        new_q = Question(subject_id=..., content=..., difficulty=..., explanation=...)
        db.session.add(new_q)
        db.session.flush() # Lấy new_q.id ngay
        for opt in options_data:
            db.session.add(QuestionOption(question_id=new_q.id, content=opt['content'], is_correct=opt['is_correct']))
        db.session.commit()
    except Exception:
        db.session.rollback()
    ```
  - `PUT /api/admin/questions/<int:id>`: Sửa nội dung câu hỏi, cập nhật đáp án và giải thích.
  - `DELETE /api/admin/questions/<int:id>`: Xóa câu hỏi (kiểm tra nếu câu hỏi đã được dùng trong đề thi thì báo lỗi hoặc vô hiệu hóa `is_active = False`).
- [ ] **Quản lý Đề thi (Assessment CRUD)**:
  - `POST /api/admin/assessments`: Tạo đề thi mới, nhận danh sách `question_ids` và lưu vào bảng `AssessmentQuestion`.
  - `PUT /api/admin/assessments/<int:id>`: Cập nhật thông tin đề thi, thời gian làm bài, điểm đạt.
  - `PATCH /api/admin/assessments/<int:id>/toggle-status`: Bật/Tắt trạng thái hoạt động (`is_active = not is_active`).

### 🎯 Tiêu chí nghiệm thu (DoD):
Admin và Giảng viên thêm/sửa/xóa được nội dung; Transaction an toàn (không bị lỗi tạo câu hỏi mồ côi không có options); Người học không gọi được các API này.

---

## 5. DEV 5 & 6: FRONTEND DEVS (GIAO DIỆN & TÍCH HỢP) - Task 1.2, 1.6, 1.7, 1.8

### 📌 Trách nhiệm chính:
Nâng cấp giao diện người dùng, xử lý form validation, kết nối các API do Backend cung cấp bằng Fetch API, và hoàn thiện trải nghiệm phân luồng người dùng.

### 📁 Các file phụ trách:
- `templates/login.html` & `templates/register.html`
- `templates/account.html` (hoặc `library.html`)
- `templates/reading.html`
- `templates/admin_dashboard.html` (màn hình mới cho Admin/Giảng viên)
- `js/` (các file script frontend)

### ✅ Checklist công việc cần code:
- [ ] **Giao diện Đăng nhập / Đăng ký (`login.html`, `register.html`)**:
  - Thêm validation client: kiểm tra email hợp lệ, độ dài mật khẩu $\ge 6$ ký tự, mật khẩu nhập lại trùng khớp.
  - Thêm dropdown chọn phong cách học tập (`study_type`: Thị giác, Thính giác, Đọc/Ghi, Vận động).
  - Bắt sự kiện submit form $\rightarrow$ Gửi AJAX/Fetch đến `/api/auth/login` hoặc `/api/auth/register`.
  - Nhận `redirect_url` từ backend và chuyển hướng trang mượt mà mà không bị reload trắng trang.
  - Hiển thị Toast/Alert khi sai mật khẩu hoặc lỗi server.
- [ ] **Giao diện Kho Tài Liệu & Đề Thi (`account.html`)**:
  - **Thanh tìm kiếm & lọc**:
    - Ô input tìm kiếm theo thời gian thực (debounce 300ms gọi API).
    - Dropdown chọn Môn học (load động từ `/api/subjects`).
    - Nút chọn mức độ: Tất cả / Dễ / Trung bình / Khó.
  - **Danh sách hiển thị (Card Grid)**:
    - Card tài liệu: Hiện tiêu đề, môn học, huy hiệu độ khó, nút "Đọc tài liệu" $\rightarrow$ Chuyển sang `reading.html?id=...`.
    - Card đề thi: Hiện tiêu đề, thời lượng làm bài, số lượng câu hỏi, điểm đạt, nút "Làm bài test".
  - **Phân trang**: Thanh số trang [1, 2, 3...] click chuyển trang bằng AJAX.
- [ ] **Cổng Quản trị Admin / Giảng viên (`admin_dashboard.html`)**:
  - Thanh Sidebar điều hướng: Quản lý Tài liệu / Quản lý Ngân hàng Câu hỏi / Quản lý Đề thi.
  - Bảng dữ liệu (Data Table) kèm nút: Thêm mới, Sửa, Xóa / Vô hiệu hóa.
  - Modal form thêm nhanh câu hỏi trắc nghiệm: Ô nhập câu hỏi, 4 ô nhập đáp án A, B, C, D kèm radio button chọn đáp án đúng nhất.

---

## 6. DEV 7: DEVOPS (MÔI TRƯỜNG & CI/CD) - Task 1.5

### 📌 Trách nhiệm chính:
Cung cấp môi trường chạy chuẩn hóa, cấu hình CI trên GitHub Actions kiểm tra mã nguồn tự động, và tài liệu hóa cách chạy dự án.

### 📁 Các file phụ trách:
- `.github/workflows/ci.yml`
- `.env.example`
- `docker-compose.yml`
- `README.md`

### ✅ Checklist công việc cần làm:
- [ ] Kiểm tra file `docker-compose.yml` chạy ổn định trên các máy thành viên.
- [ ] Tạo file workflow `.github/workflows/ci.yml`:
  - Kích hoạt mỗi khi có `pull_request` vào nhánh `main` hoặc `dev`.
  - Khởi tạo service container `postgres:16`.
  - Cài đặt `requirements.txt`, chạy lệnh kiểm tra linting hoặc test cơ bản.
- [ ] Viết tài liệu `README.md` hướng dẫn 3 bước cho thành viên mới:
  1. `docker compose up -d`
  2. `pip install -r requirements.txt`
  3. `python scripts/migrate_excel_to_db.py && python scripts/seed_data.py`
  4. `python app.py`

---

## 7. QUY TRÌNH PHỐI HỢP GIT ĐỂ KHÔNG BỊ XUNG ĐỘT

Để 4-6 người cùng code mà không bị merge conflict:

1. **Phân nhánh rõ ràng**:
   - Nhánh chính: `main` (chỉ merge khi đã demo xong).
   - Nhánh tích hợp: `dev` (nhánh làm việc chung).
   - Nhánh riêng của từng người:
     - DBA: `feature/db-models-and-migrate`
     - BE 1: `feature/auth-rbac`
     - BE 2: `feature/library-api`
     - BE 3: `feature/admin-crud`
     - FE: `feature/ui-enhancement`
2. **Quy tắc sửa file**:
   - DBA hoàn thành nhánh `feature/db-models-and-migrate` và merge vào `dev` trước tiên.
   - Mỗi Backend Dev **chỉ sửa trong file route của mình** (`auth_routes.py`, `library_routes.py`, `admin_routes.py`).
   - Tuyệt đối không tự ý sửa file của người khác nếu chưa trao đổi.
   - File `app/__init__.py` chỉ cần đăng ký các blueprint một lần duy nhất.

---

*Tài liệu này được lập cho toàn bộ team kỹ thuật Nhóm 18 bám sát mục tiêu và tiêu chí nghiệm thu của Sprint 1.*
