# Phương pháp chính WebP và bảng so sánh baseline – WebP trên cùng tập test (t04)

## 1. Mục tiêu
Phần này đặt phương pháp chính của đề tài (WebP có mất mát và không mất mát) cạnh hai baseline (JPEG q50/75/90 và PNG) trên **cùng 20 ảnh** (P: 7 ảnh chụp nhiều chi tiết; T: 7 thẻ sản phẩm có chữ; G: 6 ảnh nền gradient, trong đó G04–G06 có nhiễu Gauss σ = 1,5). Mục tiêu: (i) lập bảng trung tâm dung lượng/bpp/PSNR/SSIM theo nhóm; (ii) so sánh cặp WebP qX với JPEG qX và WebP lossless với PNG; (iii) giải thích cơ chế của chênh lệch quan sát được.

## 2. Phương pháp và tham số
Toàn bộ nén/giải nén chạy trong bộ nhớ bằng Pillow qua `common.evaluate(..., repeats=0)` (không đo thời gian). Tám cấu hình:

- **JPEG q50/75/90**: mặc định của Pillow (libjpeg-turbo, bảng lượng tử chuẩn co giãn theo q, Huffman tĩnh, không progressive). Giữ mặc định vì đề bài định nghĩa baseline theo cách này. Đã kiểm tra: lấy mẫu con màu mặc định là 4:2:0.
- **PNG compress_level = 9**: mức DEFLATE tốt nhất, để WebP lossless không được so với một PNG "nén lơi".
- **WebP lossy q50/75/90, method = 4**: mặc định Pillow/libwebp (VP8 intra, luôn 4:2:0). method 0–6 đổi thời gian lấy dung lượng; 4 là điểm cân bằng mặc định.
- **WebP lossless** (`lossless=True, quality=100, method=4`): với VP8L, `quality` là mức nỗ lực nén, không phải độ trung thực.

PNG và WebP lossless đều được kiểm tra bằng `assert` là khôi phục chính xác từng điểm ảnh (PSNR = ∞, SSIM = 1). PSNR trung bình của hai cấu hình này vì vậy ghi là ∞.

**Lưu ý phương pháp (quan trọng).** Thang `quality` của JPEG và của WebP **không tương đương**: hai bộ mã dùng lượng tử hoá khác nhau nên "q75" của hai định dạng không cho cùng chất lượng hay cùng dung lượng. So sánh cùng số quality ở mục 4 chỉ mang tính tham khảo. So sánh công bằng cần đường tốc độ–méo (RD) / iso-quality (xem task t05, t06).

## 3. Bảng so sánh tổng (trung bình trên các ảnh của từng nhóm)
| Cấu hình | P KB | P bpp | P PSNR | P SSIM | T KB | T bpp | T PSNR | T SSIM | G KB | G bpp | G PSNR | G SSIM |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| JPEG q50 | 27.4 | 0.90 | 32.01 | 0.9038 | 45.4 | 0.62 | 32.10 | 0.9520 | 15.4 | 0.23 | 42.19 | 0.9733 |
| JPEG q75 | 40.5 | 1.33 | 33.92 | 0.9314 | 61.2 | 0.85 | 34.45 | 0.9658 | 19.1 | 0.29 | 44.34 | 0.9775 |
| JPEG q90 | 68.6 | 2.25 | 36.49 | 0.9572 | 90.7 | 1.25 | 36.89 | 0.9791 | 30.8 | 0.51 | 46.58 | 0.9799 |
| PNG | 388.2 | 12.72 | ∞ | 1.0000 | 191.8 | 2.48 | ∞ | 1.0000 | 185.0 | 5.21 | ∞ | 1.0000 |
| WebP q50 | 21.5 | 0.70 | 32.61 | 0.9103 | 25.1 | 0.36 | 34.97 | 0.9695 | 3.5 | 0.06 | 42.79 | 0.9756 |
| WebP q75 | 29.2 | 0.96 | 34.08 | 0.9321 | 30.5 | 0.44 | 36.11 | 0.9761 | 4.2 | 0.07 | 44.15 | 0.9771 |
| WebP q90 | 57.1 | 1.87 | 37.22 | 0.9634 | 48.5 | 0.69 | 37.68 | 0.9842 | 7.8 | 0.14 | 46.11 | 0.9794 |
| WebP lossless | 304.9 | 9.99 | ∞ | 1.0000 | 133.9 | 1.72 | ∞ | 1.0000 | 150.5 | 4.43 | ∞ | 1.0000 |

Hình: `figures/t04/size_bar_all_configs.png` – dung lượng trung bình của 8 cấu hình theo 3 nhóm (thang log).
Hình: `figures/t04/size_vs_ssim_scatter.png` – mỗi điểm là một cặp (ảnh, cấu hình); trục x là bpp (log), trục y là SSIM; ký hiệu theo codec, màu theo nhóm.

Số liệu gốc: `results/t04/all_configs_per_image.csv` (từng ảnh), `results/t04/comparison_by_group.csv` (trung bình, kèm độ lệch chuẩn dung lượng và SSIM nhỏ nhất).

## 4. So sánh cặp cùng số quality (chỉ để tham khảo)
Tỉ lệ dung lượng tính trên từng ảnh rồi lấy trung bình/trung vị; "thắng tuyệt đối" là WebP vừa nhỏ hơn vừa có SSIM cao hơn JPEG trên cùng ảnh.

| Cặp so sánh | Nhóm | WebP/JPEG (dung lượng, TB) | Trung vị | ΔPSNR (dB) | ΔSSIM | WebP nhỏ hơn | WebP SSIM cao hơn | Thắng tuyệt đối |
|---|---|---|---|---|---|---|---|---|
| WebP q50 vs JPEG q50 | P | 0.731 | 0.684 | +0.60 | +0.0065 | 6/7 | 5/7 | 4/7 |
| WebP q50 vs JPEG q50 | T | 0.572 | 0.544 | +2.88 | +0.0175 | 7/7 | 7/7 | 7/7 |
| WebP q50 vs JPEG q50 | G | 0.242 | 0.221 | +0.60 | +0.0023 | 6/6 | 5/6 | 5/6 |
| WebP q50 vs JPEG q50 | ALL | 0.529 | 0.565 | +1.40 | +0.0091 | 19/20 | 17/20 | 16/20 |
| WebP q75 vs JPEG q75 | P | 0.675 | 0.640 | +0.16 | +0.0007 | 7/7 | 4/7 | 4/7 |
| WebP q75 vs JPEG q75 | T | 0.513 | 0.496 | +1.66 | +0.0104 | 7/7 | 7/7 | 7/7 |
| WebP q75 vs JPEG q75 | G | 0.233 | 0.209 | -0.19 | -0.0004 | 6/6 | 3/6 | 3/6 |
| WebP q75 vs JPEG q75 | ALL | 0.486 | 0.507 | +0.58 | +0.0038 | 20/20 | 14/20 | 14/20 |
| WebP q90 vs JPEG q90 | P | 0.795 | 0.755 | +0.74 | +0.0063 | 6/7 | 6/7 | 5/7 |
| WebP q90 vs JPEG q90 | T | 0.542 | 0.535 | +0.79 | +0.0051 | 7/7 | 7/7 | 7/7 |
| WebP q90 vs JPEG q90 | G | 0.255 | 0.241 | -0.48 | -0.0005 | 6/6 | 1/6 | 1/6 |
| WebP q90 vs JPEG q90 | ALL | 0.544 | 0.538 | +0.39 | +0.0038 | 19/20 | 14/20 | 13/20 |

Hình: `figures/t04/visual_compare.png` – cùng một vùng cắt 160×120 điểm ảnh của T01 và G01: gốc, JPEG q75, WebP q75 (dung lượng, SSIM, PSNR tính trên toàn ảnh; hàng G chỉ tăng tương phản ×6 để hiển thị).

## 5. WebP lossless so với PNG
| Nhóm | Giảm TB (%) | Nhỏ nhất – lớn nhất (%) | Giảm theo tổng byte (%) | WebP-LL nhỏ hơn PNG |
|---|---|---|---|---|
| P | 21.4 | 14.8 – 30.9 | 21.5 | 7/7 |
| T | 30.6 | 26.6 – 35.6 | 30.2 | 7/7 |
| G | 29.1 | 13.0 – 54.7 | 18.6 | 6/6 |
| ALL | 26.9 | 13.0 – 54.7 | 23.1 | 20/20 |

Hình: `figures/t04/lossless_png_vs_webp.png` – trái: dung lượng trung bình PNG và WebP lossless theo nhóm; phải: % giảm dung lượng của từng ảnh.

Số liệu: `results/t04/pairwise.csv` (tổng hợp theo nhóm), `results/t04/pairwise_per_image.csv` (từng ảnh).

## 6. Nhận xét và giải thích cơ chế
**Kết quả chính.** Ở cùng số quality, WebP lossy nhỏ hơn JPEG trên 19–20/20 ảnh, với dung lượng bằng 0,49–0,54 lần JPEG (trung bình các ảnh). Chênh lệch lớn nhất ở nhóm G (0,23–0,26 lần) và nhóm T (0,51–0,57 lần), nhỏ nhất ở nhóm P (0,68–0,80 lần). Chất lượng không thua rõ rệt: trên 20 ảnh, WebP có SSIM cao hơn ở 17/20 (q50), 14/20 (q75), 14/20 (q90). Ở nhóm T, WebP thắng tuyệt đối 7/7 ảnh ở cả ba mức, với ΔPSNR từ +0,79 đến +2,88 dB. Ở nhóm G, WebP chủ yếu thắng về dung lượng: ΔSSIM chỉ −0,0005 đến +0,0023, và ΔPSNR âm ở q75 (−0,19 dB) và q90 (−0,48 dB). Chênh lệch chất lượng giữa hai codec trên G rất nhỏ so với chênh lệch dung lượng.

**Bảng cũng cho thấy sai lệch của phép so sánh cùng số quality.** Trên nhóm T, WebP q90 (48,5 KB, SSIM 0,9842) vượt JPEG q90 (90,7 KB, SSIM 0,9791) trong khi nhỏ hơn khoảng một nửa; trên nhóm G, WebP q75 (4,2 KB, SSIM 0,9771) gần bằng JPEG q75 (19,1 KB, SSIM 0,9775). Hai ví dụ chỉ minh hoạ rằng tỉ lệ dung lượng phụ thuộc vào cách ghép mức q; mức tiết kiệm "thật" phải đọc từ đường RD.

**Vì sao WebP lossy nhỏ hơn, nhất là ở vùng phẳng và gradient.** (a) *Dự đoán trong ảnh (intra) của VP8*: mỗi khối được dự đoán từ các điểm ảnh đã tái tạo ở lân cận (các chế độ DC/ngang/dọc/TrueMotion cho khối 16×16, tới 10 chế độ cho khối con 4×4), và chỉ phần dư được biến đổi và lượng tử. Với nền phẳng hoặc gradient trơn, phần dư gần bằng 0 nên khối được mã gần như miễn phí (nhóm G chỉ dùng 0,06–0,14 bpp). JPEG chỉ dự đoán hệ số DC giữa các khối (DPCM) và mã mọi hệ số AC độc lập. (b) *Mã hoá entropy*: VP8 dùng bộ mã số học nhị phân với xác suất thích nghi theo ngữ cảnh, còn JPEG mặc định của Pillow dùng bảng Huffman tĩnh (không optimize). (c) *Bộ lọc vòng (loop filter)*: VP8 khử hiệu ứng khối ngay trong vòng tái tạo, nên ở mức q thấp biên khối ít lộ hơn và ảnh tham chiếu cho dự đoán sạch hơn; điều này giúp vùng gradient, nơi mắt người dễ thấy vệt khối và banding. (d) *Khối biến đổi 4×4*: cạnh chữ chỉ làm "tràn" nhiễu (ringing) trong phạm vi 4 điểm ảnh thay vì 8, và nền trắng quanh chữ rẻ do được dự đoán tốt. Đây là điểm nhiều khả năng giải thích ưu thế trên nhóm T (7/7 thắng tuyệt đối). Lưu ý các cơ chế (a)–(d) là giải thích phù hợp với kết quả, chưa được cô lập bằng ablation trong phần này.

**Lấy mẫu con màu 4:2:0 và chữ màu.** WebP lossy luôn dùng 4:2:0 (VP8 profile 0, không có tuỳ chọn 4:4:4). Với chữ/nhãn màu đỏ–vàng nét mảnh, chroma ở nửa độ phân giải làm màu "tràn" sang viền (có dấu hiệu nhẹ ở viền nhãn −35% trong hình so sánh; ở độ phóng đại này khác biệt giữa JPEG q75 và WebP q75 khó thấy bằng mắt). Tuy nhiên, **trong baseline này JPEG cũng ở 4:2:0** (Pillow mặc định; đã kiểm tra `get_sampling` = 2), nên 4:2:0 không giải thích được chênh lệch giữa WebP và JPEG mà là giới hạn chung. Để định lượng, một chẩn đoán phụ (xấp xỉ: giảm Cb/Cr bằng BOX rồi phóng lại bằng BILINEAR, không lượng tử DCT) cho PSNR chỉ do 4:2:0 là 38,16 dB (T), 39,39 dB (P), 44,79 dB (G); xem `results/t04/chroma420_ceiling_by_group.csv`. Với nhóm T, WebP q90 đã đạt 37,68 dB, sát trần này, nên tăng q thêm gần như không cải thiện PSNR. Khả năng JPEG 4:4:4 vượt WebP lossy trên chữ màu ở bitrate cao chưa được kiểm tra ở task này (thuộc phần ablation).

**WebP lossless so với PNG.** WebP lossless nhỏ hơn PNG trên 20/20 ảnh, trung bình giảm 26,9% (giảm 23,1% nếu tính theo tổng byte). Theo nhóm: P 21,4%, T 30,6%, G 29,1%. Giá trị G che giấu hai chế độ khác nhau: ảnh sạch G01–G03 giảm 39,3–54,7%, ảnh có nhiễu G04–G06 chỉ giảm 13,0–14,3%. Cơ chế: VP8L dùng các phép biến đổi thuận nghịch trước khi mã hoá, gồm dự đoán không gian theo khối với 14 chế độ, biến đổi tương quan màu và **subtract green** (trừ kênh G khỏi R và B để khử tương quan màu), và bảng màu khi ảnh ít màu; sau đó dùng LZ77 kèm **color cache** (nhớ các màu vừa dùng, mã bằng chỉ số ngắn) và nhiều bảng Huffman theo vùng. PNG chỉ có bộ lọc theo từng dòng (5 kiểu, dùng lân cận trái/trên/Paeth) rồi DEFLATE (LZ77 cửa sổ 32 KB + Huffman). Gradient trơn được dự đoán 2D rất tốt (phần dư gần 0), nên ảnh sạch lợi nhiều. Nhiễu cảm biến thì không dự đoán được: phần entropy do nhiễu gần như không nén được bởi bất kỳ bộ mã không mất mát nào, nên mức giảm co lại còn 13–14%.

**Về PSNR và SSIM.** Hai thước đo đồng hướng ở 57/60 phép so sánh (ảnh × cặp q); chỉ 3 trường hợp ngược dấu, đều với chênh lệch rất nhỏ (|ΔSSIM| ≤ 0,0028), nên kết luận về "thắng tuyệt đối" không phụ thuộc nhạy vào việc chọn thước đo. Thảo luận đầy đủ về chọn PSNR hay SSIM nằm ở phần khác của báo cáo.

## 7. Hạn chế và ngoại lệ trung thực
- WebP **không** luôn nhỏ hơn JPEG: ảnh P06 (baboon, nhiều kết cấu lông) có WebP lớn hơn JPEG ở q50 (tỉ lệ 1,07) và q90 (1,003); nhưng ở cả ba mức SSIM của WebP cao hơn (+0,047 ở q50). Tức ở ảnh này WebP "đổi" chút dung lượng lấy chất lượng, và phép so sánh cùng q lại một lần nữa cho thấy hai thang q khác nhau.
- Có 17 trong 60 phép so sánh (ảnh × mức q) WebP không thắng tuyệt đối; tập trung ở G (nơi SSIM bão hoà gần 1 nên chênh lệch rất nhỏ) và P (P01, P02, P07).
- Chỉ 20 ảnh, nhóm T và G là ảnh tổng hợp; hai ảnh P có nguồn là JPEG (P06, P07, đã thu nhỏ) có thể mang vết nén sẵn. Trung bình theo nhóm chỉ dựa trên 6–7 ảnh, không có khoảng tin cậy; kết luận định lượng nên đọc cùng bảng từng ảnh.
- Mỗi cấu hình chỉ một lần chạy với tham số mặc định (WebP method = 4, JPEG không optimize/progressive, không dùng sharp-YUV hay `exact`). Không đo thời gian ở task này. PSNR và SSIM đo trên RGB theo `common.py`, không phải trên độ chói; không phải thước đo nhận thức hoàn hảo, và khả năng đọc chữ (OCR) chưa được kiểm tra ở đây.
