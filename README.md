# Đọc Truyện — phiên bản Android (Kivy)

Cùng chức năng với bản máy tính: mở file `.txt`, tự cắt chương (kiểu *"Thứ 1 chương..."* và *"chương 100..."*), mục lục + tìm chương, đọc chương, chỉnh cỡ chữ, nền sáng/tối, chương trước/sau, nhớ vị trí đọc, và **chạm vào chữ để thay thế tên** cho toàn bộ truyện + quản lý danh sách tên.

> ⚠️ Vì sao chưa có sẵn file `.apk`? Việc đóng gói APK bắt buộc tải Android SDK/NDK từ máy chủ Google — không làm được trong môi trường tạo file này. Bên dưới là 2 cách để **tự tạo ra file APK** (không cần biết lập trình).

---

## CÁCH 1 — Build tự động trên GitHub (khuyên dùng, không cần cài gì)

1. Tạo tài khoản tại https://github.com (miễn phí).
2. Tạo một repository mới (ví dụ tên `doc-truyen`), để **Public**.
3. Tải toàn bộ thư mục này lên repo đó (nút **Add file → Upload files**, kéo thả tất cả: `main.py`, `buildozer.spec`, thư mục `.github`).
4. Vào tab **Actions** của repo → nếu được hỏi thì bấm **I understand my workflows, enable them**.
5. Quy trình **Build APK** sẽ tự chạy (khoảng 15–30 phút lần đầu). Khi xong, vào **Actions → lần chạy mới nhất → mục Artifacts → doctruyen-apk** để tải file `.apk` về.
6. Chép `.apk` vào điện thoại, mở lên cài. (Android sẽ hỏi cho phép "cài từ nguồn không xác định" → bật cho phép.)

Nếu lần chạy báo lỗi, mở log xem dòng đỏ; thường chỉ cần bấm **Re-run jobs** là được.

---

## CÁCH 2 — Build trên máy Linux / WSL (Ubuntu)

```bash
# Cài công cụ
pip install --user buildozer cython
sudo apt update
sudo apt install -y openjdk-17-jdk zip unzip autoconf libtool pkg-config \
    zlib1g-dev libncurses-dev libtinfo6 cmake libffi-dev libssl-dev

# Vào thư mục dự án rồi build
cd doc-truyen
buildozer android debug
```
File APK xuất ra trong thư mục `bin/`. Lần đầu build sẽ tải SDK/NDK (vài GB) và mất khá lâu; các lần sau nhanh hơn.

---

## CÁCH 3 — Build trên Google Colab (không cần máy mạnh)

Tạo notebook mới tại https://colab.research.google.com rồi chạy:
```python
!pip install buildozer cython
!sudo apt-get update
!sudo apt-get install -y openjdk-17-jdk zip unzip autoconf libtool pkg-config \
    zlib1g-dev libncurses-dev cmake libffi-dev libssl-dev
# tải các file main.py và buildozer.spec lên Colab trước, rồi:
!buildozer android debug
```
Sau khi xong, tải file trong `bin/*.apk` về.

---

## Dùng app trên điện thoại

- Chép các file truyện `.txt` vào một trong các thư mục: **Truyen**, **Download**, **Documents** trong bộ nhớ máy.
- Mở app → bấm **Mở** → chọn nhanh thư mục ở hàng nút trên, hoặc duyệt tới file → chạm để đọc.
- **Mục lục**: xem danh sách chương, có ô tìm chương.
- **A- / A+**: cỡ chữ. **Nền**: sáng/tối. **◀ ▶**: chương trước/sau. **▲ ▼**: lật trang.
- **Thay tên**: chạm vào một từ trong truyện → bảng hiện ra → dùng nút **Rộng/Hẹp** để nới vùng chọn, gõ tên mới → **Áp dụng** (đổi toàn truyện). Nút **Tên** (hoặc **Quản lý**) xem & xoá danh sách tên đã đổi.

> Lưu ý Android 11 trở lên: nếu app không thấy file, vào **Cài đặt → Ứng dụng → Đọc Truyện → Quyền → Bộ nhớ/Tệp**, cấp quyền truy cập tệp. Hoặc đặt file vào thư mục **Download** (thường truy cập được dễ nhất).

## Chạy thử trên máy tính trước (tuỳ chọn)
```bash
pip install kivy
python main.py
```
