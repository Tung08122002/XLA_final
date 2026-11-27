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

**Lưu ý về số đo thời gian.** Với mỗi ảnh và mỗi cấu hình, thời gian là trung vị của 7 lần lặp (A2–A4) hoặc 3 lần lặp (A5, vì WebP lossless method 6, quality 100 mất hàng giây mỗi lần mã hoá), qua `evaluate(..., repeats=N)`; bảng báo cáo trung bình các trung vị đó theo nhóm. Các số liệu đó được đo khi máy chỉ có 2 lõi và đang chạy song song nhiều tiến trình khác (load average 1 phút lúc bắt đầu các ablation có đo thời gian: @@LOAD@@), nên **giá trị tuyệt đối (ms) bị nhiễu và có thể sai lệch đáng kể; chỉ nên đọc tỉ lệ tương đối giữa các cấu hình trong cùng một bảng**. Dung lượng, PSNR và SSIM là tất định và không bị ảnh hưởng. Script có thể chạy lại tuần tự trên máy rảnh để cập nhật toàn bộ số thời gian (`python src/t08_ablation.py`).

## 2. A1 – JPEG: lấy mẫu sắc độ (quality 75)

**Cơ chế.** JPEG đổi RGB sang YCbCr rồi có thể giảm độ phân giải hai kênh màu Cb, Cr trước khi biến đổi DCT. Ở 4:4:4 không giảm; 4:2:2 trung bình hoá mỗi cặp điểm ảnh theo chiều ngang (Cb, Cr còn 1/2 số mẫu); 4:2:0 trung bình hoá mỗi khối 2×2 (còn 1/4 số mẫu). Cách làm này dựa trên việc thị giác người kém nhạy với chi tiết màu hơn chi tiết sáng. Ngược lại, tại biên có sắc độ thay đổi gắt (chữ đỏ trên nền trắng, nhãn giảm giá đỏ–vàng) giá trị Cb, Cr nhảy hàng trăm mức trong 1 điểm ảnh, nên việc lấy trung bình làm biên màu bị "loang" sang điểm ảnh bên cạnh.

Ngoài PSNR/SSIM trên RGB, tôi đo PSNR riêng từng kênh Cb, Cr (YCbCr BT.601 toàn dải) và ΔE CIE76 (trong không gian CIELAB). ΔE được tính hai cách: trung bình toàn ảnh và trung bình **tại các điểm ảnh sát biên màu** (gradient của Cb hoặc Cr trong ảnh gốc lớn hơn 30 mức/điểm ảnh, giãn 2 px); vùng này chiếm tỉ lệ @@S/a1/edge_frac/T/4:2:0|.3f@@ số điểm ảnh của ảnh T (tức chỉ vài phần trăm) nên ΔE trung bình toàn ảnh (@@S/a1/de_mean/T/4:4:4|.2f@@ ở 4:4:4 và @@S/a1/de_mean/T/4:2:0|.2f@@ ở 4:2:0) "pha loãng" lỗi màu cục bộ.

@@TABLE/c1@@

Hình: `figures/t08/a1_subsampling.png` – (a) dung lượng, (b) PSNR kênh Cb, (c) PSNR kênh Cr, (d) ΔE tại biên màu theo kiểu lấy mẫu sắc độ, từng nhóm ảnh. Hình: `figures/t08/a1_badge_zoom.png` – nhãn "-35%" của T01 phóng 4 lần (gốc, 4:4:4, 4:2:2, 4:2:0). Hình: `figures/t08/a1_crops.png` – vùng giá và nhãn giảm giá của T01 và T05.

**Kết quả và giải thích.** (i) Giảm lấy mẫu sắc độ tiết kiệm dung lượng đáng kể: ở ảnh T, 4:2:2 giảm @@D/a1/size_rel_pct/T/4:2:2|.1f@@% và 4:2:0 giảm @@D/a1/size_rel_pct/T/4:2:0|.1f@@% so với 4:4:4 (ảnh P: @@D/a1/size_rel_pct/P/4:2:0|.1f@@%; ảnh G: @@D/a1/size_rel_pct/G/4:2:0|.1f@@%), vì hai kênh màu mất 50–75% số hệ số cần mã hoá. (ii) Cái giá phải trả tập trung ở màu: ở ảnh T, PSNR kênh Cb giảm từ @@S/a1/psnr_cb/T/4:4:4|.1f@@ xuống @@S/a1/psnr_cb/T/4:2:0|.1f@@ dB và kênh Cr từ @@S/a1/psnr_cr/T/4:4:4|.1f@@ xuống @@S/a1/psnr_cr/T/4:2:0|.1f@@ dB; kênh sáng Y giảm ít hơn nhiều (từ @@S/a1/psnr_y/T/4:4:4|.1f@@ xuống @@S/a1/psnr_y/T/4:2:0|.1f@@ dB; phần giảm nhỏ này có thể do lỗi màu lan sang Y khi đổi RGB↔YCbCr), điều này phù hợp với cơ chế: chỉ kênh màu bị trung bình hoá. ΔE tại biên màu của ảnh T tăng từ @@S/a1/de_edge/T/4:4:4|.1f@@ lên @@S/a1/de_edge/T/4:2:0|.1f@@, gấp @@R/a1/de_edge/T/4:2:0/4:4:4|.1f@@ lần; giá trị cỡ 10 vượt xa ngưỡng nhận biết khác biệt màu thường dùng cho CIE76 (khoảng 2.3), tức viền màu bị lệch là nhìn thấy được nếu phóng to. (iii) PSNR RGB và SSIM giảm theo (ảnh T: @@S/a1/psnr/T/4:4:4|.2f@@ → @@S/a1/psnr/T/4:2:0|.2f@@ dB; SSIM @@S/a1/ssim/T/4:4:4|.4f@@ → @@S/a1/ssim/T/4:2:0|.4f@@). Sai số không phân bố đều giữa các ảnh nhưng đều cùng chiều: ở cả 7 ảnh T, ΔE tại biên màu ở 4:2:0 lớn hơn ở 4:4:4 (Bảng A1b trong `tables.md`). (iv) Nhóm G ít chịu thiệt nhất (PSNR RGB chỉ giảm @@S/a1/psnr/G/4:4:4|.1f@@ → @@S/a1/psnr/G/4:2:0|.1f@@ dB) vì màu biến thiên chậm, trung bình hoá 2×2 gần như không làm mất thông tin.

**Quan sát hình.** Ở `a1_badge_zoom.png`, đường biên đỏ–trắng của nhãn ở 4:2:0 hơi nhoè; các chữ vàng trên nền đỏ vẫn rõ nét vì độ sáng (kênh Y, giữ nguyên độ phân giải) vẫn mang hình dạng chữ. Do đó sai số do lấy mẫu sắc độ chủ yếu là sai màu ở viền, chưa phải mất khả năng đọc chữ; tôi chưa đo OCR ở phần này.

**Kết luận chọn tham số.** Dùng 4:2:0 (mặc định của Pillow) cho ảnh P và G. Với ảnh T có chữ/nhãn màu bão hoà, 4:4:4 giữ màu viền tốt hơn nhưng làm ảnh nặng gấp @@R/a1/size_kb/T/4:4:4/4:2:0|.2f@@ lần bản 4:2:0 (cùng quality 75), nên chỉ dùng khi thương hiệu đòi hỏi màu nhãn chính xác. 4:2:2 là phương án trung gian ít được hỗ trợ tốt trên web.

## 3. A2 – JPEG: `optimize` và `progressive` (quality 75)

**Cơ chế.** Hai tuỳ chọn này **không đổi bước lượng tử hoá** nên không làm thay đổi hệ số DCT đã lượng tử; chúng chỉ thay đổi cách mã hoá entropy. `optimize=True` thay các bảng Huffman chuẩn (Annex K của chuẩn JPEG, được thiết kế theo thống kê ảnh chụp ở bitrate trung bình) bằng bảng Huffman tối ưu theo chính ảnh đó, đòi hỏi thêm một lượt thống kê. `progressive=True` mã hoá theo nhiều lượt quét (trước hệ số DC và tần số thấp, sau đến chi tiết), mỗi lượt có bảng Huffman riêng; vì vậy trình duyệt hiển thị được bản mờ sớm. Trong libjpeg-turbo chế độ progressive luôn bật tối ưu bảng Huffman, nên kết quả `optimize+progressive` trùng với `progressive`: trong thí nghiệm này hai cấu hình cho dung lượng bằng nhau ở cả 20 ảnh (xem `a2_raw.csv`).

**Kiểm tra chất lượng.** Với mọi ảnh và mọi cấu hình, ảnh giải mã giống hệt từng điểm ảnh với bản mặc định (`np.array_equal`, 20/20 ảnh), nên PSNR/SSIM giống hệt: trung bình PSNR là @@S/a2/psnr/ALL/mặc định|.3f@@ dB ở cả bốn cấu hình. Vì vậy mọi mức giảm dung lượng dưới đây là "miễn phí" về chất lượng; cái giá duy nhất là thời gian.

@@TABLE/c2@@

Hình: `figures/t08/a2_optimize_progressive.png` – (a) % giảm dung lượng, (b) thời gian mã hoá, (c) thời gian giải mã (tính theo % so với mặc định) theo nhóm ảnh.

**Kết quả và giải thích.** `optimize` giảm dung lượng @@S/a2/size_reduction_pct/P/optimize|.1f@@% (P), @@S/a2/size_reduction_pct/T/optimize|.1f@@% (T) và @@S/a2/size_reduction_pct/G/optimize|.1f@@% (G); `progressive` giảm @@S/a2/size_reduction_pct/P/progressive|.1f@@%, @@S/a2/size_reduction_pct/T/progressive|.1f@@% và @@S/a2/size_reduction_pct/G/progressive|.1f@@%. Mức giảm phụ thuộc mạnh vào nội dung: ảnh G (nền trơn, hầu hết khối 8×8 chỉ còn rất ít hệ số khác 0) lợi nhiều nhất, nhiều khả năng vì bảng Huffman chuẩn gán mã chưa ngắn nhất cho các ký hiệu thường gặp ở ảnh này (như chuỗi số 0 dài và EOB); ảnh P có thống kê gần với bảng chuẩn nên chỉ giảm vài phần trăm. Với ảnh T và P, `progressive` giảm nhiều hơn `optimize` đơn thuần nhiều khả năng vì mã hoá riêng từng lượt quét tạo ra các nhóm ký hiệu đồng nhất hơn (ví dụ các hệ số cao tần thưa thớt nằm riêng một lượt) nên bảng Huffman riêng của từng lượt khớp thống kê hơn; tôi chưa tách riêng nguyên nhân này bằng thí nghiệm.

**Chi phí thời gian** (nhiễu, chỉ đọc tỉ lệ): `optimize` làm mã hoá chậm khoảng @@X/a2/enc_rel_pct/ALL/optimize|.1f@@ lần và hầu như không ảnh hưởng giải mã (@@X/a2/dec_rel_pct/ALL/optimize|.1f@@ lần); `progressive` làm mã hoá chậm khoảng @@X/a2/enc_rel_pct/ALL/progressive|.1f@@ lần và giải mã chậm khoảng @@X/a2/dec_rel_pct/ALL/progressive|.1f@@ lần, vì phải quét và cập nhật hệ số nhiều lượt. Về giá trị tuyệt đối, giải mã ảnh progressive cỡ 1000×1000 vẫn chỉ ở mức vài chục ms trong phép đo này, nhỏ so với thời gian tải ảnh qua mạng.

**Kết luận chọn tham số.** Luôn bật `optimize=True` (hoặc `progressive=True`, vì đã bao hàm tối ưu Huffman). Mã hoá JPEG cho catalog thường chỉ làm một lần ngoại tuyến nên chi phí mã hoá chấp nhận được; `progressive` đặc biệt nên dùng cho ảnh T (@@S/a2/size_reduction_pct/T/progressive|.1f@@% nhẹ hơn) và có lợi cảm nhận tốc độ hiển thị trên mạng chậm.

## 4. A3 – WebP lossy: tham số `method` (quality 75)

**Cơ chế.** `method` (0–6) trong libwebp không đổi định nghĩa của `quality` mà đổi **mức nỗ lực của bộ mã hoá** khi tìm cách mã hoá tốt nhất cho cùng một bước lượng tử: theo mô tả của libwebp, method thấp chọn chế độ dự đoán trong khung (intra) bằng heuristic nhanh, các method cao hơn thử nhiều chế độ hơn và chọn theo tối ưu tốc độ–méo (RD), method cao nhất còn thêm lượng tử hoá trellis. Giải mã không phụ thuộc method (cùng định dạng bitstream VP8), nên cột giải mã gần như không đổi.

@@TABLE/c3@@

Hình: `figures/t08/a3_webp_method.png` – (a) dung lượng (% so với method 4), (b) SSIM, (c) thời gian mã hoá (thang log) theo method, từng nhóm ảnh.

**Kết quả và giải thích.** Method 0 cho file bằng @@S/a3/size_rel_pct/P/m0|.0f@@% (P), @@S/a3/size_rel_pct/T/m0|.0f@@% (T) và @@S/a3/size_rel_pct/G/m0|.0f@@% (G) dung lượng của method 4 – tức thừa khoảng @@E/a3/size_rel_pct/ALL/m0|.0f@@% trên toàn tập – nhưng chỉ mã hoá nhanh bằng khoảng @@X/a3/enc_rel_pct/ALL/m0|.2f@@ lần method 4. Từ method 2 trở lên đường cong dung lượng bão hoà nhanh: method 2 chỉ lớn hơn method 4 khoảng @@E/a3/size_rel_pct/ALL/m2|.0f@@%, còn method 6 nhỏ hơn method 4 chỉ @@D/a3/size_rel_pct/ALL/m6|.1f@@% (P: @@D/a3/size_rel_pct/P/m6|.1f@@%, T: @@D/a3/size_rel_pct/T/m6|.1f@@%, G: @@D/a3/size_rel_pct/G/m6|.1f@@%) với thời gian khoảng @@X/a3/enc_rel_pct/ALL/m6|.1f@@ lần: hiệu suất tăng giảm dần theo công sức tính toán.

Chất lượng gần như không đổi giữa các method (SSIM trung bình toàn tập: @@S/a3/ssim/ALL/m0|.4f@@, @@S/a3/ssim/ALL/m2|.4f@@, @@S/a3/ssim/ALL/m4|.4f@@, @@S/a3/ssim/ALL/m6|.4f@@ cho method 0, 2, 4, 6). Chú ý quan trọng: ở thí nghiệm này tôi giữ `quality` cố định chứ không giữ cố định bitrate, nên dung lượng và chất lượng cùng thay đổi; PSNR không đơn điệu theo method (ví dụ ảnh P: method 0 có PSNR @@S/a3/psnr/P/m0|.2f@@ dB cao hơn method 4 (@@S/a3/psnr/P/m4|.2f@@ dB) chỉ vì file lớn hơn nhiều). Kết luận đúng là: method cao hơn cho **cùng chất lượng ở dung lượng nhỏ hơn** (đường RD tốt hơn), không phải "chất lượng cao hơn ở cùng dung lượng"; một so sánh chặt chẽ hơn cần đo đường cong RD ở nhiều quality, ngoài phạm vi ablation này.

**Kết luận chọn tham số.** Dùng method 4 (mặc định) cho chuyển đổi hàng loạt; dùng method 6 khi có thể mã hoá ngoại tuyến cho kho ảnh tĩnh (tiết kiệm thêm vài phần trăm dung lượng, mỗi ảnh tốn vài lần thời gian); không dùng method 0–2 cho ảnh web vì đánh đổi dung lượng quá lớn (chỉ hợp lý khi phải mã hoá tức thời).

## 5. A4 – PNG: `compress_level` và `optimize`

**Cơ chế.** PNG gồm hai bước: (1) với mỗi dòng ảnh Pillow chọn một trong các bộ lọc dự đoán (None, Sub, Up, Paeth) có tổng giá trị tuyệt đối phần dư nhỏ nhất; (2) nén phần dư bằng DEFLATE (LZ77 + Huffman) của zlib. `compress_level` điều khiển công sức tìm chuỗi lặp của LZ77: ở mức 1 zlib dùng thuật toán nhanh (khớp tham lam, chuỗi băm ngắn); từ mức 4 dùng khớp lười (lazy matching) và độ dài chuỗi tìm kiếm tăng dần (mức 6 khoảng 128 ứng viên, mức 9 khoảng 4096 ứng viên). Theo mã nguồn Pillow, `optimize=True` ép mức nén 9 (nên cấu hình `L1+optimize` trùng kết quả `optimize` ở mọi ảnh) và còn thử thêm bộ lọc Average ở mỗi dòng; thao tác là hoàn toàn không mất mát, tôi đã kiểm tra ảnh giải mã trùng khớp ảnh gốc ở 20/20 ảnh, mọi cấu hình.

@@TABLE/c4@@

Hình: `figures/t08/a4_png_compress.png` – (a) dung lượng (% so với L6), (b) thời gian mã hoá (thang log), (c) đường đánh đổi thời gian–dung lượng, theo nhóm ảnh.

**Kết quả và giải thích.** Tính trung bình toàn tập (@@S/a4/size_kb/ALL/L6|.1f@@ KB ở L6), L1 làm file lớn hơn L6 khoảng @@E/a4/size_rel_pct/ALL/L1|.0f@@% (ở ảnh G: @@E/a4/size_rel_pct/G/L1|.0f@@%), trong khi mã hoá nhanh khoảng @@X/a4/enc_rel_pct/ALL/L1|.2f@@ lần. L9 chỉ nhỏ hơn L6 @@D/a4/size_rel_pct/P/L9|.1f@@% ở ảnh P và @@D/a4/size_rel_pct/T/L9|.1f@@% ở ảnh T, nhưng chậm khoảng @@X/a4/enc_rel_pct/P/L9|.1f@@ và @@X/a4/enc_rel_pct/T/L9|.1f@@ lần: với ảnh chụp, nhiều nhiễu cảm biến nên phần dư sau lọc gần ngẫu nhiên và ít chuỗi lặp dài để tìm thêm. Ảnh G (nền trơn, nhiều dòng giống nhau sau lọc) lợi nhiều nhất: L9 nhỏ hơn L6 @@D/a4/size_rel_pct/G/L9|.1f@@%, `optimize` nhỏ hơn @@D/a4/size_rel_pct/G/optimize|.1f@@%. Phần lớn lợi ích này đến từ ảnh G sạch 1000×1000, còn ba ảnh G nhiễu 500×500 gần như không giảm (dưới 2%; xem `a4_raw.csv`). `optimize` nhỏ hơn L9 một chút (@@S/a4/size_rel_pct/ALL/optimize|.1f@@% so với @@S/a4/size_rel_pct/ALL/L9|.1f@@%, tính theo L6 = 100%) nhờ bộ lọc Average, đổi lấy thời gian cao hơn. Thời gian giải mã không phụ thuộc mức nén (@@S/a4/dec_ms/ALL/L1|.1f@@, @@S/a4/dec_ms/ALL/L6|.1f@@ và @@S/a4/dec_ms/ALL/L9|.1f@@ ms ở L1, L6, L9: chênh lệch nằm trong khoảng nhiễu), vì quá trình inflate luôn là phép đọc tuần tự bất kể mức nén.

Dù đã tối ưu, PNG vẫn rất nặng so với mã hoá có mất mát: L6 trung bình @@S/a4/size_kb/ALL/L6|.0f@@ KB so với @@S/a1/size_kb/ALL/4:2:0|.0f@@ KB của JPEG q75 4:2:0 (A1).

**Kết luận chọn tham số.** Mức mặc định L6 là điểm cân bằng cho ảnh chụp. L9/`optimize` chỉ đáng dùng khi mã hoá ngoại tuyến các ảnh đồ hoạ, nền phẳng hoặc gradient (logo, banner, ảnh nền trơn), nơi lợi dung lượng tới @@D/a4/size_rel_pct/G/optimize|.0f@@%; không dùng L1 trừ khi cần tốc độ tối đa.

## 6. A5 – WebP không mất mát: `quality` (mức nỗ lực) × `method`

**Cơ chế.** Trong chế độ `lossless=True`, tham số `quality` **không** điều khiển độ trung thực (ảnh luôn khôi phục đúng 100%): nó là mức nỗ lực nén (0 nhanh nhất, 100 chậm nhất, nén nhiều nhất). WebP lossless dự đoán điểm ảnh từ lân cận, có thể áp các phép biến đổi (dự đoán không gian, tương quan giữa các kênh màu, trừ màu xanh lục, bảng màu) rồi mã hoá entropy bằng LZ77 và mã Huffman theo ngữ cảnh. Method và quality quyết định số biến đổi/tham số được thử; theo mô tả của libwebp các mức thấp thử ít lựa chọn hơn. Tôi chạy lưới 3×3 (method 0/4/6 × quality 0/50/100); bảng đầy đủ ở `tables.md`, bảng dưới là các tổ hợp tiêu biểu. Cả 9 cấu hình đều khôi phục chính xác 20/20 ảnh. Mốc so sánh là PNG L9 trên cùng ảnh.

@@TABLE/c5@@

Hình: `figures/t08/a5_webp_lossless.png` – dung lượng (% so với PNG L9, thang log) theo thời gian mã hoá (thang log), từng nhóm ảnh; mỗi đường là một method, đi từ quality 0 đến quality 100.

**Kết quả và giải thích.** (i) **Method quan trọng hơn quality.** Toàn tập, ở quality 100 chuyển từ method 0 sang method 4 giảm dung lượng từ @@S/a5/size_kb/ALL/m0-q100|.0f@@ xuống @@S/a5/size_kb/ALL/m4-q100|.0f@@ KB, trong khi tăng quality từ 0 lên 100 ở method 4 chỉ giảm từ @@S/a5/size_kb/ALL/m4-q0|.0f@@ xuống @@S/a5/size_kb/ALL/m4-q100|.0f@@ KB. (ii) **Lợi ích giảm dần rất nhanh:** từ method 4 lên method 6 ở quality 100 dung lượng chỉ giảm thêm từ @@S/a5/size_kb/ALL/m4-q100|.0f@@ xuống @@S/a5/size_kb/ALL/m6-q100|.0f@@ KB (method 4 lớn hơn method 6 @@R/a5/size_kb/ALL/m4-q100/m6-q100|.3f@@ lần) trong khi thời gian chậm khoảng @@R/a5/enc_ms/ALL/m6-q100/m4-q100|.1f@@ lần (đo nhiễu), trung bình @@S/a5/enc_ms/ALL/m6-q100|.0f@@ ms mỗi ảnh. (iii) So với PNG L9, WebP lossless method 4 quality 100 chỉ còn @@S/a5/size_vs_png9_pct/P/m4-q100|.0f@@% (P), @@S/a5/size_vs_png9_pct/T/m4-q100|.0f@@% (T), @@S/a5/size_vs_png9_pct/G/m4-q100|.0f@@% (G) dung lượng, với thời gian mã hoá cùng bậc (trung bình toàn tập: PNG L9 @@S/a4/enc_ms/ALL/L9|.0f@@ ms, WebP method 4 quality 100 @@S/a5/enc_ms/ALL/m4-q100|.0f@@ ms; số đo nhiễu). (iv) **Thất bại cần ghi nhận:** method 0 không phải lúc nào cũng thắng PNG. Ở ảnh G, method 0 quality 0 bằng @@S/a5/size_vs_png9_pct/G/m0-q0|.0f@@% dung lượng PNG L9 (trung bình theo ảnh) và ở ảnh T bằng @@S/a5/size_vs_png9_pct/T/m0-q0|.0f@@%. Phần lớn mức chênh ở nhóm G đến từ một ảnh: G03 (chỉ có @@IMG/a5/n_colors/G03/m0-q0|.0f@@ màu phân biệt, so với @@IMG/a5/n_colors/G01/m0-q0|.0f@@ màu của G01) nặng @@IMG/a5/size_kb/G03/m0-q0|.0f@@ KB ở method 0 quality 0 nhưng chỉ @@IMG/a5/size_kb/G03/m4-q0|.0f@@ KB ở method 4 và @@IMG/a5/png9_kb/G03/m0-q0|.0f@@ KB với PNG L9 (cột `n_colors`, `png9_kb` trong `a5_raw.csv`); điều này phù hợp với giả thuyết method thấp không thử các biến đổi (bảng màu/dự đoán) phù hợp cho ảnh đồ hoạ ít màu, nhưng tôi chưa kiểm chứng riêng bằng cách bật/tắt từng biến đổi.

**Kết luận chọn tham số.** Với ảnh cần giữ nguyên tuyệt đối (ảnh gốc lưu trữ, logo), dùng WebP lossless **method 4**, quality ở mức trung bình (khoảng 50–100): nhỏ hơn PNG L9 khoảng @@D/a5/size_vs_png9_pct/ALL/m4-q100|.0f@@% trong khi thời gian vẫn chấp nhận được; chỉ dùng method 6, quality 100 cho tài sản tĩnh, mã hoá một lần. Tránh method 0 cho ảnh có nền phẳng/gradient hoặc ít màu.

## 7. A6 – Độ phân giải: 1000 px so với 500 px

**Phương pháp.** Bảy ảnh gốc 1000×1000 (T01–T04, G01–G03) được thu nhỏ còn 500×500 bằng Lanczos (`Image.LANCZOS`), sau đó nén JPEG q75 và WebP q75 (method 4) và so bpp = 8·số byte/(rộng·cao). Ảnh P không có bản 1000 px (nguồn gốc 500 px) nên không tham gia. Để kiểm chứng giả thuyết "ảnh lớn có tương quan không gian cao hơn", tôi đo hệ số tương quan Pearson giữa các cặp điểm ảnh kề ngang (kênh Y) và độ lớn gradient trung bình của chính ảnh trước khi nén.

@@TABLE/c6@@

Hình: `figures/t08/a6_resolution.png` – (a) bpp của JPEG q75, (b) bpp của WebP q75 ở hai độ phân giải cho từng ảnh; (c) tương quan kề ở 500 px so với 1000 px (đường nét đứt là y = x).

**Kết quả và giải thích.** Ảnh 1000 px có bpp thấp hơn ảnh 500 px ở **cả 7 ảnh và cả hai định dạng**: JPEG dùng bpp ở 500 px gấp @@R/a6/bpp/T/JPEG75-500/JPEG75-1000|.2f@@ lần ở 1000 px với nhóm T và @@R/a6/bpp/G/JPEG75-500/JPEG75-1000|.2f@@ lần với nhóm G; WebP tương ứng @@R/a6/bpp/T/WebP75-500/WebP75-1000|.2f@@ và @@R/a6/bpp/G/WebP75-500/WebP75-1000|.2f@@ lần. Hệ quả thực dụng: nhân 4 số điểm ảnh chỉ làm file lớn khoảng @@R/a6/size_kb/T/JPEG75-1000/JPEG75-500|.1f@@ lần với JPEG và @@R/a6/size_kb/T/WebP75-1000/WebP75-500|.1f@@ lần với WebP (nhóm T), chứ không phải 4 lần.

Cơ chế: tương quan giữa các điểm ảnh kề nhau cao hơn ở ảnh độ phân giải lớn (nhóm T: @@S/a6/neighbor_corr/T/JPEG75-1000|.4f@@ ở 1000 px so với @@S/a6/neighbor_corr/T/JPEG75-500|.4f@@ ở 500 px; nhóm G: @@S/a6/neighbor_corr/G/JPEG75-1000|.4f@@ so với @@S/a6/neighbor_corr/G/JPEG75-500|.4f@@), và gradient trung bình thấp hơn (nhóm T: @@S/a6/mean_grad/T/JPEG75-1000|.2f@@ so với @@S/a6/mean_grad/T/JPEG75-500|.2f@@ mức xám/điểm ảnh). Thu nhỏ một nửa nén cùng nội dung vào 1/4 số điểm ảnh: một nét chữ hay một viền rộng 2 px còn 1 px, nên mỗi khối 8×8 của JPEG chứa nhiều biên hơn, nhiều hệ số AC khác 0 hơn và ít chuỗi số 0 hơn, kéo bpp tăng. Cùng lý do khiến chất lượng ở 500 px thấp hơn ở cùng quality: PSNR trung bình @@S/a6/psnr/ALL/JPEG75-500|.2f@@ dB (500 px) so với @@S/a6/psnr/ALL/JPEG75-1000|.2f@@ dB (1000 px) với JPEG, vì cùng một bảng lượng tử hoá được áp lên nội dung nhiều tần số cao hơn. WebP hưởng lợi nhiều hơn từ ảnh lớn (tỉ số bpp @@R/a6/bpp/ALL/WebP75-500/WebP75-1000|.2f@@ so với @@R/a6/bpp/ALL/JPEG75-500/JPEG75-1000|.2f@@ của JPEG, trung bình 7 ảnh), nhiều khả năng vì dự đoán trong khung của VP8 khai thác trực tiếp vùng nhẵn rộng, còn JPEG chỉ dự đoán hệ số DC giữa các khối. Lưu ý WebP và JPEG ở cùng q = 75 không có cùng chất lượng, nên phép so sánh này chỉ là so sánh *tỉ số* giữa hai độ phân giải của từng định dạng, không phải so sánh hiệu suất tuyệt đối của hai định dạng.

**Kết luận.** Với trang web, ảnh sản phẩm 1000×1000 tốn trung bình chỉ khoảng @@R/a6/size_kb/ALL/JPEG75-1000/JPEG75-500|.1f@@ lần (JPEG) và @@R/a6/size_kb/ALL/WebP75-1000/WebP75-500|.1f@@ lần (WebP) dung lượng của bản 500×500: nên cung cấp hai kích thước (thumbnail 500 px cho danh sách, 1000 px cho trang chi tiết, qua `srcset`) và không nên dùng bpp của ảnh 500 px để ước tính dung lượng ảnh lớn (hoặc ngược lại).

## 8. Tổng hợp lựa chọn tham số cho khuyến nghị cuối

| Định dạng | Tham số khuyến nghị | Lý do (từ ablation) |
|---|---|---|
| JPEG | quality 75, lấy mẫu 4:2:0, `optimize=True` (hoặc `progressive=True`) | 4:2:0 tiết kiệm @@D/a1/size_rel_pct/ALL/4:2:0|.0f@@% so với 4:4:4; tối ưu Huffman giảm thêm @@S/a2/size_reduction_pct/ALL/optimize|.0f@@–@@S/a2/size_reduction_pct/ALL/progressive|.0f@@% (trung bình 20 ảnh) mà ảnh giải mã giống hệt; ảnh T có nhãn màu bão hoà: cân nhắc 4:4:4 hoặc 4:2:2 |
| WebP lossy | quality 75, method 4 (tức thời) hoặc 6 (ngoại tuyến) | method 2 và method 0 làm file lớn hơn method 4 lần lượt @@E/a3/size_rel_pct/ALL/m2|.0f@@% và @@E/a3/size_rel_pct/ALL/m0|.0f@@%; method 6 chỉ nhỏ hơn thêm @@D/a3/size_rel_pct/ALL/m6|.1f@@% |
| PNG | `compress_level` 6; L9/`optimize` chỉ cho đồ hoạ phẳng ngoại tuyến | L9 chỉ giảm @@D/a4/size_rel_pct/P/L9|.1f@@% (ảnh P) nhưng chậm gấp @@X/a4/enc_rel_pct/P/L9|.1f@@ lần |
| WebP lossless | method 4, quality 50–100 | nhỏ hơn PNG L9 khoảng @@D/a5/size_vs_png9_pct/ALL/m4-q100|.0f@@%; tránh method 0 cho ảnh nền phẳng |
| Kích thước | cung cấp cả 500 và 1000 px | bpp ở 1000 px thấp hơn ở 500 px (A6) |

**Hạn chế.** (1) Thời gian bị nhiễu như đã nêu ở mục 1; đừng trích số ms tuyệt đối khi chưa đo lại tuần tự. (2) Các ablation đo trên 20 ảnh (7/7/6 theo nhóm); trung bình theo nhóm chịu ảnh hưởng của các ảnh ngoại lệ (đặc biệt G03 ở A4, A5). (3) A1–A5 cố định quality 75 (lossy) nên kết luận về method, lấy mẫu sắc độ có thể thay đổi ở quality khác; chưa dựng đường cong RD đầy đủ. (4) Nhóm T, G là ảnh tổng hợp; A6 thu nhỏ ảnh tổng hợp có nội dung được sinh ở 1000 px, nên chưa chứng minh được xu hướng với ảnh chụp thật. (5) Chưa đo OCR ở các ablation này, nên "chữ còn đọc được" mới chỉ được suy ra từ ΔE/hình, không phải từ OCR.
