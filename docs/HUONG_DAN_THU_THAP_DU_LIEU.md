# Hướng dẫn thu thập và xử lý dữ liệu

**Dự án:** Adaptive Exam and Learn
**Dành cho:** Thành viên thu thập nội dung, người kiểm duyệt và Dev A phụ trách cơ sở dữ liệu
**Phiên bản:** 1.1 — ngày 15/11/2026

Tài liệu này hướng dẫn cách biến các file PDF thành tài liệu học tập và ngân hàng câu hỏi có thể sử dụng trên website. Người thu thập chỉ cần chuẩn bị file, điền bảng thông tin và kiểm tra nội dung; Dev A phụ trách lưu file, chuyển dữ liệu vào database và kiểm tra trên hệ thống.

**Đầu ra cần bàn giao:** một thư mục PDF, một workbook Excel mô tả nội dung và các liên kết, cùng danh sách vấn đề chưa xác minh. Không cần tài khoản Render, mật khẩu database hay thao tác SQL để thu thập dữ liệu.

## 1. Hiểu nhanh hệ thống đang lưu những gì

Website phục vụ hai việc: đọc tài liệu theo môn học và làm bài kiểm tra để nhận kết quả, gợi ý ôn tập. Database PostgreSQL lưu thông tin có cấu trúc; PDF được lưu riêng và database lưu đường dẫn tới file.

```text
Môn học
├── Bài học được tổ chức như một chương
│   ├── Liên kết tới tài liệu PDF
│   └── Liên kết tới câu hỏi luyện tập
├── Kho tài liệu của môn
├── Ngân hàng câu hỏi của môn
│   └── Các phương án trả lời và đáp án đúng
└── Đề kiểm tra của môn
    └── Danh sách câu hỏi theo thứ tự và điểm số

Người học làm đề → Lượt làm bài → Câu trả lời → Kết quả
```

Ví dụ: môn **Giải tích 1** có bài **Giới hạn của dãy số**, được tổ chức trực tiếp dưới môn. Bài học liên kết tới một PDF lý thuyết và các câu hỏi phù hợp. Một đề kiểm tra có thể chọn câu hỏi từ nhiều bài học trong cùng môn.

Một tài liệu hoặc câu hỏi có thể liên kết với nhiều bài học trong cùng môn. Chỉ lưu một bản nội dung rồi khai báo các liên kết; không tạo nhiều bản giống nhau chỉ vì dùng ở nhiều bài học.

### Các nhóm bảng hiện có

| Nhóm | Các bảng | Người thu thập cần chuẩn bị |
|---|---|---|
| Cấu trúc học tập | `subjects`, `lessons` | Tên môn, bài học, thứ tự và mục tiêu học |
| Tài liệu | `materials`, `lesson_materials` | PDF, thông tin mô tả và bài học liên quan |
| Câu hỏi | `questions`, `question_options`, `question_lessons` | Câu hỏi, 4 lựa chọn, 1 đáp án đúng, lời giải và bài học liên quan |
| Đề kiểm tra | `assessments`, `assessment_questions` | Tên đề, thời lượng, các câu hỏi, thứ tự và điểm |
| Hoạt động người học | `users`, `attempts`, `attempt_answers` | Không thu thập trong đợt nội dung này; tài khoản và lượt làm bài do hệ thống quản lý |
| Gợi ý học tập | `learning_rules` | Có thể đề xuất tài liệu phù hợp cho từng bài; Dev A và nhóm chức năng thống nhất quy tắc sau |

Thiết kế mới có 13 bảng ứng dụng và bảng kỹ thuật `alembic_version`. Không có bảng chương riêng; mỗi bài học đóng vai trò một chương trực thuộc môn. Migration `20261115_01` đã được chuẩn bị và kiểm thử; database cloud chỉ đổi khi triển khai migration cùng code tương ứng. Việc có bảng chưa đồng nghĩa giao diện và API bài học đã hoàn thiện. Tài liệu không còn liên kết tới tài khoản tác giả/người upload; vẫn phải thu thập nguồn và tác giả gốc của PDF.


## 2. Phân chia công việc

| Vai trò | Công việc | Sản phẩm bàn giao |
|---|---|---|
| Người thu thập | Tìm nguồn, tổ chức PDF, nhập thông tin, trích câu hỏi | PDF và workbook đã điền |
| Người kiểm duyệt nội dung | Đối chiếu nguồn, kiểm tra đáp án, công thức, mức độ và phân loại | Dữ liệu đã duyệt hoặc ghi rõ lỗi cần sửa |
| Dev A | Kiểm tra định dạng, xử lý mã liên kết, lưu file và import dữ liệu | Báo cáo nhập thành công và lỗi theo dòng |
| QA hoặc người kiểm tra | Mở tài liệu, làm đề mẫu, đối chiếu kết quả | Danh sách lỗi hiển thị và lỗi nội dung |

Nên phân công một người chịu trách nhiệm chính cho từng môn. Người kiểm duyệt nên khác người nhập để giảm lỗi bỏ sót.

## 3. Làm một bộ nhỏ trước

Trước khi thu thập hàng loạt, chuẩn bị một bộ mẫu gồm:

- 1 môn học.
- 2 bài học trực tiếp thuộc môn.
- 2–3 PDF phù hợp.
- 10 câu hỏi đã kiểm duyệt, mỗi câu có 4 lựa chọn và đúng 1 đáp án đúng.
- 1 đề mẫu sử dụng các câu hỏi đó.

Mục đích là kiểm tra cách đặt mã, định dạng nội dung, mở PDF và chấm điểm. Chỉ mở rộng sau khi bộ mẫu nhập và sử dụng được trên website. Số lượng trên là đề xuất cho vòng thử, không phải giới hạn của hệ thống.

## 4. Thu thập và kiểm tra PDF

### Bước 1 — Chọn nguồn

Ưu tiên giáo trình, bài giảng hoặc đề có nguồn rõ ràng và được phép sử dụng trong dự án. Ghi lại tên tài liệu, tác giả hoặc đơn vị phát hành, đường dẫn nguồn nếu có và ghi chú quyền sử dụng. Nếu chưa rõ quyền chia sẻ, đánh dấu để kiểm tra trước khi đưa lên website công khai.

Không thu thập file bị khóa không đọc được, thiếu trang quan trọng hoặc có chất lượng quá thấp để kiểm tra đáp án. Nếu file chứa thông tin cá nhân không cần thiết, chuẩn bị một bản đã loại bỏ thông tin đó trước khi bàn giao để đăng tải.

### Bước 2 — Phân loại

- **Tài liệu học:** lý thuyết, bài giảng, ví dụ có lời giải.
- **Nguồn câu hỏi:** đề thi, bài tập, bộ trắc nghiệm.
- **Kết hợp:** vừa lưu PDF làm tài liệu, vừa trích các câu phù hợp vào ngân hàng câu hỏi.

Một PDF đề thi chưa thể trở thành bài kiểm tra tự chấm điểm chỉ bằng cách tải file lên. Hệ thống cần nội dung từng câu, các lựa chọn và đáp án đúng riêng biệt.

### Bước 3 — Kiểm tra khả năng trích xuất

Thử bôi đen và sao chép một đoạn văn trong PDF. Nếu sao chép được đúng chữ, có thể dùng nội dung đó làm bản nháp. Nếu PDF là ảnh scan, cần OCR để nhận dạng chữ rồi kiểm tra lại bằng mắt.

Đặc biệt chú ý dấu tiếng Việt, dấu âm, phân số, số mũ, căn, chỉ số, đơn vị và các ký hiệu gần giống nhau như 0/O hoặc 1/l. Công thức và hình vẽ phải được đối chiếu với trang gốc.

### Bước 4 — Đặt tên và lưu file

Giữ bản gốc riêng. Đặt tên bản dùng để import bằng chữ không dấu, số và dấu gạch ngang; dùng tên ngắn nhưng đủ hiểu. Tiêu đề hiển thị trong Excel vẫn viết tiếng Việt đầy đủ.

```text
ban-giao-data/
├── README.txt
├── noi-dung.xlsx
├── pdf/
│   └── GT1/
│       ├── GT1-TL001-gioi-han-day-so.pdf
│       └── GT1-TL002-bai-tap-gioi-han.pdf
└── media/
    └── GT1-Q005-hinh-01.png
```

Chỉ tạo thư mục `media` khi câu hỏi có hình. Tên file hình phải được ghi trong câu hỏi hoặc ghi chú để Dev A xử lý. Khả năng hiển thị hình và công thức cần được thử trên giao diện thực tế trước khi nhập hàng loạt.

## 5. Quy tắc chung khi điền Excel

Các sheet dưới đây là **quy ước bàn giao đề xuất**, chưa phải cam kết rằng lệnh import hiện tại đọc được nguyên workbook này. Dev A cần bổ sung hoặc điều chỉnh importer theo cấu trúc đã thống nhất trước lần nhập đầu tiên.

- Mỗi dòng là một bản ghi; hàng đầu là tên cột. Không gộp ô và không dùng màu ô thay cho dữ liệu.
- Dùng mã ổn định để liên kết các sheet. Không tự điền ID số của database.
- Không đổi mã của bản ghi đã bàn giao mà không báo Dev A. Sửa nội dung thì giữ mã và ghi rõ thay đổi.
- Không dùng ô trống để ám chỉ “giống dòng trên”. Điền đầy đủ mã liên kết ở mỗi dòng.
- Ngày ghi theo dạng `YYYY-MM-DD`. Trang PDF ghi theo số trang trên trình đọc; nếu khác số in trên tài liệu, ghi cả hai trong chú thích.
- Dùng `review_status`: `draft` là đang soạn, `needs_review` là chờ duyệt, `approved` là đã duyệt. Đây là trạng thái kiểm duyệt trong workbook, không phải một cột đã có ở tất cả bảng database.
- `draft`, `published`, `archived` là các giá trị trạng thái riêng của bài học trong database. Dev A quyết định chuyển trạng thái sau kiểm tra.

Đề xuất mã có tiền tố môn để dễ đối chiếu: môn `GT1`, bài `GT1-L01`, tài liệu `GT1-TL001`, câu hỏi `GT1-Q001`, đề `GT1-DE001`. Mã tài liệu, câu hỏi và đề là mã quản lý trong gói bàn giao; các bảng hiện tại chưa có cột mã tương ứng, nên importer cần quản lý cách đối chiếu khi nhập lại.

## 6. Điền cấu trúc môn và bài học

### Sheet Subjects

| Cột | Cách điền | Ví dụ |
|---|---|---|
| `subject_code` | Mã môn duy nhất | GT1 |
| `name` | Tên môn đầy đủ | Giải tích 1 |
| `description` | Mô tả ngắn phạm vi môn | Giới hạn và đạo hàm cơ bản |

### Sheet Lessons

| Cột | Cách điền | Ví dụ |
|---|---|---|
| `lesson_code` | Mã bài học | GT1-L01 |
| `subject_code` | Môn chứa bài học | GT1 |
| `title` | Tên bài học | Giới hạn của dãy số |
| `objectives` | Sau bài này người học làm được gì | Tính giới hạn của một số dãy cơ bản |
| `content` | Tóm tắt tự biên soạn nếu có; có thể để trống | Các khái niệm và ví dụ chính |
| `order_num` | Số nguyên dương, thứ tự trong môn | 1 |

Không tạo bài học theo tên từng file nếu cách chia đó không hợp lý về kiến thức. Một bài học có thể dùng nhiều PDF; một PDF dài cũng có thể phục vụ nhiều bài học.

## 7. Điền thông tin tài liệu và liên kết

### Sheet Materials

| Cột | Cách điền |
|---|---|
| `material_code` | Mã tài liệu, ví dụ GT1-TL001 |
| `subject_code` | Môn sở hữu tài liệu |
| `title` | Tên hiển thị trên website |
| `relative_path` | Đường dẫn trong gói bàn giao, ví dụ pdf/GT1/GT1-TL001-gioi-han-day-so.pdf |
| `description` | Nội dung chính, đối tượng phù hợp và phạm vi sử dụng |
| `difficulty` | Mức độ dự kiến từ 1 đến 10; người kiểm duyệt xác nhận |
| `source_title` | Tên tài liệu gốc |
| `source_author` | Tác giả hoặc đơn vị phát hành nếu biết |
| `source_url` | Đường dẫn nguồn nếu có |
| `usage_note` | Ghi chú quyền sử dụng hoặc vấn đề cần xác minh |
| `review_status` | draft, needs_review hoặc approved |

Các trường nguồn và quyền sử dụng là hồ sơ bàn giao, chưa phải toàn bộ đều có cột riêng trong database. Không điền đường dẫn cá nhân như `C:\Users\...` vào `file_url`; Dev A tạo đường dẫn lưu trữ phù hợp khi upload.

### Sheet LessonMaterials

| Cột | Cách điền | Ví dụ |
|---|---|---|
| `lesson_code` | Bài học sử dụng tài liệu | GT1-L01 |
| `material_code` | Tài liệu đã khai báo | GT1-TL001 |
| `order_num` | Thứ tự tài liệu trong bài | 1 |
| `page_note` | Trang nên đọc trong PDF | Trang PDF 5–12, tương ứng trang in 1–8 |

Mỗi cặp bài học và tài liệu chỉ xuất hiện một lần. `page_note` phục vụ đối chiếu; liên kết hiện tại chưa có cột trang riêng. Với tài liệu nhiều phần, có thể liên kết cùng file tới nhiều bài và ghi trang tương ứng, không cần tự chia file ngay.

## 8. Trích xuất và kiểm duyệt câu hỏi

### Sheet Questions

| Cột | Cách điền |
|---|---|
| `question_code` | Mã câu hỏi ổn định, ví dụ GT1-Q001 |
| `subject_code` | Môn của câu hỏi |
| `topic` | Chủ đề ngắn và nhất quán, ví dụ Giới hạn của dãy số |
| `content` | Toàn bộ đề bài, gồm điều kiện và đơn vị |
| `option_a`, `option_b`, `option_c`, `option_d` | Nội dung 4 lựa chọn, mỗi lựa chọn một ô |
| `correct_option` | Chỉ một trong A, B, C, D |
| `explanation` | Giải thích cách làm hoặc lý do đáp án đúng |
| `difficulty` | Số từ 1 đến 10 |
| `source_material_code` | Mã tài liệu nguồn nếu đã khai báo trong Materials |
| `source_page` | Trang PDF để người duyệt tìm lại |
| `source_question` | Số câu hoặc tên mục trong bản gốc |
| `media_files` | Tên file hình cần kèm, nếu có |
| `review_status`, `reviewer`, `notes` | Trạng thái duyệt, người duyệt, vấn đề còn lại |

### Sheet QuestionLessons

Mỗi dòng gồm `question_code` và `lesson_code`. Dùng nhiều dòng nếu một câu liên quan tới nhiều bài học. Câu hỏi và các bài liên kết phải cùng môn; không lặp lại cùng một cặp.

### Quy trình xử lý mỗi câu

1. Sao chép hoặc OCR nội dung từ PDF vào bản nháp.
2. Đối chiếu đề bài và cả 4 lựa chọn với trang gốc; bỏ số trang hoặc đầu trang bị OCR chèn nhầm.
3. Xác minh đáp án từ nguồn và kiểm tra lại bằng kiến thức môn học. Nếu thiếu đáp án hoặc nghi sai, đánh dấu `needs_review`, không đoán rồi duyệt.
4. Viết lời giải dễ hiểu. Nếu dùng AI để hỗ trợ, người kiểm duyệt phải kiểm tra nội dung trước khi chuyển `approved`.
5. Gắn chủ đề, bài học và độ khó; ghi rõ nguồn để truy lại được.
6. Người thứ hai kiểm tra, ghi tên người duyệt và các lỗi còn lại.

Hiện tại câu hỏi được đưa vào sử dụng cần **đúng 4 lựa chọn và đúng 1 đáp án đúng**. Câu tự luận, nhiều đáp án đúng, câu phụ thuộc đoạn văn hoặc hình chung nên đưa vào danh sách chờ xử lý; không tự ép vào định dạng làm thay đổi ý nghĩa câu hỏi.

### Thống nhất cách ước lượng độ khó

| Mức | Cách hiểu ban đầu |
|---|---|
| 1–3 | Nhận biết, hiểu khái niệm hoặc áp dụng trực tiếp một bước |
| 4–6 | Vận dụng thông thường, cần kết hợp vài bước |
| 7–8 | Vận dụng nhiều kiến thức hoặc có tình huống dễ nhầm |
| 9–10 | Bài tổng hợp khó, cần suy luận sâu |

Đây là quy ước biên soạn ban đầu, chưa phải độ khó được xác định từ kết quả thực tế. Cả tài liệu và câu hỏi hiện cho phép giá trị từ 1 đến 10; nên dùng số nguyên khi thu thập để dễ thống nhất.

### Ví dụ một câu hoàn chỉnh

- Mã: `GT1-Q001`; môn: `GT1`; bài liên kết: `GT1-L01`.
- Đề: Tính giới hạn của dãy số u_n = 1/n khi n tiến tới vô cùng.
- A: 0; B: 1; C: 2; D: Dãy không có giới hạn.
- Đáp án đúng: A.
- Lời giải: Khi n tăng không giới hạn, 1/n tiến về 0 nên giới hạn bằng 0.
- Độ khó: 2. Nguồn: ghi tài liệu và trang thực tế khi sử dụng; đây chỉ là ví dụ cách điền.

## 9. Chuẩn bị đề kiểm tra

### Sheet Assessments

| Cột | Cách điền |
|---|---|
| `assessment_code` | Mã đề, ví dụ GT1-DE001 |
| `subject_code` | Môn của đề |
| `title` | Tên đề hiển thị |
| `description` | Phạm vi kiến thức hoặc hướng dẫn |
| `type` | quiz, exam hoặc practice |
| `duration_minutes` | Thời lượng là số nguyên dương |
| `pass_score` | Ngưỡng đạt từ 0 đến 100; thống nhất với người phụ trách môn |
| `review_status` | Trạng thái kiểm duyệt |

### Sheet AssessmentQuestions

Mỗi dòng gồm `assessment_code`, `question_code`, `order_num`, `points`. Thứ tự là số nguyên dương, điểm lớn hơn 0. Trong một đề không lặp câu hỏi và không lặp số thứ tự. Đợt thu thập này dùng câu hỏi cùng môn với đề; người duyệt kiểm tra cả thời lượng và độ phủ kiến thức.

Không nhập các bản sao của câu hỏi chỉ để tạo đề khác. Dùng lại mã câu hỏi đã có và khai báo thêm liên kết với đề mới.

## 10. Bàn giao và đưa dữ liệu lên hệ thống

### Người thu thập bàn giao

Gói bàn giao gồm thư mục như mục 4 và workbook với các sheet đã mô tả. Trong `README.txt`, ghi người phụ trách, ngày bàn giao, phạm vi môn/bài, số file, số câu đã duyệt và danh sách câu hoặc file còn vấn đề. Nếu cập nhật một gói cũ, ghi rõ mã nào thêm mới, mã nào sửa và lý do.

Không gửi mật khẩu database trong gói dữ liệu. Không cần chép workbook hoặc PDF vào GitHub nếu chưa thống nhất cách quản lý dung lượng và quyền truy cập.

### Dev A xử lý

1. Kiểm tra mã trùng, mã liên kết thiếu, file không tồn tại và trạng thái duyệt. Báo lỗi theo tên sheet và số dòng.
2. Kiểm tra hoặc xây dựng importer phù hợp workbook; xác định cách nhận diện tài liệu, câu hỏi và đề ở lần nhập lại để tránh tạo trùng.
3. Upload PDF vào nơi lưu trữ bền vững, kiểm tra mở được file rồi lưu đường dẫn vào bản ghi tài liệu. File và bản ghi cần được đối chiếu; tránh để lại bản ghi trỏ tới file thiếu.
4. Import thử vào database local theo thứ tự: môn → bài → tài liệu → liên kết tài liệu → câu hỏi và lựa chọn → liên kết câu hỏi → đề → liên kết đề.
5. Chạy lại gói mẫu để kiểm tra không phát sinh bản ghi trùng. Đối chiếu số bản ghi và lấy mẫu nội dung trên website.
6. Khi đạt yêu cầu, sao lưu staging rồi nhập cùng gói đã duyệt lên staging. Thông báo số lượng thành công, lỗi và các nội dung chưa công bố.

Ở local, PDF có thể dùng thư mục `uploads/materials/`. Trên cloud, cần chọn và tích hợp nơi lưu file có tính bền vững; không coi ổ đĩa tạm của dịch vụ web là kho tài liệu lâu dài. Việc lưu file trên cloud là phần triển khai riêng cần hoàn thiện, không phải người thu thập tự cấu hình.

## 11. Checklist trước khi bàn giao

- [ ] Mỗi môn và bài có tên rõ ràng, mã nhất quán và thứ tự hợp lý.
- [ ] Mọi PDF mở được, đủ trang cần dùng, có nguồn và ghi chú quyền sử dụng.
- [ ] Tên file trong workbook khớp chính xác với file đã gửi.
- [ ] Mỗi tài liệu có mô tả, độ khó và ít nhất một bài học phù hợp trong phạm vi gói này.
- [ ] Mỗi câu dùng được có đề đầy đủ, 4 lựa chọn, 1 đáp án đúng và lời giải đã kiểm tra.
- [ ] Công thức, hình và ký hiệu đã được đối chiếu với PDF gốc.
- [ ] Câu hỏi có chủ đề, độ khó, nguồn và liên kết bài học; không gắn nhầm môn.
- [ ] Câu trùng đã được rà soát theo nội dung, không chỉ theo mã.
- [ ] Đề mẫu có thời lượng, ngưỡng đạt, câu hỏi theo thứ tự và điểm hợp lệ.
- [ ] Những nội dung chưa chắc chắn được đánh dấu chờ duyệt, không trộn vào phần đã duyệt.
- [ ] README ghi rõ người phụ trách, số lượng và các vấn đề cần xử lý.

## 12. Những lỗi cần tránh

| Lỗi thường gặp | Cách xử lý |
|---|---|
| Chỉ gửi một thư mục PDF, không ghi nội dung thuộc bài nào | Điền cấu trúc môn/bài và các sheet liên kết |
| OCR sai ký hiệu nhưng vẫn đánh dấu đã duyệt | So từng câu với trang nguồn, đặc biệt công thức |
| Không có đáp án nên tự chọn một phương án | Giữ chờ duyệt và nhờ người có chuyên môn xác minh |
| Cùng một tài liệu được gửi nhiều lần với tên khác nhau | Giữ một mã tài liệu và nhiều liên kết bài học |
| Đổi mã mỗi lần gửi lại | Giữ mã ổn định và liệt kê thay đổi |
| Cho rằng mã trong Excel chính là ID database | Dev A tra mã và chuyển sang ID khi import |
| Đưa toàn bộ dữ liệu lên staging trước khi thử | Kiểm tra bộ mẫu ở local rồi mới mở rộng |
| Tải PDF lên nhưng nghĩ đã có đề tự chấm | Trích riêng câu hỏi, lựa chọn và đáp án để tạo đề |

**Việc cần bắt đầu:** chọn một môn, thống nhất hai bài học đầu tiên, tìm 2–3 PDF và hoàn thành bộ 10 câu đã duyệt. Gửi bộ mẫu cho Dev A kiểm tra trước khi thu thập toàn bộ môn.
