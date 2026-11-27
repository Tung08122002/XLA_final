# Thí nghiệm ablation: ảnh hưởng của từng tham số bộ mã hoá (t08)

## 1. Mục tiêu và phương pháp

Các phần so sánh chính (JPEG, PNG, WebP) dùng tham số "mặc định" của thư viện. Phần này kiểm tra xem việc chọn tham số đó có hợp lý không bằng sáu ablation, mỗi ablation **chỉ thay đổi một tham số, giữ nguyên mọi thứ còn lại**: cùng 20 ảnh (7 ảnh P, 7 ảnh T, 6 ảnh G), cùng hàm mã hoá/giải mã và cùng cách đo PSNR, SSIM (RGB, data_range 255; SSIM Gauss σ = 1.5) của `common.py`. Số liệu báo cáo là trung bình theo nhóm (trung bình các giá trị của từng ảnh; các phần trăm so với cấu hình cơ sở được tính theo từng ảnh rồi mới lấy trung bình). Chất lượng danh định cố định ở 75 cho các thí nghiệm lossy, vì đây là mức khuyến nghị thông dụng của JPEG/WebP và nằm giữa hai baseline 50 và 90. Mã nguồn: `src/t08_ablation.py`; số liệu từng ảnh: `results/t08/a1_raw.csv` ... `a6_raw.csv`; bảng đầy đủ: `results/t08/tables.md`.

| Mã | Tham số thay đổi | Giá trị | Chỉ số chính |
|---|---|---|---|
| A1 | JPEG: lấy mẫu sắc độ | 4:4:4 / 4:2:2 / 4:2:0 | dung lượng, PSNR, SSIM, PSNR Cb/Cr, ΔE |
| A2 | JPEG: `optimize`, `progressive` | tắt / bật | dung lượng, ảnh giải mã có giống hệt không, thời gian |
| A3 | WebP lossy: `method` | 0 / 2 / 4 / 6 | dung lượng, SSIM, thời gian mã hoá |
| A4 | PNG: `compress_level`, `optimize` | 1 / 6 / 9, optimize | dung lượng, thời gian mã hoá |
| A5 | WebP lossless: `quality` (mức nỗ lực) và `method` | quality 0/50/100, method 0/4/6 | dung lượng, thời gian mã hoá |
| A6 | Độ phân giải | 1000 px so với 500 px (Lanczos) | bit/điểm ảnh (bpp) |

**Lưu ý về số đo thời gian.** Với mỗi ảnh và mỗi cấu hình, thời gian là trung vị của 7 lần lặp (A2–A4) hoặc 3 lần lặp (A5, vì WebP lossless method 6, quality 100 mất hàng giây mỗi lần mã hoá), qua `evaluate(..., repeats=N)`; bảng báo cáo trung bình các trung vị đó theo nhóm. Các số liệu đó được đo khi máy chỉ có 2 lõi và đang chạy song song nhiều tiến trình khác (load average 1 phút lúc bắt đầu các ablation có đo thời gian: nan–nan), nên **giá trị tuyệt đối (ms) bị nhiễu và có thể sai lệch đáng kể; chỉ nên đọc tỉ lệ tương đối giữa các cấu hình trong cùng một bảng**. Dung lượng, PSNR và SSIM là tất định và không bị ảnh hưởng. Script có thể chạy lại tuần tự trên máy rảnh để cập nhật toàn bộ số thời gian (`python src/t08_ablation.py`).

## 2. A1 – JPEG: lấy mẫu sắc độ (quality 75)

**Cơ chế.** JPEG đổi RGB sang YCbCr rồi có thể giảm độ phân giải hai kênh màu Cb, Cr trước khi biến đổi DCT. Ở 4:4:4 không giảm; 4:2:2 trung bình hoá mỗi cặp điểm ảnh theo chiều ngang (Cb, Cr còn 1/2 số mẫu); 4:2:0 trung bình hoá mỗi khối 2×2 (còn 1/4 số mẫu). Cách làm này dựa trên việc thị giác người kém nhạy với chi tiết màu hơn chi tiết sáng. Ngược lại, tại biên có sắc độ thay đổi gắt (chữ đỏ trên nền trắng, nhãn giảm giá đỏ–vàng) giá trị Cb, Cr nhảy hàng trăm mức trong 1 điểm ảnh, nên việc lấy trung bình làm biên màu bị "loang" sang điểm ảnh bên cạnh.

Ngoài PSNR/SSIM trên RGB, tôi đo PSNR riêng từng kênh Cb, Cr (YCbCr BT.601 toàn dải) và ΔE CIE76 (trong không gian CIELAB). ΔE được tính hai cách: trung bình toàn ảnh và trung bình **tại các điểm ảnh sát biên màu** (gradient của Cb hoặc Cr trong ảnh gốc lớn hơn 30 mức/điểm ảnh, giãn 2 px); vùng này chiếm tỉ lệ 0.045 số điểm ảnh của ảnh T (tức chỉ vài phần trăm) nên ΔE trung bình toàn ảnh (0.86 ở 4:4:4 và 1.25 ở 4:2:0) "pha loãng" lỗi màu cục bộ.

| Nhóm | Lấy mẫu | Dung lượng (KB) | So với 4:4:4 (%) | PSNR RGB (dB) | SSIM | PSNR Cb (dB) | PSNR Cr (dB) | ΔE tại biên màu |
|---|---|---|---|---|---|---|---|---|
| P (ảnh chụp) | 4:4:4 | 51.6 | 100.0 | 35.72 | 0.9455 | 41.18 | 42.05 | 7.02 |
| P (ảnh chụp) | 4:2:2 | 44.6 | 86.3 | 34.72 | 0.9376 | 39.41 | 40.34 | 9.57 |
| P (ảnh chụp) | 4:2:0 | 40.5 | 78.3 | 33.92 | 0.9314 | 38.11 | 39.08 | 11.60 |
| T (ảnh có chữ) | 4:4:4 | 72.4 | 100.0 | 37.43 | 0.9757 | 44.55 | 43.65 | 5.76 |
| T (ảnh có chữ) | 4:2:2 | 62.4 | 86.3 | 36.12 | 0.9730 | 42.30 | 40.59 | 7.84 |
| T (ảnh có chữ) | 4:2:0 | 57.6 | 80.0 | 34.73 | 0.9681 | 40.41 | 38.21 | 10.75 |
| G (gradient) | 4:4:4 | 26.6 | 100.0 | 45.54 | 0.9785 | 49.16 | 48.64 | 5.30 |
| G (gradient) | 4:2:2 | 21.6 | 82.0 | 44.68 | 0.9778 | 48.08 | 47.79 | 6.03 |
| G (gradient) | 4:2:0 | 19.1 | 72.8 | 44.34 | 0.9775 | 47.72 | 47.37 | 8.17 |

Hình: `figures/t08/a1_subsampling.png` – (a) dung lượng, (b) PSNR kênh Cb, (c) PSNR kênh Cr, (d) ΔE tại biên màu theo kiểu lấy mẫu sắc độ, từng nhóm ảnh. Hình: `figures/t08/a1_badge_zoom.png` – nhãn "-35%" của T01 phóng 4 lần (gốc, 4:4:4, 4:2:2, 4:2:0). Hình: `figures/t08/a1_crops.png` – vùng giá và nhãn giảm giá của T01 và T05.

**Kết quả và giải thích.** (i) Giảm lấy mẫu sắc độ tiết kiệm dung lượng đáng kể: ở ảnh T, 4:2:2 giảm 13.7% và 4:2:0 giảm 20.0% so với 4:4:4 (ảnh P: 21.7%; ảnh G: 27.2%), vì hai kênh màu mất 50–75% số hệ số cần mã hoá. (ii) Cái giá phải trả tập trung ở màu: ở ảnh T, PSNR kênh Cb giảm từ 44.5 xuống 40.4 dB và kênh Cr từ 43.7 xuống 38.2 dB; kênh sáng Y giảm ít hơn nhiều (từ 39.4 xuống 38.7 dB; phần giảm nhỏ này có thể do lỗi màu lan sang Y khi đổi RGB↔YCbCr), điều này phù hợp với cơ chế: chỉ kênh màu bị trung bình hoá. ΔE tại biên màu của ảnh T tăng từ 5.8 lên 10.7, gấp 1.9 lần; giá trị cỡ 10 vượt xa ngưỡng nhận biết khác biệt màu thường dùng cho CIE76 (khoảng 2.3), tức viền màu bị lệch là nhìn thấy được nếu phóng to. (iii) PSNR RGB và SSIM giảm theo (ảnh T: 37.43 → 34.73 dB; SSIM 0.9757 → 0.9681). Sai số không phân bố đều giữa các ảnh nhưng đều cùng chiều: ở cả 7 ảnh T, ΔE tại biên màu ở 4:2:0 lớn hơn ở 4:4:4 (Bảng A1b trong `tables.md`). (iv) Nhóm G ít chịu thiệt nhất (PSNR RGB chỉ giảm 45.5 → 44.3 dB) vì màu biến thiên chậm, trung bình hoá 2×2 gần như không làm mất thông tin.

**Quan sát hình.** Ở `a1_badge_zoom.png`, đường biên đỏ–trắng của nhãn ở 4:2:0 hơi nhoè; các chữ vàng trên nền đỏ vẫn rõ nét vì độ sáng (kênh Y, giữ nguyên độ phân giải) vẫn mang hình dạng chữ. Do đó sai số do lấy mẫu sắc độ chủ yếu là sai màu ở viền, chưa phải mất khả năng đọc chữ; tôi chưa đo OCR ở phần này.

**Kết luận chọn tham số.** Dùng 4:2:0 (mặc định của Pillow) cho ảnh P và G. Với ảnh T có chữ/nhãn màu bão hoà, 4:4:4 giữ màu viền tốt hơn nhưng làm ảnh nặng gấp 1.26 lần bản 4:2:0 (cùng quality 75), nên chỉ dùng khi thương hiệu đòi hỏi màu nhãn chính xác. 4:2:2 là phương án trung gian ít được hỗ trợ tốt trên web.

## 3. A2 – JPEG: `optimize` và `progressive` (quality 75)

**Cơ chế.** Hai tuỳ chọn này **không đổi bước lượng tử hoá** nên không làm thay đổi hệ số DCT đã lượng tử; chúng chỉ thay đổi cách mã hoá entropy. `optimize=True` thay các bảng Huffman chuẩn (Annex K của chuẩn JPEG, được thiết kế theo thống kê ảnh chụp ở bitrate trung bình) bằng bảng Huffman tối ưu theo chính ảnh đó, đòi hỏi thêm một lượt thống kê. `progressive=True` mã hoá theo nhiều lượt quét (trước hệ số DC và tần số thấp, sau đến chi tiết), mỗi lượt có bảng Huffman riêng; vì vậy trình duyệt hiển thị được bản mờ sớm. Trong libjpeg-turbo chế độ progressive luôn bật tối ưu bảng Huffman, nên kết quả `optimize+progressive` trùng với `progressive`: trong thí nghiệm này hai cấu hình cho dung lượng bằng nhau ở cả 20 ảnh (xem `a2_raw.csv`).

**Kiểm tra chất lượng.** Với mọi ảnh và mọi cấu hình, ảnh giải mã giống hệt từng điểm ảnh với bản mặc định (`np.array_equal`, 20/20 ảnh), nên PSNR/SSIM giống hệt: trung bình PSNR là 37.329 dB ở cả bốn cấu hình. Vì vậy mọi mức giảm dung lượng dưới đây là "miễn phí" về chất lượng; cái giá duy nhất là thời gian.

| Nhóm | Cấu hình | Dung lượng (KB) | Giảm (%) | Mã hoá (ms) | Mã hoá (×) | Giải mã (ms) | Giải mã (×) |
|---|---|---|---|---|---|---|---|
| P (ảnh chụp) | mặc định | 40.5 | 0.0 | 2.2 | 1.0 | 2.7 | 1.0 |
| P (ảnh chụp) | optimize | 39.8 | 2.2 | 4.3 | 2.0 | 2.7 | 1.0 |
| P (ảnh chụp) | progressive | 39.0 | 3.6 | 9.2 | 4.2 | 6.2 | 2.4 |
| P (ảnh chụp) | optimize+progressive | 39.0 | 3.6 | 9.4 | 4.3 | 6.1 | 2.3 |
| T (ảnh có chữ) | mặc định | 57.6 | 0.0 | 5.3 | 1.0 | 7.1 | 1.0 |
| T (ảnh có chữ) | optimize | 53.6 | 6.6 | 8.2 | 1.6 | 6.4 | 0.9 |
| T (ảnh có chữ) | progressive | 50.1 | 12.5 | 15.4 | 3.1 | 12.1 | 1.7 |
| T (ảnh có chữ) | optimize+progressive | 50.1 | 12.5 | 16.3 | 3.2 | 13.1 | 1.8 |
| G (gradient) | mặc định | 19.1 | 0.0 | 4.7 | 1.0 | 5.2 | 1.0 |
| G (gradient) | optimize | 13.5 | 26.9 | 6.7 | 1.5 | 5.7 | 1.2 |
| G (gradient) | progressive | 13.9 | 24.4 | 11.8 | 2.6 | 9.5 | 1.9 |
| G (gradient) | optimize+progressive | 13.9 | 24.4 | 12.0 | 2.6 | 10.0 | 2.1 |

Hình: `figures/t08/a2_optimize_progressive.png` – (a) % giảm dung lượng, (b) thời gian mã hoá, (c) thời gian giải mã (tính theo % so với mặc định) theo nhóm ảnh.

**Kết quả và giải thích.** `optimize` giảm dung lượng 2.2% (P), 6.6% (T) và 26.9% (G); `progressive` giảm 3.6%, 12.5% và 24.4%. Mức giảm phụ thuộc mạnh vào nội dung: ảnh G (nền trơn, hầu hết khối 8×8 chỉ còn rất ít hệ số khác 0) lợi nhiều nhất, nhiều khả năng vì bảng Huffman chuẩn gán mã chưa ngắn nhất cho các ký hiệu thường gặp ở ảnh này (như chuỗi số 0 dài và EOB); ảnh P có thống kê gần với bảng chuẩn nên chỉ giảm vài phần trăm. Với ảnh T và P, `progressive` giảm nhiều hơn `optimize` đơn thuần nhiều khả năng vì mã hoá riêng từng lượt quét tạo ra các nhóm ký hiệu đồng nhất hơn (ví dụ các hệ số cao tần thưa thớt nằm riêng một lượt) nên bảng Huffman riêng của từng lượt khớp thống kê hơn; tôi chưa tách riêng nguyên nhân này bằng thí nghiệm.

**Chi phí thời gian** (nhiễu, chỉ đọc tỉ lệ): `optimize` làm mã hoá chậm khoảng 1.7 lần và hầu như không ảnh hưởng giải mã (1.0 lần); `progressive` làm mã hoá chậm khoảng 3.3 lần và giải mã chậm khoảng 2.0 lần, vì phải quét và cập nhật hệ số nhiều lượt. Về giá trị tuyệt đối, giải mã ảnh progressive cỡ 1000×1000 vẫn chỉ ở mức vài chục ms trong phép đo này, nhỏ so với thời gian tải ảnh qua mạng.

**Kết luận chọn tham số.** Luôn bật `optimize=True` (hoặc `progressive=True`, vì đã bao hàm tối ưu Huffman). Mã hoá JPEG cho catalog thường chỉ làm một lần ngoại tuyến nên chi phí mã hoá chấp nhận được; `progressive` đặc biệt nên dùng cho ảnh T (12.5% nhẹ hơn) và có lợi cảm nhận tốc độ hiển thị trên mạng chậm.

## 4. A3 – WebP lossy: tham số `method` (quality 75)

**Cơ chế.** `method` (0–6) trong libwebp không đổi định nghĩa của `quality` mà đổi **mức nỗ lực của bộ mã hoá** khi tìm cách mã hoá tốt nhất cho cùng một bước lượng tử: theo mô tả của libwebp, method thấp chọn chế độ dự đoán trong khung (intra) bằng heuristic nhanh, các method cao hơn thử nhiều chế độ hơn và chọn theo tối ưu tốc độ–méo (RD), method cao nhất còn thêm lượng tử hoá trellis. Giải mã không phụ thuộc method (cùng định dạng bitstream VP8), nên cột giải mã gần như không đổi.

| Nhóm | Method | Dung lượng (KB) | So với method 4 (%) | PSNR (dB) | SSIM | Mã hoá (ms) | Mã hoá (×method 4) |
|---|---|---|---|---|---|---|---|
| P (ảnh chụp) | 0 | 36.4 | 131.4 | 34.14 | 0.9276 | 17.7 | 0.20 |
| P (ảnh chụp) | 2 | 30.3 | 104.2 | 33.89 | 0.9284 | 32.8 | 0.38 |
| P (ảnh chụp) | 4 | 29.2 | 100.0 | 34.08 | 0.9321 | 85.9 | 1.00 |
| P (ảnh chụp) | 6 | 28.1 | 96.0 | 33.99 | 0.9305 | 121.4 | 1.39 |
| T (ảnh có chữ) | 0 | 40.0 | 135.4 | 36.57 | 0.9765 | 36.6 | 0.23 |
| T (ảnh có chữ) | 2 | 30.6 | 104.5 | 36.25 | 0.9766 | 60.3 | 0.38 |
| T (ảnh có chữ) | 4 | 29.2 | 100.0 | 36.27 | 0.9772 | 160.6 | 1.00 |
| T (ảnh có chữ) | 6 | 28.4 | 97.4 | 36.24 | 0.9766 | 198.6 | 1.26 |
| G (gradient) | 0 | 6.1 | 138.6 | 43.76 | 0.9757 | 29.4 | 0.20 |
| G (gradient) | 2 | 4.5 | 107.1 | 43.74 | 0.9759 | 47.7 | 0.34 |
| G (gradient) | 4 | 4.2 | 100.0 | 44.15 | 0.9771 | 133.6 | 1.00 |
| G (gradient) | 6 | 4.2 | 99.2 | 44.06 | 0.9771 | 145.0 | 1.08 |

Hình: `figures/t08/a3_webp_method.png` – (a) dung lượng (% so với method 4), (b) SSIM, (c) thời gian mã hoá (thang log) theo method, từng nhóm ảnh.

**Kết quả và giải thích.** Method 0 cho file bằng 131% (P), 135% (T) và 139% (G) dung lượng của method 4 – tức thừa khoảng 35% trên toàn tập – nhưng chỉ mã hoá nhanh bằng khoảng 0.21 lần method 4. Từ method 2 trở lên đường cong dung lượng bão hoà nhanh: method 2 chỉ lớn hơn method 4 khoảng 5%, còn method 6 nhỏ hơn method 4 chỉ 2.6% (P: 4.0%, T: 2.6%, G: 0.8%) với thời gian khoảng 1.3 lần: hiệu suất tăng giảm dần theo công sức tính toán.

Chất lượng gần như không đổi giữa các method (SSIM trung bình toàn tập: 0.9591, 0.9595, 0.9614, 0.9606 cho method 0, 2, 4, 6). Chú ý quan trọng: ở thí nghiệm này tôi giữ `quality` cố định chứ không giữ cố định bitrate, nên dung lượng và chất lượng cùng thay đổi; PSNR không đơn điệu theo method (ví dụ ảnh P: method 0 có PSNR 34.14 dB cao hơn method 4 (34.08 dB) chỉ vì file lớn hơn nhiều). Kết luận đúng là: method cao hơn cho **cùng chất lượng ở dung lượng nhỏ hơn** (đường RD tốt hơn), không phải "chất lượng cao hơn ở cùng dung lượng"; một so sánh chặt chẽ hơn cần đo đường cong RD ở nhiều quality, ngoài phạm vi ablation này.

**Kết luận chọn tham số.** Dùng method 4 (mặc định) cho chuyển đổi hàng loạt; dùng method 6 khi có thể mã hoá ngoại tuyến cho kho ảnh tĩnh (tiết kiệm thêm vài phần trăm dung lượng, mỗi ảnh tốn vài lần thời gian); không dùng method 0–2 cho ảnh web vì đánh đổi dung lượng quá lớn (chỉ hợp lý khi phải mã hoá tức thời).

## 5. A4 – PNG: `compress_level` và `optimize`

**Cơ chế.** PNG gồm hai bước: (1) với mỗi dòng ảnh Pillow chọn một trong các bộ lọc dự đoán (None, Sub, Up, Paeth) có tổng giá trị tuyệt đối phần dư nhỏ nhất; (2) nén phần dư bằng DEFLATE (LZ77 + Huffman) của zlib. `compress_level` điều khiển công sức tìm chuỗi lặp của LZ77: ở mức 1 zlib dùng thuật toán nhanh (khớp tham lam, chuỗi băm ngắn); từ mức 4 dùng khớp lười (lazy matching) và độ dài chuỗi tìm kiếm tăng dần (mức 6 khoảng 128 ứng viên, mức 9 khoảng 4096 ứng viên). Theo mã nguồn Pillow, `optimize=True` ép mức nén 9 (nên cấu hình `L1+optimize` trùng kết quả `optimize` ở mọi ảnh) và còn thử thêm bộ lọc Average ở mỗi dòng; thao tác là hoàn toàn không mất mát, tôi đã kiểm tra ảnh giải mã trùng khớp ảnh gốc ở 20/20 ảnh, mọi cấu hình.

| Nhóm | Cấu hình | Dung lượng (KB) | So với L6 (%) | Mã hoá (ms) | Mã hoá (×L6) | Giải mã (ms) |
|---|---|---|---|---|---|---|
| P (ảnh chụp) | L1 | 572.2 | 144.8 | 11.9 | 0.46 | 7.3 |
| P (ảnh chụp) | L6 | 400.0 | 100.0 | 28.5 | 1.00 | 7.2 |
| P (ảnh chụp) | L9 | 388.2 | 96.7 | 103.3 | 3.81 | 6.6 |
| P (ảnh chụp) | optimize | 386.1 | 96.2 | 106.3 | 3.91 | 6.3 |
| T (ảnh có chữ) | L1 | 279.4 | 137.6 | 11.7 | 0.57 | 5.2 |
| T (ảnh có chữ) | L6 | 200.4 | 100.0 | 21.0 | 1.00 | 6.2 |
| T (ảnh có chữ) | L9 | 192.5 | 96.4 | 90.4 | 4.14 | 6.5 |
| T (ảnh có chữ) | optimize | 192.4 | 96.3 | 86.7 | 3.99 | 6.4 |
| G (gradient) | L1 | 374.7 | 219.2 | 31.3 | 0.55 | 12.1 |
| G (gradient) | L6 | 205.9 | 100.0 | 59.5 | 1.00 | 11.2 |
| G (gradient) | L9 | 185.0 | 88.0 | 322.2 | 5.29 | 10.8 |
| G (gradient) | optimize | 183.1 | 87.4 | 315.8 | 5.26 | 10.2 |

Hình: `figures/t08/a4_png_compress.png` – (a) dung lượng (% so với L6), (b) thời gian mã hoá (thang log), (c) đường đánh đổi thời gian–dung lượng, theo nhóm ảnh.

**Kết quả và giải thích.** Tính trung bình toàn tập (271.9 KB ở L6), L1 làm file lớn hơn L6 khoảng 65% (ở ảnh G: 119%), trong khi mã hoá nhanh khoảng 0.52 lần. L9 chỉ nhỏ hơn L6 3.3% ở ảnh P và 3.6% ở ảnh T, nhưng chậm khoảng 3.8 và 4.1 lần: với ảnh chụp, nhiều nhiễu cảm biến nên phần dư sau lọc gần ngẫu nhiên và ít chuỗi lặp dài để tìm thêm. Ảnh G (nền trơn, nhiều dòng giống nhau sau lọc) lợi nhiều nhất: L9 nhỏ hơn L6 12.0%, `optimize` nhỏ hơn 12.6%. Phần lớn lợi ích này đến từ ảnh G sạch 1000×1000, còn ba ảnh G nhiễu 500×500 gần như không giảm (dưới 2%; xem `a4_raw.csv`). `optimize` nhỏ hơn L9 một chút (93.6% so với 94.0%, tính theo L6 = 100%) nhờ bộ lọc Average, đổi lấy thời gian cao hơn. Thời gian giải mã không phụ thuộc mức nén (8.0, 8.0 và 7.8 ms ở L1, L6, L9: chênh lệch nằm trong khoảng nhiễu), vì quá trình inflate luôn là phép đọc tuần tự bất kể mức nén.

Dù đã tối ưu, PNG vẫn rất nặng so với mã hoá có mất mát: L6 trung bình 272 KB so với 40 KB của JPEG q75 4:2:0 (A1).

**Kết luận chọn tham số.** Mức mặc định L6 là điểm cân bằng cho ảnh chụp. L9/`optimize` chỉ đáng dùng khi mã hoá ngoại tuyến các ảnh đồ hoạ, nền phẳng hoặc gradient (logo, banner, ảnh nền trơn), nơi lợi dung lượng tới 13%; không dùng L1 trừ khi cần tốc độ tối đa.

## 6. A5 – WebP không mất mát: `quality` (mức nỗ lực) × `method`

**Cơ chế.** Trong chế độ `lossless=True`, tham số `quality` **không** điều khiển độ trung thực (ảnh luôn khôi phục đúng 100%): nó là mức nỗ lực nén (0 nhanh nhất, 100 chậm nhất, nén nhiều nhất). WebP lossless dự đoán điểm ảnh từ lân cận, có thể áp các phép biến đổi (dự đoán không gian, tương quan giữa các kênh màu, trừ màu xanh lục, bảng màu) rồi mã hoá entropy bằng LZ77 và mã Huffman theo ngữ cảnh. Method và quality quyết định số biến đổi/tham số được thử; theo mô tả của libwebp các mức thấp thử ít lựa chọn hơn. Tôi chạy lưới 3×3 (method 0/4/6 × quality 0/50/100); bảng đầy đủ ở `tables.md`, bảng dưới là các tổ hợp tiêu biểu. Cả 9 cấu hình đều khôi phục chính xác 20/20 ảnh. Mốc so sánh là PNG L9 trên cùng ảnh.

| Nhóm | Cấu hình WebP lossless | Dung lượng (KB) | So với PNG L9 (%) | Mã hoá (ms) |
|---|---|---|---|---|
| P (ảnh chụp) | method 0, quality 0 | 342.3 | 88.9 | 24 |
| P (ảnh chụp) | method 0, quality 100 | 341.2 | 88.5 | 55 |
| P (ảnh chụp) | method 4, quality 0 | 307.8 | 79.7 | 209 |
| P (ảnh chụp) | method 4, quality 100 | 304.9 | 78.6 | 673 |
| P (ảnh chụp) | method 6, quality 100 | 300.8 | 77.5 | 9195 |
| T (ảnh có chữ) | method 0, quality 0 | 230.2 | 114.9 | 24 |
| T (ảnh có chữ) | method 0, quality 100 | 174.5 | 89.6 | 34 |
| T (ảnh có chữ) | method 4, quality 0 | 137.1 | 70.9 | 193 |
| T (ảnh có chữ) | method 4, quality 100 | 133.5 | 69.0 | 290 |
| T (ảnh có chữ) | method 6, quality 100 | 131.0 | 67.5 | 2388 |
| G (gradient) | method 0, quality 0 | 246.5 | 408.6 | 46 |
| G (gradient) | method 0, quality 100 | 196.5 | 129.6 | 85 |
| G (gradient) | method 4, quality 0 | 161.2 | 84.4 | 285 |
| G (gradient) | method 4, quality 100 | 150.5 | 70.9 | 564 |
| G (gradient) | method 6, quality 100 | 149.5 | 70.4 | 5861 |

Hình: `figures/t08/a5_webp_lossless.png` – dung lượng (% so với PNG L9, thang log) theo thời gian mã hoá (thang log), từng nhóm ảnh; mỗi đường là một method, đi từ quality 0 đến quality 100.

**Kết quả và giải thích.** (i) **Method quan trọng hơn quality.** Toàn tập, ở quality 100 chuyển từ method 0 sang method 4 giảm dung lượng từ 239 xuống 199 KB, trong khi tăng quality từ 0 lên 100 ở method 4 chỉ giảm từ 204 xuống 199 KB. (ii) **Lợi ích giảm dần rất nhanh:** từ method 4 lên method 6 ở quality 100 dung lượng chỉ giảm thêm từ 199 xuống 196 KB (method 4 lớn hơn method 6 1.013 lần) trong khi thời gian chậm khoảng 11.5 lần (đo nhiễu), trung bình 5812 ms mỗi ảnh. (iii) So với PNG L9, WebP lossless method 4 quality 100 chỉ còn 79% (P), 69% (T), 71% (G) dung lượng, với thời gian mã hoá cùng bậc (trung bình toàn tập: PNG L9 164 ms, WebP method 4 quality 100 506 ms; số đo nhiễu). (iv) **Thất bại cần ghi nhận:** method 0 không phải lúc nào cũng thắng PNG. Ở ảnh G, method 0 quality 0 bằng 409% dung lượng PNG L9 (trung bình theo ảnh) và ở ảnh T bằng 115%. Phần lớn mức chênh ở nhóm G đến từ một ảnh: G03 (chỉ có 1188 màu phân biệt, so với 3181 màu của G01) nặng 287 KB ở method 0 quality 0 nhưng chỉ 10 KB ở method 4 và 15 KB với PNG L9 (cột `n_colors`, `png9_kb` trong `a5_raw.csv`); điều này phù hợp với giả thuyết method thấp không thử các biến đổi (bảng màu/dự đoán) phù hợp cho ảnh đồ hoạ ít màu, nhưng tôi chưa kiểm chứng riêng bằng cách bật/tắt từng biến đổi.

**Kết luận chọn tham số.** Với ảnh cần giữ nguyên tuyệt đối (ảnh gốc lưu trữ, logo), dùng WebP lossless **method 4**, quality ở mức trung bình (khoảng 50–100): nhỏ hơn PNG L9 khoảng 27% trong khi thời gian vẫn chấp nhận được; chỉ dùng method 6, quality 100 cho tài sản tĩnh, mã hoá một lần. Tránh method 0 cho ảnh có nền phẳng/gradient hoặc ít màu.

## 7. A6 – Độ phân giải: 1000 px so với 500 px

**Phương pháp.** Bảy ảnh gốc 1000×1000 (T01–T04, G01–G03) được thu nhỏ còn 500×500 bằng Lanczos (`Image.LANCZOS`), sau đó nén JPEG q75 và WebP q75 (method 4) và so bpp = 8·số byte/(rộng·cao). Ảnh P không có bản 1000 px (nguồn gốc 500 px) nên không tham gia. Để kiểm chứng giả thuyết "ảnh lớn có tương quan không gian cao hơn", tôi đo hệ số tương quan Pearson giữa các cặp điểm ảnh kề ngang (kênh Y) và độ lớn gradient trung bình của chính ảnh trước khi nén.

| Ảnh | JPEG 1000 | JPEG 500 | Tỉ số | WebP 1000 | WebP 500 | Tỉ số | Tương quan kề 1000 | Tương quan kề 500 |
|---|---|---|---|---|---|---|---|---|
| T01 | 0.677 | 1.014 | 1.50 | 0.338 | 0.572 | 1.69 | 0.9665 | 0.9415 |
| T02 | 0.553 | 0.833 | 1.51 | 0.254 | 0.429 | 1.69 | 0.9733 | 0.9536 |
| T03 | 0.662 | 0.987 | 1.49 | 0.333 | 0.576 | 1.73 | 0.9654 | 0.9375 |
| T04 | 0.645 | 0.945 | 1.46 | 0.320 | 0.541 | 1.69 | 0.9641 | 0.9357 |
| G01 | 0.236 | 0.335 | 1.42 | 0.064 | 0.111 | 1.74 | 0.9984 | 0.9960 |
| G02 | 0.225 | 0.336 | 1.50 | 0.044 | 0.070 | 1.59 | 0.9948 | 0.9874 |
| G03 | 0.217 | 0.306 | 1.41 | 0.029 | 0.050 | 1.68 | 0.9969 | 0.9920 |
| **TB nhóm T** | 0.634 | 0.945 | 1.49 | 0.311 | 0.529 | 1.70 | 0.9673 | 0.9420 |
| **TB nhóm G** | 0.226 | 0.326 | 1.44 | 0.046 | 0.077 | 1.68 | 0.9967 | 0.9918 |

Hình: `figures/t08/a6_resolution.png` – (a) bpp của JPEG q75, (b) bpp của WebP q75 ở hai độ phân giải cho từng ảnh; (c) tương quan kề ở 500 px so với 1000 px (đường nét đứt là y = x).

**Kết quả và giải thích.** Ảnh 1000 px có bpp thấp hơn ảnh 500 px ở **cả 7 ảnh và cả hai định dạng**: JPEG dùng bpp ở 500 px gấp 1.49 lần ở 1000 px với nhóm T và 1.44 lần với nhóm G; WebP tương ứng 1.70 và 1.68 lần. Hệ quả thực dụng: nhân 4 số điểm ảnh chỉ làm file lớn khoảng 2.7 lần với JPEG và 2.4 lần với WebP (nhóm T), chứ không phải 4 lần.

Cơ chế: tương quan giữa các điểm ảnh kề nhau cao hơn ở ảnh độ phân giải lớn (nhóm T: 0.9673 ở 1000 px so với 0.9420 ở 500 px; nhóm G: 0.9967 so với 0.9918), và gradient trung bình thấp hơn (nhóm T: 4.54 so với 6.85 mức xám/điểm ảnh). Thu nhỏ một nửa nén cùng nội dung vào 1/4 số điểm ảnh: một nét chữ hay một viền rộng 2 px còn 1 px, nên mỗi khối 8×8 của JPEG chứa nhiều biên hơn, nhiều hệ số AC khác 0 hơn và ít chuỗi số 0 hơn, kéo bpp tăng. Cùng lý do khiến chất lượng ở 500 px thấp hơn ở cùng quality: PSNR trung bình 38.79 dB (500 px) so với 40.87 dB (1000 px) với JPEG, vì cùng một bảng lượng tử hoá được áp lên nội dung nhiều tần số cao hơn. WebP hưởng lợi nhiều hơn từ ảnh lớn (tỉ số bpp 1.70 so với 1.48 của JPEG, trung bình 7 ảnh), nhiều khả năng vì dự đoán trong khung của VP8 khai thác trực tiếp vùng nhẵn rộng, còn JPEG chỉ dự đoán hệ số DC giữa các khối. Lưu ý WebP và JPEG ở cùng q = 75 không có cùng chất lượng, nên phép so sánh này chỉ là so sánh *tỉ số* giữa hai độ phân giải của từng định dạng, không phải so sánh hiệu suất tuyệt đối của hai định dạng.

**Kết luận.** Với trang web, ảnh sản phẩm 1000×1000 tốn trung bình chỉ khoảng 2.7 lần (JPEG) và 2.4 lần (WebP) dung lượng của bản 500×500: nên cung cấp hai kích thước (thumbnail 500 px cho danh sách, 1000 px cho trang chi tiết, qua `srcset`) và không nên dùng bpp của ảnh 500 px để ước tính dung lượng ảnh lớn (hoặc ngược lại).

## 8. Tổng hợp lựa chọn tham số cho khuyến nghị cuối

| Định dạng | Tham số khuyến nghị | Lý do (từ ablation) |
|---|---|---|
| JPEG | quality 75, lấy mẫu 4:2:0, `optimize=True` (hoặc `progressive=True`) | 4:2:0 tiết kiệm 23% so với 4:4:4; tối ưu Huffman giảm thêm 11–13% (trung bình 20 ảnh) mà ảnh giải mã giống hệt; ảnh T có nhãn màu bão hoà: cân nhắc 4:4:4 hoặc 4:2:2 |
| WebP lossy | quality 75, method 4 (tức thời) hoặc 6 (ngoại tuyến) | method 2 và method 0 làm file lớn hơn method 4 lần lượt 5% và 35%; method 6 chỉ nhỏ hơn thêm 2.6% |
| PNG | `compress_level` 6; L9/`optimize` chỉ cho đồ hoạ phẳng ngoại tuyến | L9 chỉ giảm 3.3% (ảnh P) nhưng chậm gấp 3.8 lần |
| WebP lossless | method 4, quality 50–100 | nhỏ hơn PNG L9 khoảng 27%; tránh method 0 cho ảnh nền phẳng |
| Kích thước | cung cấp cả 500 và 1000 px | bpp ở 1000 px thấp hơn ở 500 px (A6) |

**Hạn chế.** (1) Thời gian bị nhiễu như đã nêu ở mục 1; đừng trích số ms tuyệt đối khi chưa đo lại tuần tự. (2) Các ablation đo trên 20 ảnh (7/7/6 theo nhóm); trung bình theo nhóm chịu ảnh hưởng của các ảnh ngoại lệ (đặc biệt G03 ở A4, A5). (3) A1–A5 cố định quality 75 (lossy) nên kết luận về method, lấy mẫu sắc độ có thể thay đổi ở quality khác; chưa dựng đường cong RD đầy đủ. (4) Nhóm T, G là ảnh tổng hợp; A6 thu nhỏ ảnh tổng hợp có nội dung được sinh ở 1000 px, nên chưa chứng minh được xu hướng với ảnh chụp thật. (5) Chưa đo OCR ở các ablation này, nên "chữ còn đọc được" mới chỉ được suy ra từ ΔE/hình, không phải từ OCR.
