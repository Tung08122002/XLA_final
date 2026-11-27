# Bảng số liệu t10 (tự sinh bởi src/t10_timing.py từ các file CSV)

## Môi trường đo

- CPU: Intel64 Family 6 Model 186 Stepping 3, GenuineIntel; 12 lõi logic (12 lõi dùng được); Python 3.13.12.
- Pillow 12.3.0; libjpeg-turbo 3.1.4.1; libwebp 1.6.0; zlib 1.3.1.zlib-ng.
- Quy trình: 1 lần khởi động bỏ đi + 9 lần đo, lấy trung vị; toàn bộ trong bộ nhớ; ngày đo 2026-11-25T23:30:26.
- Độ nhiễu: Windows không hỗ trợ `os.getloadavg()`, nên dùng phép đo tham chiếu thay cho load average.
- Phép đo tham chiếu (JPEG q75, ảnh P01, 9 lần): trước 1.43 ms (IQR/trung vị 12%, max/min 1.89), sau 8.29 ms (IQR/trung vị 20%, max/min 1.72).
- Không kết luận trạng thái rảnh/bận từ load average trên Windows; xem IQR/trung vị của phép đo tham chiếu.

## B1. Thời gian mã hoá, trung vị theo nhóm (ms/ảnh)

P: ảnh chụp chi tiết (7 ảnh 500 px); T: ảnh có chữ (3×500 px + 4×1000 px); G: gradient/nền trơn (3×500 px + 3×1000 px).

| Cấu hình | P | T | G | Tất cả |
|---|---:|---:|---:|---:|
| JPEG q50 | 1.92 | 7.53 | 2.04 | 2.44 |
| JPEG q75 | 2.32 | 7.24 | 1.67 | 2.27 |
| JPEG q90 | 2.47 | 6.92 | 2.08 | 2.46 |
| PNG L9 | 190.8 | 158.6 | 202.7 | 176.0 |
| WebP q50 | 76.9 | 197.3 | 107.0 | 77.8 |
| WebP q75 | 82.0 | 202.3 | 109.6 | 82.7 |
| WebP q90 | 92.0 | 210.4 | 100.8 | 94.6 |
| WebP lossless | 707.0 | 671.5 | 506.8 | 655.1 |

## B2. Thời gian giải mã, trung vị theo nhóm (ms/ảnh)

P: ảnh chụp chi tiết (7 ảnh 500 px); T: ảnh có chữ (3×500 px + 4×1000 px); G: gradient/nền trơn (3×500 px + 3×1000 px).

| Cấu hình | P | T | G | Tất cả |
|---|---:|---:|---:|---:|
| JPEG q50 | 2.27 | 8.99 | 2.54 | 2.43 |
| JPEG q75 | 2.50 | 8.83 | 2.41 | 2.74 |
| JPEG q90 | 2.77 | 9.27 | 3.64 | 3.21 |
| PNG L9 | 12.7 | 13.3 | 8.75 | 12.3 |
| WebP q50 | 11.4 | 27.4 | 15.7 | 11.5 |
| WebP q75 | 11.8 | 28.9 | 14.8 | 12.4 |
| WebP q90 | 13.3 | 30.2 | 13.7 | 13.3 |
| WebP lossless | 17.4 | 29.4 | 17.9 | 17.6 |

## B3. Theo kích thước ảnh (trung vị ms/ảnh; 13 ảnh 500 px, 7 ảnh 1000 px)

Lưu ý: nội dung và kích thước không độc lập (ảnh 1000 px chỉ thuộc nhóm T và G), nên tỉ số 1000/500 lẫn cả ảnh hưởng của nội dung; lý thuyết thuần tuý theo diện tích là 4,00.

| Cấu hình | Mã hoá 500 px (ms) | Mã hoá 1000 px (ms) | Tỉ số 1000/500 | Giải mã 500 px (ms) | Giải mã 1000 px (ms) | Tỉ số 1000/500 |
|---|---:|---:|---:|---:|---:|---:|
| JPEG q50 | 2.14 | 7.55 | 3.53 | 2.10 | 9.05 | 4.31 |
| JPEG q75 | 2.09 | 7.33 | 3.52 | 2.28 | 8.88 | 3.89 |
| JPEG q90 | 2.42 | 6.92 | 2.86 | 2.68 | 9.27 | 3.46 |
| PNG L9 | 151.0 | 190.5 | 1.26 | 10.3 | 15.9 | 1.54 |
| WebP q50 | 71.5 | 197.3 | 2.76 | 10.0 | 27.4 | 2.74 |
| WebP q75 | 73.7 | 202.3 | 2.74 | 11.1 | 28.9 | 2.62 |
| WebP q90 | 78.7 | 219.4 | 2.79 | 12.0 | 30.2 | 2.52 |
| WebP lossless | 468.1 | 698.8 | 1.49 | 13.2 | 29.4 | 2.23 |

## B4. Thông lượng gộp (megapixel/giây; tổng MP / tổng thời gian)

| Cấu hình | Mã hoá 500 px | Mã hoá 1000 px | Mã hoá tất cả | Giải mã 500 px | Giải mã 1000 px | Giải mã tất cả |
|---|---:|---:|---:|---:|---:|---:|
| JPEG q50 | 123.8 | 148.3 | 139.5 | 120.0 | 121.1 | 120.7 |
| JPEG q75 | 122.8 | 154.8 | 143.0 | 99.7 | 120.8 | 113.2 |
| JPEG q90 | 111.5 | 159.2 | 140.2 | 93.3 | 116.0 | 107.7 |
| PNG L9 | 1.47 | 4.80 | 2.79 | 28.5 | 66.6 | 46.8 |
| WebP q50 | 3.77 | 5.28 | 4.68 | 26.4 | 35.4 | 31.9 |
| WebP q75 | 3.51 | 5.10 | 4.46 | 24.1 | 35.3 | 30.8 |
| WebP q90 | 3.07 | 4.75 | 4.05 | 21.5 | 36.3 | 29.8 |
| WebP lossless | 0.48 | 1.42 | 0.88 | 18.8 | 35.7 | 27.8 |

## B5a. Tải trang danh mục 40 ảnh trên 4G (10 Mbit/s), trung bình cả 20 ảnh

| Cấu hình | KB/ảnh | KB/trang | Truyền (s) | Giải mã (s) | Tổng (s) | Giải mã / tổng (%) | Tổng so với JPEG q75 |
|---|---:|---:|---:|---:|---:|---:|---:|
| JPEG q50 | 29.2 | 1,168 | 0.96 | 0.17 | 1.13 | 15.08 | 0.75 |
| JPEG q75 | 40.1 | 1,603 | 1.31 | 0.18 | 1.49 | 12.12 | 1.00 |
| JPEG q90 | 63.0 | 2,519 | 2.06 | 0.19 | 2.25 | 8.44 | 1.51 |
| PNG L9 | 258.8 | 10,350 | 8.48 | 0.44 | 8.92 | 4.91 | 5.97 |
| WebP q50 | 16.9 | 677.5 | 0.56 | 0.64 | 1.20 | 53.62 | 0.80 |
| WebP q75 | 21.7 | 868.9 | 0.71 | 0.67 | 1.38 | 48.34 | 0.92 |
| WebP q90 | 38.6 | 1,543 | 1.26 | 0.69 | 1.95 | 35.27 | 1.31 |
| WebP lossless | 198.6 | 7,945 | 6.51 | 0.74 | 7.25 | 10.18 | 4.85 |

## B5b. Tải trang danh mục 40 ảnh trên 3G (2 Mbit/s), trung bình cả 20 ảnh

| Cấu hình | KB/ảnh | KB/trang | Truyền (s) | Giải mã (s) | Tổng (s) | Giải mã / tổng (%) | Tổng so với JPEG q75 |
|---|---:|---:|---:|---:|---:|---:|---:|
| JPEG q50 | 29.2 | 1,168 | 4.78 | 0.17 | 4.95 | 3.43 | 0.73 |
| JPEG q75 | 40.1 | 1,603 | 6.56 | 0.18 | 6.75 | 2.68 | 1.00 |
| JPEG q90 | 63.0 | 2,519 | 10.3 | 0.19 | 10.5 | 1.81 | 1.56 |
| PNG L9 | 258.8 | 10,350 | 42.4 | 0.44 | 42.8 | 1.02 | 6.35 |
| WebP q50 | 16.9 | 677.5 | 2.78 | 0.64 | 3.42 | 18.78 | 0.51 |
| WebP q75 | 21.7 | 868.9 | 3.56 | 0.67 | 4.22 | 15.76 | 0.63 |
| WebP q90 | 38.6 | 1,543 | 6.32 | 0.69 | 7.01 | 9.83 | 1.04 |
| WebP lossless | 198.6 | 7,945 | 32.5 | 0.74 | 33.3 | 2.22 | 4.93 |

## B6. Tổng thời gian tải trang 40 ảnh theo nhóm (s)

| Cấu hình | P 4G | P 3G | T 4G | T 3G | G 4G | G 3G |
|---|---:|---:|---:|---:|---:|---:|
| JPEG q50 | 0.99 | 4.58 | 1.65 | 7.27 | 0.67 | 2.68 |
| JPEG q75 | 1.44 | 6.75 | 2.15 | 9.70 | 0.79 | 3.29 |
| JPEG q90 | 2.38 | 11.4 | 3.04 | 14.2 | 1.19 | 5.23 |
| PNG L9 | 13.2 | 64.1 | 6.75 | 32.0 | 6.41 | 30.7 |
| WebP q50 | 1.15 | 3.97 | 1.64 | 4.77 | 0.73 | 1.19 |
| WebP q75 | 1.44 | 5.28 | 1.86 | 5.69 | 0.73 | 1.29 |
| WebP q90 | 2.44 | 9.92 | 2.42 | 8.52 | 0.84 | 1.86 |
| WebP lossless | 10.7 | 50.6 | 5.23 | 22.7 | 5.62 | 25.4 |

- Trên 4G (10 Mbit/s), truyền 1 KB mất 0.82 ms; tức 1 ms giải mã tương đương 1.22 KB dung lượng.
- Trên 3G (2 Mbit/s), truyền 1 KB mất 4.10 ms; tức 1 ms giải mã tương đương 0.24 KB dung lượng.

## B7. Chi phí mã hoá 10.000 ảnh (một luồng; lõi-phút CPU)

| Cấu hình | 500 px: ms/ảnh | 500 px: lõi-phút | 1000 px: ms/ảnh | 1000 px: lõi-phút | Cả 20 ảnh: ms/ảnh | Cả 20 ảnh: lõi-phút |
|---|---:|---:|---:|---:|---:|---:|
| JPEG q50 | 2.02 | 0.34 | 6.74 | 1.12 | 3.67 | 0.61 |
| JPEG q75 | 2.04 | 0.34 | 6.46 | 1.08 | 3.58 | 0.60 |
| JPEG q90 | 2.24 | 0.37 | 6.28 | 1.05 | 3.66 | 0.61 |
| PNG L9 | 170.1 | 28.3 | 208.2 | 34.7 | 183.4 | 30.6 |
| WebP q50 | 66.4 | 11.1 | 189.4 | 31.6 | 109.4 | 18.2 |
| WebP q75 | 71.2 | 11.9 | 196.2 | 32.7 | 115.0 | 19.2 |
| WebP q90 | 81.5 | 13.6 | 210.6 | 35.1 | 126.6 | 21.1 |
| WebP lossless | 519.6 | 86.6 | 705.3 | 117.5 | 584.6 | 97.4 |

## B9. Đối chiếu thời gian tường (wall) và thời gian CPU của tiến trình (trung vị, tất cả 20 ảnh)

Thời gian CPU ít nhạy với việc tiến trình khác chen vào lõi; tỉ số wall/CPU xa 1 cho biết mức nhiễu (≈1 khi máy rảnh).

| Cấu hình | Mã hoá wall (ms) | Mã hoá CPU (ms) | wall/CPU | Giải mã wall (ms) | Giải mã CPU (ms) | wall/CPU |
|---|---:|---:|---:|---:|---:|---:|
| JPEG q50 | 2.44 | 2.23 | 1.09 | 2.43 | 2.72 | 0.89 |
| JPEG q75 | 2.27 | 2.32 | 0.98 | 2.74 | 2.98 | 0.92 |
| JPEG q90 | 2.46 | 2.84 | 0.87 | 3.21 | 3.79 | 0.85 |
| PNG L9 | 176.0 | 171.9 | 1.02 | 12.3 | 13.0 | 0.95 |
| WebP q50 | 77.8 | 78.1 | 1.00 | 11.5 | 10.4 | 1.10 |
| WebP q75 | 82.7 | 78.1 | 1.06 | 12.4 | 13.0 | 0.95 |
| WebP q90 | 94.6 | 93.8 | 1.01 | 13.3 | 15.6 | 0.85 |
| WebP lossless | 655.1 | 593.8 | 1.10 | 17.6 | 15.6 | 1.13 |

## B8. Dung lượng trung bình (KB/ảnh) dùng cho ước tính tải trang

| Cấu hình | P | T | G | Tất cả |
|---|---:|---:|---:|---:|
| JPEG q50 | 27.4 | 42.9 | 15.4 | 29.2 |
| JPEG q75 | 40.5 | 57.6 | 19.1 | 40.1 |
| JPEG q90 | 68.6 | 84.9 | 30.8 | 63.0 |
| PNG L9 | 388.2 | 192.5 | 185.0 | 258.8 |
| WebP q50 | 21.5 | 23.9 | 3.51 | 16.9 |
| WebP q75 | 29.2 | 29.2 | 4.21 | 21.7 |
| WebP q90 | 57.1 | 46.5 | 7.81 | 38.6 |
| WebP lossless | 304.9 | 133.5 | 150.5 | 198.6 |
