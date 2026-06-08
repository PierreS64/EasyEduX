# Hướng dẫn sử dụng EasyEduX

Hệ thống EasyEduX cung cấp các công cụ tự động hóa giúp giải quyết các bài kiểm tra và bài giảng (slide) trực tuyến trên nền tảng EDUX.

## 1. Cài đặt hệ thống (Chỉ làm lần đầu)
Trước khi sử dụng, bạn cần cài đặt môi trường và các thư viện cần thiết:
1. Nhấn đúp chuột vào file `install_deps.bat` ở thư mục gốc của dự án.
2. Hệ thống sẽ tự động tạo môi trường ảo Python (`.venv`) và tải toàn bộ các thư viện (Playwright, pytest, v.v.).
3. Chờ cho đến khi terminal báo cài đặt hoàn tất.

## 2. Các chức năng chính

### 2.1. Giải bài kiểm tra (EDUX-TEST-SOLVER)
Dùng để tự động tham gia và lựa chọn đáp án cho các hệ test.
- **Cách sử dụng**: Nhấp đúp vào file `run_test_solver.bat`.
- Màn hình Terminal hiện lên yêu cầu bạn chọn phương thức đăng nhập:
  - Nhập `1`: Đăng nhập bằng tên đăng nhập & mật khẩu.
  - Nhập `2`: Đăng nhập bằng tài khoản Microsoft.
- Trình duyệt tự động mở lên, thực hiện đăng nhập và làm bài.
- **Lưu ý**: Lần chạy đầu tiên sẽ yêu cầu điền thông tin và tự động lưu vào file `.env`. Đảm bảo cung cấp sẵn file thông tin câu hỏi/đáp án phù hợp vào đúng thư mục trước khi chạy.

### 2.2. Trượt Slide Brute Force (EDUX-SLIDE-BRUTEFORCE)
Chức năng tự động xem các slide bài giảng và vượt qua các câu hỏi bên trong slide.
- **Cách sử dụng**: Nhấp đúp vào file `run_slide_bruteforce.bat`.
- Chọn phương thức đăng nhập theo màn hình hiển thị.
- Trình duyệt sẽ tự động thực hiện thao tác xem qua toàn bộ slide.