[app]

# Tên hiển thị của ứng dụng
title = Doc Truyen

# Tên gói (không dấu, không khoảng trắng)
package.name = doctruyen
package.domain = org.mynovel

# Thư mục chứa main.py
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt

# Phiên bản
version = 1.0

# Thư viện cần thiết
requirements = python3,kivy

# Hướng màn hình
orientation = portrait

# Toàn màn hình (0 = có thanh trạng thái)
fullscreen = 0

# ----- Android -----
# Quyền truy cập bộ nhớ để đọc file truyện
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# API target / tối thiểu
android.api = 34
android.minapi = 24

# Kiến trúc (đa số máy hiện nay)
android.archs = arm64-v8a, armeabi-v7a

# Cho phép truy cập bộ nhớ theo kiểu cũ (giúp đọc /sdcard dễ hơn)
android.allow_backup = 1

# Bật để chấp nhận license SDK tự động khi build
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
