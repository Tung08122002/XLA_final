## Phân tích lỗi: 5 trường hợp thất bại của nén ảnh JPEG / PNG / WebP

### 1. Mục tiêu và phương pháp

Phần này tìm và chứng minh bằng số liệu 5 trường hợp nén thất bại (đề bài yêu cầu đúng 5 ca). Năm giả thuyết ban đầu đều được kiểm chứng bằng chỉ số cục bộ (không chỉ PSNR/SSIM toàn ảnh) và một thí nghiệm đối chứng (ablation) để tách nguyên nhân; kết quả ca nào không hoàn toàn ủng hộ giả thuyết thì được nói rõ. Toàn bộ cấu hình đo bằng `common.encode/decode/psnr/ssim/evaluate`; JPEG ghi tường minh `subsampling` (2 = 4:2:0, 0 = 4:4:4); WebP `method=4`; PNG `compress_level=9`; mọi nhiễu ngẫu nhiên dùng seed 2026. Số liệu đầy đủ ở `results/t09/failure_cases.csv` (dạng dài: ca, ảnh, cấu hình, KB, PSNR, SSIM, tên và giá trị chỉ số cục bộ). Số thập phân trong phần này dùng dấu chấm cho khớp với CSV.

### 2. Ca 1 – Ringing (nhiễu muỗi) quanh chữ nhỏ ở JPEG chất lượng thấp

**Hiện tượng.** Trên ba thẻ 500 px (T05–T07), bảng thông số có chữ cao 14 px (nét dày 1–2 px). Sau nén JPEG q50, quanh nét chữ xuất hiện quầng nhiễu (hình `case1.png`). Để định lượng, ta lấy các điểm nền (gốc sáng ≥ 240) nằm cách nét chữ 2–4 px làm “vùng quầng” và đo sai số độ chói |ΔY| ở đó; đồng thời chạy OCR (tesseract 5, tiếng Việt, phóng 3×) để biết chữ còn đọc được không (CER = khoảng cách Levenshtein / số ký tự tham chiếu).

Bảng 1. Ca 1 – trung bình T05–T07.

| Cấu hình | KB | PSNR toàn ảnh (dB) | SSIM toàn ảnh | SSIM vùng chữ | Điểm quầng lệch ≥6 mức (%) | |ΔY| quầng lớn nhất | CER OCR (%) |
|---|---|---|---|---|---|---|---|
| JPEG q10 | 10.6 | 25.2 | 0.876 | 0.914 | 44.8 | 105 | 12.9 |
| JPEG q30 | 17.9 | 28.7 | 0.919 | 0.956 | 41.9 | 73 | 3.0 |
| JPEG q50 | 22.6 | 30.6 | 0.942 | 0.972 | 38.9 | 60 | 1.8 |
| JPEG q50 4:4:4 | 27.7 | 32.1 | 0.950 | 0.972 | 38.9 | 60 | 1.8 |
| JPEG q75 | 31.1 | 33.2 | 0.960 | 0.986 | 30.7 | 33 | 1.0 |
| JPEG q90 | 45.9 | 35.6 | 0.977 | 0.996 | 8.8 | 15 | 1.2 |
| WebP q5 | 7.2 | 28.6 | 0.933 | 0.961 | 37.6 | 77 | 1.5 |
| WebP q30 | 11.5 | 32.2 | 0.957 | 0.978 | 18.7 | 41 | 1.5 |
| WebP q50 | 14.4 | 33.8 | 0.966 | 0.983 | 13.8 | 28 | 1.2 |
| WebP q75 | 17.5 | 34.9 | 0.973 | 0.991 | 7.9 | 18 | 1.2 |

Hình: `figures/t09/case1.png` – (a) crop gốc 100×54 px, (b) JPEG q50, (c) tỉ lệ điểm quầng lệch ≥ 6 mức theo cấu hình, (d–f) bản đồ |ΔY| của JPEG q50, JPEG q90, WebP q75 cùng thang 0–60 (đậm = sai số lớn).

**Số liệu và phát hiện trung thực.** Ở JPEG q50, 38.9% điểm nền quanh chữ lệch ≥ 6 mức xám (tối đa 60 mức), so với 8.8% ở q90 và 7.9% ở WebP q75 (17.5 KB, nhỏ hơn cả JPEG q50 22.6 KB). Tuy nhiên chữ vẫn ĐỌC ĐƯỢC: CER OCR = 1.8% ở q50 và chỉ bắt đầu tăng đáng kể khi q ≤ 15 (7.5% ở q15, 12.9% ở q10, 38.4% ở q5); WebP còn đọc được tới q5 (CER 1.5%) và hỏng ở q0 (14.5%). Vì vậy giả thuyết “q50 làm chữ không đọc được” KHÔNG đúng với OCR; thất bại thực chất là thẩm mỹ/độ sạch (quầng quanh nét chữ: SSIM vùng chữ giảm còn 0.972 so với 0.996 ở q90), chứ chưa phải mất thông tin. Kết luận này giới hạn trong chữ DejaVu Sans 14 px, một công cụ OCR và có phóng 3×; mắt người hoặc OCR khác có thể nhạy hơn (chưa thử).

**Nguyên nhân.** JPEG biến đổi DCT 8×8 độc lập từng khối rồi lượng tử hoá các hệ số tần số cao bằng bảng lượng tử thô. Nét chữ mảnh là tín hiệu băng rộng (cạnh sắc) nên năng lượng rải lên nhiều hệ số AC; khi các hệ số này bị làm tròn về bội của bước lượng tử (bảng chuẩn ở q50 có bước ≈ 10–120 tuỳ tần số), tổng các hàm cơ sở cosin không còn triệt tiêu ở vùng nền kế cạnh, tạo dao động tắt dần (hiện tượng Gibbs) – các “nhiễu muỗi” nằm trong cùng khối 8×8 với nét chữ. Ablation: JPEG q50 4:4:4 cho đúng cùng số liệu quầng (độ chói không phụ thuộc lấy mẫu sắc độ: 38.9% như 4:2:0), xác nhận nguyên nhân nằm ở lượng tử hoá kênh Y chứ không phải ở sắc độ. WebP (dự đoán trong khối + biến đổi 4×4 + bộ lọc vòng giảm khối) có thể giới hạn dao động trong ô 4×4 và làm mịn thêm bằng loop filter nên quầng thấp hơn ở cùng KB (giả thuyết phù hợp với số liệu, không ablation được vì Pillow không mở tham số này).

**Khắc phục.** Với ảnh có chữ nhỏ: dùng JPEG q ≥ 75–90 (q90 giảm quầng còn 9%), hoặc ưu tiên WebP lossy q ≥ 50; tốt nhất giữ chữ ở dạng văn bản HTML/SVG hoặc PNG/WebP lossless cho vùng đồ hoạ; tăng cỡ chữ lên ≥ 20 px ở ảnh 500 px.

### 3. Ca 2 – Loang màu (colour bleeding) quanh nhãn đỏ do lấy mẫu sắc độ 4:2:0

**Hiện tượng.** Nhãn giảm giá “-xx%” (đỏ thuần 255,0,0 với chữ vàng) và giá cam trên thẻ T01–T07 có biên cạnh màu cực sắc. JPEG mặc định (4:2:0) và WebP lossy (luôn 4:2:0) làm viền nhãn bị nhoè sang nền trắng và chữ vàng bị pha đỏ (hình `case2.png`). Chỉ số cục bộ: sai số tuyệt đối trung bình của kênh Cr (YCbCr JFIF) trong khung bao nhãn + 4 px (và khung bao giá).

Bảng 2. Ca 2 – trung bình T01–T07 (Cr đo trên thang 0–255).

| Cấu hình | KB | PSNR toàn ảnh (dB) | SSIM toàn ảnh | Cr MAE nhãn | Cr tối đa nhãn | Y MAE nhãn | Cr MAE giá |
|---|---|---|---|---|---|---|---|
| JPEG q90 4:2:0 | 84.9 | 37.1 | 0.980 | 7.59 | 70 | 3.26 | 5.71 |
| JPEG q90 4:4:4 | 106.7 | 42.7 | 0.989 | 1.41 | 19 | 1.38 | 2.21 |
| JPEG q75 4:2:0 | 57.6 | 34.7 | 0.968 | 9.10 | 76 | 4.32 | 7.02 |
| JPEG q75 4:4:4 | 72.4 | 37.4 | 0.976 | 3.00 | 47 | 2.59 | 4.04 |
| WebP q90 (4:2:0) | 46.5 | 37.8 | 0.985 | 6.30 | 64 | 2.97 | 5.08 |
| WebP q75 (4:2:0) | 29.2 | 36.3 | 0.977 | 6.68 | 66 | 3.57 | 5.58 |
| Chỉ lấy mẫu 4:2:0 (không lượng tử) | – | – | – | 6.76 | 68 | 2.98 | 4.99 |

Hình: `figures/t09/case2.png` – (a) nhãn gốc (T05), (b) JPEG q90 4:2:0, (c) JPEG q90 4:4:4, (d) WebP q90, (e–g) bản đồ |ΔCr| của (b–d) cùng thang 0–40, (h) Cr MAE trung bình T01–T07 kèm cột đối chứng “chỉ lấy mẫu 4:2:0 không lượng tử”.

**Số liệu.** Ở JPEG q90, chuyển 4:4:4 → 4:2:0 làm sai số Cr tại nhãn tăng từ 1.41 lên 7.59 mức (×5.4) và Cr cực đại từ 19 lên 70 mức; PSNR toàn ảnh giảm 5.6 dB nhưng đổi lại tiết kiệm 20% dung lượng (84.9 so với 106.7 KB). WebP q90 (4:2:0, 46.5 KB) có Cr MAE 6.30 – cùng bậc với JPEG 4:2:0, tức WebP KHÔNG tránh được loang màu dù nhỏ hơn. Đối chứng “chỉ lấy mẫu 4:2:0, không lượng tử DCT” đã cho Cr MAE 6.76, tức 89% sai số của JPEG q90 4:2:0 (7.59); phần còn lại ≈ 0.83 mức quy cho lượng tử hoá DCT (JPEG 4:4:4 chỉ có 1.41 từ lượng tử). Vậy phần lớn sai số sắc độ đến từ việc giảm độ phân giải sắc độ chứ không phải từ lượng tử hoá (đối chứng tự cài bằng trung bình 2×2 + nội suy song tuyến, có thể khác bộ giải mã libjpeg đôi chút; chỉ kết luận về bậc độ lớn). Sai số lớn hơn ở ảnh 500 px (Cr MAE nhãn 9–10 mức) so với ảnh 1000 px (≈ 7 mức) có thể vì nhãn nhỏ hơn nên tỉ lệ điểm nằm sát biên cao hơn (chưa kiểm chứng riêng).

**Nguyên nhân.** Mắt nhạy với độ chói hơn sắc độ, nên JPEG/WebP lưu Y đầy đủ nhưng Cb, Cr chỉ ở nửa độ phân giải theo mỗi chiều (mỗi mẫu sắc độ phủ khối 2×2 điểm ảnh). Tại biên đỏ–trắng, giá trị Cr nhảy từ ≈255 xuống ≈128 trong một điểm ảnh; sau khi lấy trung bình 2×2 rồi nội suy lại, một dải rộng 1–2 điểm ảnh quanh biên bị pha trộn (đỏ nhạt lan ra nền, chữ vàng–đỏ trộn). Y vẫn đúng nên cạnh “nhìn” vẫn sắc nhưng màu bị loang – lỗi chỉ lộ ra ở màu bão hoà cao cạnh màu tương phản, hiếm khi thấy ở ảnh chụp tự nhiên.

**Khắc phục.** Với ảnh có nhãn/chữ màu bão hoà: JPEG 4:4:4 (`subsampling=0`, +≈25% KB), hoặc WebP lossless / PNG cho vùng đồ hoạ; hoặc đặt nhãn dưới dạng lớp HTML/CSS thay vì nướng vào ảnh. WebP lossy (qua Pillow) không có tuỳ chọn 4:4:4 nên không khắc phục được ở mức định dạng.

### 4. Ca 3 – Dải màu / khối (banding) trên nền gradient sạch

**Hiện tượng.** Nền studio G01–G03 là gradient mượt. Ở chất lượng thấp, JPEG và WebP biến gradient thành các bậc rộng; đáng chú ý PSNR/SSIM vẫn rất cao nên các chỉ số này KHÔNG báo động. Chỉ số cục bộ: lấy vùng nền thuần (hàng 20–700, cột 20–200), tính độ chói trung bình theo hàng rồi đo (i) bậc nhảy lớn nhất giữa hai hàng liền kề, (ii) số bậc (>0.5 mức), (iii) tỉ lệ tổng biến thiên nằm đúng trên biên khối 8 hàng. Ảnh gốc 8 bit tự nó có bậc 1 mức (không thể mịn hơn); lỗi nghĩa là bậc LỚN HƠN và THƯA HƠN so với gốc.

Bảng 3. Ca 3 – ảnh G01 (gradient dọc, 1000×1000).

| Cấu hình | KB | PSNR (dB) | SSIM | Bậc nhảy lớn nhất (mức) | Số bậc | Bậc nằm ở biên khối 8 hàng (%) |
|---|---|---|---|---|---|---|
| Gốc (PNG) | 98.8 | ∞ | 1.0000 | 1.0 | 39 | 3 |
| JPEG q30 | 20.6 | 40.3 | 0.9865 | 4.0 | 11 | 100 |
| JPEG q50 | 22.9 | 43.2 | 0.9909 | 2.0 | 20 | 100 |
| JPEG q75 | 28.8 | 45.8 | 0.9938 | 1.0 | 81 | 49 |
| JPEG q90 | 41.9 | 49.0 | 0.9958 | 1.0 | 43 | 21 |
| WebP q30 | 5.5 | 42.8 | 0.9919 | 2.0 | 34 | 95 |
| WebP q90 | 13.2 | 49.1 | 0.9957 | 2.0 | 39 | 67 |
| WebP q100 (lossy) | 28.2 | 49.9 | 0.9961 | 2.0 | 62 | 14 |
| WebP lossless | 59.5 | ∞ | 1.0000 | 1.0 | 39 | 3 |
| JPEG q30 + dither σ=1 | 20.6 | 40.4 | 0.9861 | 4.0 | 16 | 100 |
| JPEG q90 + dither σ=1 | 52.8 | 48.2 | 0.9935 | 0.8 | 6 | 19 |

Hình: `figures/t09/case3.png` – (a–c) vùng nền G01 (hàng 100–260) của gốc, JPEG q30 và WebP q30, giãn tương phản về khoảng độ chói của gốc để lộ bậc; (d) profile độ chói trung bình theo hàng, đường xám nhạt là biên khối 8 hàng.

**Số liệu.** JPEG q30 trên G01 chỉ có 11 bậc với bậc nhảy tới 4 mức, trong khi gốc có 39 bậc mỗi bậc 1 mức; 100% biến thiên nằm đúng trên biên khối 8 hàng (gốc chỉ 3%, đúng bằng xác suất ngẫu nhiên ≈ 1/8). Vậy mà PSNR = 40.3 dB và SSIM = 0.987 – thường được coi là chất lượng cao. WebP q30 chỉ 5.5 KB cũng có bậc 2 mức và 95% bậc trên biên khối (PSNR 42.8 dB). Mức 3–4 bậc xám trên một vùng phẳng rộng hàng chục điểm ảnh nằm ở ngưỡng có thể nhìn thấy trên màn hình tốt; tuy nhiên tôi CHƯA làm thí nghiệm thị giác với người xem nên “thấy được” ở đây là suy luận từ độ lớn bậc và hình giãn tương phản, không phải số đo tri giác. Có thể hiểu vì sao hai chỉ số này không báo động: PSNR lấy trung bình bình phương sai số trên 10⁶ điểm ảnh nên sai số ≤ 4 mức cho MSE nhỏ, còn SSIM so cấu trúc trong cửa sổ Gauss σ=1.5 (vài điểm ảnh) nên không “thấy” một bậc phẳng rộng hàng chục điểm ảnh (giải thích suy luận, không đo riêng). Đây là giới hạn của chỉ số, liên quan đến câu hỏi mở “PSNR hay SSIM?”: cả hai đều không đủ cho ảnh nền mượt; cần thêm chỉ số cục bộ như profile/bậc thang ở trên.

Ở G03 (gradient xám sạch), WebP lossless chỉ 6.9 KB, nhỏ hơn JPEG q30 (20.5 KB) mà không có bậc nào thêm. Ở G02 (gradient xuyên tâm) chỉ số theo hàng kém ý nghĩa hơn vì nền thay đổi theo cả hai chiều; số liệu của G02 vẫn có trong CSV.

**Nguyên nhân.** Trong khối 8×8 gradient thuần chỉ có hệ số DC lớn và vài AC thấp tần. DC được lượng tử bằng một bước Q (ở q30 Q_DC ≈ 27, tương đương bước ≈ 27/8 ≈ 3.3 mức độ chói trung bình khối); mỗi khối nhận một mức DC làm tròn nên toàn khối phẳng, và biên giữa hai khối kề là bậc nhảy bằng bội của bước. Hệ số AC nhỏ (biểu diễn độ dốc nội khối) bị làm tròn về 0 nên không khôi phục được độ dốc. Kết quả là bậc thang đúng tại biên khối 8×8, khớp tỉ lệ 100%. WebP dự đoán DC theo khối lân cận (intra 16×16 hoặc 4×4) và lượng tử phần dư; vùng phẳng được dự đoán hoàn hảo và phần dư làm tròn về 0 nên cũng tạo bậc rộng (không có tuỳ chọn tắt trong Pillow nên không ablation được loop filter ở đây).

**Đối chứng và khắc phục.** (i) Tăng chất lượng: JPEG q75 (28.8 KB) đã đưa bậc nhảy lớn nhất về 1 mức như gốc, đổi lại +40% KB so với q30. WebP lossy KHÔNG đạt được điều đó: bậc vẫn 2 mức ngay cả ở q100 (28.2 KB), chỉ WebP lossless khôi phục đúng. (ii) Dithering nguồn (nhiễu Gauss σ=1 thêm trước khi nén) KHÔNG giúp ở chất lượng thấp: q30 vẫn bậc 4 mức vì lượng tử hoá xoá nhiễu tần cao; chỉ ở q90 nó làm bậc giảm còn 0.82 mức nhưng tốn 52.8 KB (so 41.9 KB khi không dither). Giả thuyết “thêm nhiễu nhẹ chống banding” do đó chỉ đúng với chất lượng cao hoặc khi dither được áp dụng sau giải mã phía trình duyệt (không thử). (iii) Với ảnh nền gradient đơn giản, chọn WebP lossless (G03) hoặc JPEG ≥ q75.

### 5. Ca 4 – Mất kết cấu chi tiết (lông baboon)

**Hiện tượng.** P06 (mặt khỉ baboon: lông, râu tần số cao dày đặc) là ảnh khó nhất của bộ dữ liệu: ở cả JPEG q50 và WebP q75 nó có SSIM THẤP NHẤT trong 20 ảnh (hạng 1 và 1 từ dưới lên). Giả thuyết ban đầu là WebP làm mịn kết cấu nhiều hơn JPEG ở cùng dung lượng; ta kiểm chứng bằng cách chọn quality WebP sao cho KB gần nhất với từng mức JPEG, đo SSIM cục bộ, và năng lượng + tương quan của dải tần 1–3 px (hiệu hai bộ lọc Gauss σ=1 và σ=3, trên độ chói) so với gốc.

Bảng 4. Ca 4 – JPEG so với WebP cùng dung lượng.

| Ảnh | Cấu hình | KB | PSNR (dB) | SSIM | SSIM vùng lông+râu | Năng lượng dải 1–3 px (nén/gốc) | Tương quan dải 1–3 px |
|---|---|---|---|---|---|---|---|
| P06 | JPEG q10 | 15.8 | 22.34 | 0.631 | 0.646 | 1.012 | 0.928 |
| P06 | WebP q5 (≈KB JPEG q10) | 15.7 | 23.45 | 0.663 | 0.650 | 0.904 | 0.916 |
| P06 | JPEG q20 | 25.8 | 24.04 | 0.730 | 0.754 | 1.005 | 0.974 |
| P06 | WebP q17 (≈KB JPEG q20) | 26.1 | 25.08 | 0.769 | 0.780 | 0.965 | 0.962 |
| P06 | JPEG q50 | 47.5 | 26.28 | 0.825 | 0.855 | 1.002 | 0.994 |
| P06 | WebP q44 (≈KB JPEG q50) | 47.8 | 27.60 | 0.862 | 0.889 | 0.989 | 0.988 |
| P06 | JPEG q75 | 71.5 | 28.10 | 0.875 | 0.907 | 1.001 | 0.998 |
| P06 | WebP q76 (≈KB JPEG q75) | 72.5 | 29.64 | 0.913 | 0.933 | 0.993 | 0.996 |
| P02 | JPEG q10 | 8.9 | 29.31 | 0.781 | – | 1.005 | 0.867 |
| P02 | WebP q21 (≈KB JPEG q10) | 8.9 | 32.67 | 0.863 | – | 0.854 | 0.913 |

Bảng 5. Dung lượng nhỏ nhất (quét quality nguyên) để đạt SSIM ≥ 0.95.

| Ảnh | JPEG (KB, q) | WebP (KB, q) |
|---|---|---|
| P04 rocket | 19.1 (JPEG q77) | 8.9 (WebP q65) |
| P02 chelsea | 27.1 (JPEG q61) | 23.7 (WebP q79) |
| P06 baboon | 190.3 (JPEG q96) | 121.9 (WebP q90) |

Hình: `figures/t09/case4.png` – (a) vùng lông+râu 96×96 px của P06, (b) JPEG q50, (c) WebP cùng dung lượng, (d–e) bản đồ SSIM cục bộ tương ứng (tối = mất cấu trúc), (f) năng lượng dải 1–3 px theo dung lượng cho P06 và P02.

**Phát hiện (giả thuyết được ủng hộ một phần).** (1) Mất kết cấu là có thật và nặng: để đạt SSIM 0.95, P06 cần 190 KB (JPEG) / 122 KB (WebP), gấp 10× / 14× so với P04 rocket (19 / 9 KB). Ở JPEG q50 (47.5 KB) SSIM toàn ảnh chỉ 0.825, vùng lông+râu 0.855; bản đồ SSIM cho thấy mất cấu trúc tập trung ở vùng lông dày xen kẽ. (2) WebP có làm mịn: ở dung lượng thấp năng lượng dải 1–3 px còn 0.90 lần gốc ở P06 (15.7 KB) và 0.85 ở P02 (8.9 KB), trong khi JPEG giữ ≈ 1.00 – phần năng lượng “đủ” này có thể một phần là nhiễu khối/ringing chứ không hoàn toàn là kết cấu thật (chưa tách). (3) Tuy nhiên GIẢ THUYẾT “WebP kém hơn JPEG ở kết cấu” không đứng vững theo chỉ số: cùng ≈47.5 KB, WebP q44 có PSNR 27.60 dB, SSIM 0.862 so với JPEG q50 26.28 dB, 0.825; ở mọi cặp P06 trong Bảng 4 WebP đều cao hơn về PSNR và SSIM. Riêng tương quan dải 1–3 px ở P06 thì JPEG nhỉnh hơn (0.994 so với 0.988 ở ≈47.5 KB) còn ở P02 mức thấp WebP lại cao hơn (0.913 so với 0.867 của JPEG q10) – nghĩa là kết quả hỗn hợp, không có kết luận một chiều. Làm mịn của WebP là sự đánh đổi mà PSNR/SSIM thưởng chứ không phạt, nên đây vừa là điểm yếu về cảm nhận (mất tinh thể lông ở dung lượng thấp) vừa là giới hạn của chỉ số.

**Nguyên nhân.** Kết cấu lông là tín hiệu ngẫu nhiên băng rộng, entropy cao (phần dư MED ≈ 6.2 bit/mẫu, cao nhất bộ dữ liệu, xem ca 5): hệ số DCT tần cao có biên độ lớn và không thưa, nên bảng lượng tử thô buộc phải bỏ chúng (JPEG) hoặc bỏ/làm mịn chúng để tiết kiệm bit (WebP: lượng tử 4×4, tối ưu tốc độ–méo của libwebp ưu tiên làm tròn về 0 và bộ lọc vòng giảm khối làm mịn thêm). Tôi không tách riêng được vai trò loop filter của WebP vì Pillow không mở tham số này và máy không có `cwebp`; nên phần quy cho loop filter là giả thuyết phù hợp với chiều mịn hơn quan sát được, chưa được ablation.

**Khắc phục.** Với ảnh nhiều kết cấu (lông, vải): đừng nén xuống dưới JPEG q75 / WebP q76 (P06: SSIM ≈ 0.88 / 0.91 ở ≈72 KB); chấp nhận dung lượng lớn hơn hẳn các ảnh khác hoặc giảm độ phân giải xuất ảnh thay vì tăng lượng tử; kiểm tra bằng bản đồ SSIM cục bộ thay vì chỉ SSIM toàn ảnh.

### 6. Ca 5 – Thất bại về dung lượng: nén không mất mát trên ảnh có nhiễu

**Hiện tượng.** PNG và WebP lossless hoạt động rất tốt trên đồ hoạ phẳng (thẻ T) nhưng gần như vô hiệu trên ảnh chụp và ảnh có nhiễu cảm biến: dung lượng gấp nhiều lần JPEG q90, tỉ lệ nén chỉ ≈ 1.3–3.6× (hình `case5.png`).

Bảng 6. Ca 5 – bit trên điểm ảnh (bpp) và tỉ số dung lượng so với JPEG q90.

| Ảnh | PNG (KB / bpp) | WebP lossless (KB / bpp) | JPEG q90 (KB / bpp) | PNG ÷ JPEG q90 | Tỉ lệ nén PNG | Entropy phần dư MED (bit/mẫu) |
|---|---|---|---|---|---|---|
| G01_studio1000 | 99 / 0.81 | 59 / 0.49 | 42 / 0.34 | 2.4× | 29.65 | 0.43 |
| G04_studio500_noise | 306 / 10.04 | 262 / 8.60 | 23 / 0.75 | 13.4× | 2.39 | 3.18 |
| G05_studio500_noise | 298 / 9.77 | 259 / 8.48 | 21 / 0.67 | 14.5× | 2.46 | 3.08 |
| G06_studio500_noise | 298 / 9.76 | 259 / 8.49 | 20 / 0.65 | 15.1× | 2.46 | 3.07 |
| P06_baboon | 571 / 18.71 | 470 / 15.41 | 122 / 3.98 | 4.7× | 1.28 | 6.21 |
| P04_rocket | 206 / 6.74 | 175 / 5.74 | 33 / 1.08 | 6.2× | 3.56 | 2.53 |
| T05_card500 | 105 / 3.44 | 72 / 2.35 | 52 / 1.69 | 2.0× | 6.98 | 1.79 |
| T01_card1000 | 306 / 2.51 | 217 / 1.78 | 123 / 1.01 | 2.5× | 9.56 | 1.36 |

Bảng 7. Quét σ nhiễu Gauss thêm vào chính G01 (cùng cảnh; bpp).

| σ | PNG | WebP lossless | JPEG q90 | Cận dưới 3·h(N) |
|---|---|---|---|---|
| 0 | 0.81 | 0.49 | 0.34 | – |
| 0.5 | 6.50 | 5.27 | 0.35 | 3.14 |
| 1 | 8.96 | 7.32 | 0.43 | 6.14 |
| 1.5 | 10.17 | 8.80 | 0.57 | 7.90 |
| 2 | 11.08 | 9.99 | 0.70 | 9.14 |
| 3 | 12.70 | 11.60 | 0.94 | 10.90 |

Hình: `figures/t09/case5.png` – (a) crop G01 sạch, (b) crop G04 nhiễu (cùng tăng tương phản), (c) bpp của PNG/WebP lossless/JPEG q90 (thang log) cho G01, G04, P06, (d) bpp theo σ trên G01 cùng đường cận dưới entropy của nhiễu.

**Số liệu.** G01 (sạch) cần 0.81 bpp với PNG, G04 (nhiễu σ=1.5) cần 10.04 bpp: gấp 12.4× (tỉ lệ nén PNG từ 29.6× xuống 2.39×), và PNG lớn gấp 13.4× JPEG q90 (0.75 bpp); WebP lossless 8.60 bpp vẫn gấp 11.4× JPEG q90. Trong thí nghiệm sạch/nhiễu trên cùng một cảnh (Bảng 7), chỉ cần σ = 0.5 (±1 mức xám) đã đẩy PNG từ 0.81 lên 6.50 bpp (×8.0); JPEG q90 gần như không đổi (0.34 → 0.35 bpp). Giải thích định lượng bằng entropy: nhiễu thật của G04 (G04 trừ bản sạch tái tạo) có σ hiệu dụng 1.47 và entropy biên 2.60 bit/mẫu, nên cận dưới ≈ 3 × 2.60 = 7.80 bpp nếu nhiễu độc lập giữa các kênh và điểm ảnh; WebP lossless (8.60 bpp) chỉ cao hơn cận này 10% và PNG (10.04 bpp) cao hơn 29% – nghĩa là hai bộ nén đã gần chạm giới hạn lý thuyết, không có lỗi cài đặt nào để sửa. (Bản sạch tái tạo của G04 chỉ 2.00 bpp với PNG, nên nhiễu chiếm phần lớn dung lượng.) Cùng chiều, ảnh P có entropy phần dư MED cao (P06: 6.2 bit/mẫu) cho PNG tới 18.7 bpp.

**Nguyên nhân.** PNG dự đoán từng điểm ảnh bằng bộ lọc (Sub/Up/Average/Paeth) rồi nén phần dư bằng DEFLATE (LZ77 + Huffman); WebP lossless dùng dự đoán không gian, biến đổi màu, bộ nhớ màu và mã hoá entropy. Trên gradient mượt phần dư gần 0 và rất lặp, LZ77 tìm được các chuỗi trùng khớp dài. Nhiễu ngẫu nhiên làm phần dư có phân bố rộng, độc lập và không lặp: không còn chuỗi trùng khớp cho LZ77, và entropy mỗi mẫu bị chặn dưới bởi h(N) = ½·log₂(2πeσ²) bit; không thuật toán lossless nào vượt được. JPEG q90 không ràng buộc này vì nó vứt bỏ phần nhiễu (hệ số tần cao nhỏ làm tròn về 0) – đổi lấy PSNR hữu hạn.

**Khắc phục.** Với ảnh chụp có nhiễu: dùng lossy (JPEG q75–90 hoặc WebP q75–90); nếu bắt buộc lossless thì khử nhiễu trước (bỏ nhiễu cảm biến mất mát nhưng không nhìn thấy) hoặc chấp nhận file lớn. Giữ lossless cho đồ hoạ phẳng (thẻ T: tỉ lệ nén PNG 7–15×, WebP lossless nhỏ hơn PNG khoảng 25–36%) và ảnh gradient sạch.

### 7. Bảng tóm tắt 5 ca thất bại

| Ca | Ảnh – cấu hình | Hiện tượng đo được | Nguyên nhân (thuật toán) | Khắc phục |
|---|---|---|---|---|
| C1 Ringing quanh chữ nhỏ | T05–T07, JPEG q50 | 39% điểm nền quanh chữ lệch ≥6 mức (q90: 9%); OCR vẫn đọc được (CER 1.8%), hỏng khi q≤10 | Lượng tử DCT 8×8 các hệ số cao tần của cạnh sắc → dao động Gibbs trong khối | JPEG ≥q75–90 hoặc WebP ≥q50; chữ để dạng văn bản/lossless |
| C2 Loang màu | T01–T07, JPEG q90 4:2:0 và WebP q90 | Cr MAE tại nhãn 7.6 (4:4:4: 1.4); WebP 6.3; chỉ riêng lấy mẫu 4:2:0 đã 6.8 | Lấy mẫu sắc độ 4:2:0 trộn màu bão hoà ở biên (WebP lossy luôn 4:2:0) | JPEG 4:4:4 (+26% KB) hoặc lossless cho đồ hoạ |
| C3 Banding | G01, JPEG q30 / WebP q30 | Bậc 4 mức, 11 bậc (gốc 1 mức, 39 bậc), 100% ở biên khối; PSNR 40.3 dB, SSIM 0.987 | Làm tròn DC theo khối + AC thấp tần về 0 (JPEG), dự đoán DC + loop filter (WebP) | JPEG ≥q75 hoặc WebP lossless; dither nguồn chỉ giúp ở q90 (+26% KB) |
| C4 Mất kết cấu | P06 baboon, JPEG q50 / WebP | SSIM thấp nhất bộ dữ liệu (0.825); cần 190 KB (JPEG) / 122 KB (WebP) để SSIM≥0.95, gấp 10× / 14× rocket; WebP mịn hơn (năng lượng dải 0.90) nhưng PSNR/SSIM vẫn cao hơn JPEG | Kết cấu entropy cao, hệ số cao tần lớn bị lượng tử bỏ; WebP thêm làm mịn (giả thuyết loop filter) | Không nén dưới q75; giảm độ phân giải thay vì tăng lượng tử |
| C5 Dung lượng lossless | G04 nhiễu σ=1.5 và P06 | PNG 10.04 bpp (×13.4 JPEG q90), tỉ lệ nén 2.39×; chỉ σ=0.5 đã nhân PNG ×8.0; WebP LL cách cận entropy 10% | Nhiễu độc lập làm vô hiệu dự đoán + LZ77; entropy h(N) là cận dưới | Dùng lossy cho ảnh chụp; lossless chỉ cho đồ hoạ/gradient sạch |

### 8. Hạn chế

(1) Ảnh T và G là ảnh tổng hợp (chữ DejaVu Sans, nền gradient lý tưởng) nên mức độ lỗi có thể khác trên ảnh sản phẩm thật. (2) OCR chỉ dùng một công cụ (tesseract) với phóng 3×; chưa có thí nghiệm người xem, nên ngưỡng “thấy banding/ringing” là suy luận từ độ lớn sai số. (3) Pillow không cho tắt loop filter, đổi sns, hay chọn 4:4:4 cho WebP lossy; nên cơ chế WebP (ca 3, ca 4) chưa được ablation trực tiếp. (4) Cận dưới entropy giả sử nhiễu độc lập từng kênh/điểm ảnh; nhiễu G04 có thể hơi tương quan không gian do bước làm mờ khi tạo dữ liệu nên cận thật có thể thấp hơn chút. (5) Re-encode lại ảnh nguồn JPEG (P06/P07) không được xét vì các ảnh này đã được thu nhỏ trước khi lưu PNG, khối 8×8 gốc không còn thẳng hàng.
