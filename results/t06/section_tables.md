### Bảng 1 - Iso-quality (SSIM)

| Nhóm | Ngưỡng SSIM | JPEG 4:2:0: trung vị KB (số ảnh đạt) | JPEG 4:4:4 | WebP lossy | WebP tiết kiệm so với JPEG 4:2:0: trung vị % (số cặp) |
|---|---|---|---|---|---|
| P | 0,95 | 58,7 (7/7) | 56,7 (7/7) | 42,7 (7/7) | 28,6 (7) |
| P | 0,98 | 189,7 (5/7) | 154,9 (7/7) | 96,9 (2/7) | 32,1 (2) |
| P | 0,99 | 162,0 (1/7) | 314,0 (7/7) | – (0/7) | – |
| T | 0,95 | 35,8 (7/7) | 45,1 (7/7) | 13,7 (7/7) | 61,7 (7) |
| T | 0,98 | 97,8 (7/7) | 87,2 (7/7) | 27,6 (7/7) | 60,9 (7) |
| T | 0,99 | 263,6 (3/7) | 126,7 (7/7) | 99,8 (2/7) | 61,7 (2) |
| G | 0,95 | 12,8 (6/6) | 20,0 (6/6) | 2,6 (6/6) | 80,4 (6) |
| G | 0,98 | 19,3 (3/6) | 151,1 (6/6) | 3,6 (3/6) | 81,5 (3) |
| G | 0,99 | 22,0 (3/6) | 152,6 (6/6) | 4,1 (3/6) | 81,5 (3) |
| ALL | 0,95 | 29,2 (20/20) | 31,1 (20/20) | 12,8 (20/20) | 61,6 (20) |
| ALL | 0,98 | 97,8 (15/20) | 100,2 (20/20) | 27,4 (12/20) | 61,2 (12) |
| ALL | 0,99 | 162,0 (7/20) | 166,4 (20/20) | 5,1 (5/20) | 77,4 (5) |

### Bảng 2 - Iso-quality (PSNR), toàn bộ 20 ảnh

| Ngưỡng PSNR | JPEG 4:2:0: trung vị KB (số ảnh đạt) | JPEG 4:4:4 | WebP lossy | WebP tiết kiệm so với JPEG 4:2:0: trung vị % (số cặp) |
|---|---|---|---|---|
| 35 dB | 34,0 (19/20) | 35,0 (20/20) | 19,2 (19/20) | 60,1 (19) |
| 40 dB | 20,9 (11/20) | 60,4 (20/20) | 3,8 (9/20) | 77,2 (9) |

### Bảng 3 - Không mất mát so với lossy tại SSIM 0,99 (dung lượng TB, KB)

| Nhóm | PNG (level 9) | WebP lossless | Số ảnh WebP lossless NHỎ HƠN lossy tốt nhất đạt 0,99 |
|---|---|---|---|
| P | 388,2 | 304,9 | 6/7 |
| T | 192,5 | 133,5 | 3/7 |
| G | 185,0 | 150,5 | 3/6 |
| Cả 20 ảnh | 258,8 | 198,6 | 12/20 |

### Bảng 4 - Tương quan PSNR-SSIM (Spearman)

| Phạm vi | n | rho |
|---|---|---|
| toàn bộ - ALL | 1200 | 0,841 |
| nhóm - G | 360 | 0,902 |
| nhóm - P | 420 | 0,905 |
| nhóm - T | 420 | 0,977 |
| codec - JPEG 4:2:0 | 400 | 0,850 |
| codec - JPEG 4:4:4 | 400 | 0,878 |
| codec - WebP lossy | 400 | 0,784 |
| trong ảnh (TB 20 ảnh) - ALL | 20 | 0,989 |
| trong ảnh (min) - G04_studio500_noise | 1 | 0,958 |
| trong ảnh (TB theo nhóm) - G | 6 | 0,981 |
| trong ảnh (TB theo nhóm) - P | 7 | 0,996 |
| trong ảnh (TB theo nhóm) - T | 7 | 0,990 |

Cặp bất đồng (cùng ảnh, |dPSNR|>=0,5 dB và |dSSIM|>=0,002): 194/30927 = 0,63 %
- Nhóm G: 76/8178 = 0,93 %
- Nhóm P: 29/11445 = 0,25 %
- Nhóm T: 89/11304 = 0,79 %

### Bảng 5 - Khuyến nghị

| Loại ảnh (số ảnh) | Mục tiêu SSIM | Định dạng chính, quality (q đo được) | Dung lượng TB KB (bpp) | SSIM TB (min) | PSNR TB (min) dB | Dự phòng cho `<picture>`: định dạng, quality, KB (so với chính) | WebP lossless / PNG KB |
|---|---|---|---|---|---|---|---|
| Ảnh có chữ (T) (7) | >= 0,95 | WebP lossy q=50 (q đo 30) | 23,9 (0,35) | 0,971 (0,962) | 35,1 (33,1) | JPEG 4:2:0 q=70, 53,5 KB (+124 %) | 133,5 / 192,5 |
| Ảnh có chữ (T) (7) | >= 0,98 | WebP lossy q=90 (q đo 90) | 46,5 (0,66) | 0,985 (0,981) | 37,8 (36,1) | JPEG 4:4:4 q=90, 106,7 KB (+130 %) | 133,5 / 192,5 |
| Gradient/nền trơn, sạch (G01-G03) (3) | >= 0,95 | WebP lossy q=50 (q đo 5) | 4,8 (0,04) | 0,994 (0,992) | 45,4 (44,9) | JPEG 4:2:0 q=50, 22,7 KB (+376 %) | 41,0 / 69,1 |
| Gradient/nền trơn, sạch (G01-G03) (3) | >= 0,98 | WebP lossy q=50 (q đo 5) | 4,8 (0,04) | 0,994 (0,992) | 45,4 (44,9) | JPEG 4:2:0 q=50, 22,7 KB (+376 %) | 41,0 / 69,1 |
| Gradient/nền trơn, nhiễu cảm biến (G04-G06) (3) | >= 0,95 | WebP lossy q=50 (q đo 20) | 2,2 (0,07) | 0,958 (0,956) | 40,2 (39,4) | JPEG 4:2:0 q=50, 8,1 KB (+260 %) | 260,1 / 300,8 |
| Gradient/nền trơn, nhiễu cảm biến (G04-G06) (3) | >= 0,98 | WebP lossless | 260,1 (8,52) | 1,000 (1,000) | – | JPEG 4:4:4 q=100, 275,0 KB (+6 %) | 260,1 / 300,8 |
| Ảnh chụp nhiều chi tiết (P) (7) | >= 0,95 | WebP lossy q=90 (q đo 90) | 57,1 (1,87) | 0,963 (0,950) | 37,2 (32,1) | JPEG 4:4:4 q=90, 90,4 KB (+58 %) | 304,9 / 388,2 |
| Ảnh chụp nhiều chi tiết (P) (7) | >= 0,98 | WebP lossless | 304,9 (9,99) | 1,000 (1,000) | – | JPEG 4:4:4 q=100, 326,5 KB (+7 %) | 304,9 / 388,2 |
