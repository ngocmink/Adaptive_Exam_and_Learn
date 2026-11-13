# Khôi phục giao diện học viên sau đăng nhập

## Mục tiêu

Sau khi đăng nhập với tài khoản học viên, người dùng đến trang `/account` có bố cục và phong cách từ `templates/account.html` cùng `asset/style.css`. Nội dung học tập lấy từ các API/database hiện tại thay vì các biến template và thao tác POST cũ. Admin/giảng viên tiếp tục dùng dashboard hiện tại ở `/admin`.

## Phạm vi

- Giữ cấu trúc giao diện cũ (header, phần giới thiệu, khóa học, FAQ/footer) và asset hiện có; sửa các đường dẫn tệp để chạy qua static endpoint của Flask.
- Nối danh sách môn học, tài liệu và đề thi với `/api/subjects`, `/api/materials`, `/api/assessments`; hiển thị trạng thái tải, rỗng và lỗi.
- Dùng `/reading?id=...` cho tài liệu, hiển thị thông tin đề thi từ API mà không để lộ câu hỏi/đáp án.
- Hiển thị tên người dùng từ `user` của route đăng nhập hiện tại; thêm đăng xuất qua endpoint hiện hành với CSRF.
- Giữ dashboard quản trị/giảng viên riêng và không đổi quyền truy cập.

## Ngoài phạm vi

- Không thay đổi schema/database, API nghiệp vụ, thuật toán học thích ứng hay nội dung thiết kế tổng thể.
- Không triển khai luồng làm bài thi mới; API hiện tại chỉ cung cấp metadata đề thi.
- Không tái sử dụng trang account cũ cho admin/giảng viên.

## Phương án đã cân nhắc

1. **Đề xuất/chọn:** dùng `account.html` làm khung trang học viên và thay các vùng nội dung khóa học bằng nội dung động từ API. Giữ lại thiết kế cũ tốt nhất, đồng thời dùng backend hiện có.
2. Giữ `library.html` làm trang chính và chỉ chuyển một phần CSS/bố cục cũ sang đó. Dễ giữ nguyên danh sách API hiện tại nhưng không khôi phục trọn giao diện người dùng đã làm.

## Ràng buộc

- Route `/account` đã yêu cầu đăng nhập; `/api/subjects`, `/api/materials`, `/api/assessments` trả dữ liệu phân trang theo envelope `success/data/pagination`.
- API đọc tài liệu và đề thi không yêu cầu đăng nhập hiện tại; trang `/reading` có đăng nhập.
- `account.html` chứa các biến không còn được route truyền (`user_email`, `tai_lieus`) và form POST cũ không còn handler; cần thay bằng dữ liệu/đường dẫn hiện hành.
- Dùng URL `url_for('static', filename=...)`, nội dung DOM từ API phải được gán an toàn, và thao tác đăng xuất phải gửi CSRF token.

## Để người triển khai quyết định

Cách bố trí nội dung động bên trong phần khóa học cũ và cách hiển thị tab lọc tài liệu/đề thi, miễn là giữ cảm nhận thị giác tổng thể, dùng API hiện có, hỗ trợ màn hình nhỏ, và có trạng thái tải/rỗng/lỗi rõ ràng.
