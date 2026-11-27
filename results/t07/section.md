## Ảnh có chữ: nén ở mức nào thì vẫn đọc được? (đo bằng OCR)

### 1. Mục tiêu
Trả lời câu hỏi mở của đề bài bằng một thước đo khách quan, tái lập được thay cho nhận xét bằng mắt: với 7 thẻ sản phẩm có chữ tiếng Việt (nhóm T: 4 ảnh 1000 px, chữ thông số cao 26 px; 3 ảnh 500 px, chữ thông số cao 14 px), mức *quality* tối thiểu của JPEG (4:2:0 và 4:4:4) và WebP lossy là bao nhiêu để chữ còn đọc được, và dung lượng tương ứng là bao nhiêu.

### 2. Phương pháp
**OCR làm "người đọc đại diện".** PSNR/SSIM đo sai khác pixel/cấu trúc trên toàn ảnh nên không cho biết chữ còn đọc được hay không (ví dụ ảnh có SSIM 0,89 vẫn có thể đọc trọn vẹn, xem mục 4). OCR cho một con số trực tiếp theo đúng mục đích sử dụng (đọc nội dung): tesseract 5.3.4, `lang='vie'`, kết quả so với ground truth `data/text_ground_truth.json` (tên, giá, 6 dòng thông số của mỗi ảnh). Ưu điểm: khách quan, tự động, lặp lại được; nhược điểm xem mục 6.

**Chỉ số.** CER = khoảng cách Levenshtein (ký tự) / số ký tự GT; WER tính tương tự trên từ. Cả hai sau chuẩn hoá Unicode NFC và gộp khoảng trắng; Levenshtein tự cài bằng quy hoạch động.

**Chọn cấu hình OCR trên ảnh gốc** (`ocr_config_selection.csv`). Thử {toàn ảnh, cắt vùng chữ} × {phóng 1×, 2× LANCZOS} × `--psm` {3, 4, 6, 11}. Kết quả: OCR toàn ảnh cho CER trung bình 33–56 % ngay trên ảnh gốc vì ảnh còn dải tiêu đề, nhãn giảm giá, dòng "Đã bán", tiêu đề bảng, ... không có trong GT (chèn thừa), nên không phản ánh chất lượng nén. Cắt vùng chữ cố định theo bố cục `text_card()` (k = S/1000): vùng A (tên + giá) x ∈ [440k, S], y ∈ [120k, 270k]; vùng B (6 dòng thông số) x ∈ [30k, S−30k], y ∈ [585k, S] đưa CER xuống 0,8–1,1 %. Trong các cấu hình hướng khối văn bản (psm 3/4/6) tốt nhất là phóng 2×, CER trung bình 0,89 %; hoà giữa psm 3/4/6 nên chọn psm 6 (khối văn bản đồng nhất). psm 11 (sparse, 0,80 % ở 1×) bị loại vì không bảo đảm thứ tự đọc, CER có thể nhảy do đảo dòng chứ không do chất lượng ảnh. **Cấu hình dùng: cắt hai vùng, phóng 2×, psm 6**, áp dụng giống hệt cho ảnh gốc và ảnh đã nén.

**Thí nghiệm.** 7 ảnh × 3 codec (JPEG 4:2:0 mặc định Pillow; JPEG 4:4:4 `subsampling=0`; WebP lossy `method=4`) × quality {5, 10, 20, 30, 40, 50, 60, 75, 90} = 189 ảnh nén, giải mã bằng `common.decode`, đo dung lượng, PSNR, SSIM (`common.psnr/ssim`) và CER/WER. Số liệu: `ocr_results.csv`.

**Định nghĩa "còn đọc được".** CER(nén) ≤ CER(gốc) + δ, δ = 1 và 2 điểm phần trăm. Dùng mức chênh so với ảnh gốc vì OCR không hoàn hảo ngay cả trên ảnh sạch (xem Bảng 1). Quality tối thiểu là quality nhỏ nhất trong lưới sao cho nó **và mọi quality cao hơn trong lưới** đều thoả, để một lần OCR may mắn ở quality thấp không bị tính là đạt. Kết quả: `min_readable_quality.csv` (từng ảnh) và `min_readable_summary.csv` (gộp theo cỡ ảnh).

### 3. Kết quả
**Bảng 1. CER/WER của OCR trên ảnh PNG gốc (mốc).**

| Ảnh | Kích thước | CER (%) | WER (%) | CER vùng tên+giá (%) | CER vùng thông số (%) |
|---|---|---|---|---|---|
| T01 | 1000 | 0,53 | 2,56 | 2,70 | 0,00 |
| T02 | 1000 | 0,64 | 2,86 | 2,63 | 0,00 |
| T03 | 1000 | 1,23 | 8,33 | 3,03 | 0,78 |
| T04 | 1000 | 1,31 | 6,06 | 5,71 | 0,00 |
| T05 | 500 | 0,56 | 3,12 | 2,63 | 0,00 |
| T06 | 500 | 1,37 | 6,25 | 5,71 | 0,00 |
| T07 | 500 | 0,60 | 2,56 | 3,23 | 0,00 |

OCR không hoàn hảo ngay trên ảnh gốc: CER 0,53–1,37 %, WER 2,6–8,3 %. Phần lớn lỗi nằm ở vùng tên + giá (ví dụ ký hiệu "₫" thường bị đọc thành "đ"), còn vùng thông số gần như không lỗi. Vì vậy ngưỡng được đặt tương đối so với mốc này.

**Bảng 2. CER trung bình (%) theo quality, ảnh 500 px (3 ảnh, chữ 14 px) và ảnh 1000 px (4 ảnh, chữ 26 px).**

| Quality | 500 px JPEG 4:2:0 | 500 px JPEG 4:4:4 | 500 px WebP | 1000 px JPEG 4:2:0 | 1000 px JPEG 4:4:4 | 1000 px WebP |
|---|---|---|---|---|---|---|
| 5 | 29,04 | 29,64 | 1,03 | 1,08 | 1,08 | 0,93 |
| 10 | 7,40 | 7,60 | 0,84 | 1,21 | 1,21 | 0,93 |
| 20 | 2,31 | 2,31 | 0,84 | 1,08 | 1,08 | 0,93 |
| 30 | 1,07 | 1,07 | 0,84 | 0,93 | 0,93 | 0,93 |
| 50 | 0,84 | 0,84 | 0,61 | 1,09 | 1,09 | 0,93 |
| 75 | 0,84 | 0,84 | 0,84 | 0,93 | 0,93 | 0,93 |
| 90 | 0,61 | 0,61 | 0,61 | 0,93 | 0,93 | 0,95 |
| *Mốc PNG gốc* | 0,84 | | | 0,93 | | |

Hình: `figures/t07/cer_vs_quality.png` (CER theo quality, tách 1000/500 px; đường JPEG 4:2:0 và 4:4:4 gần như trùng nhau nên đường đen bị đường xanh che), `figures/t07/cer_vs_size.png` (CER theo dung lượng trung bình), `figures/t07/text_crops.png` (hai dòng thông số chữ 14 px của T05 ở gốc / JPEG q20 / JPEG q50 / WebP q20 / WebP q50, phóng nearest).

**Bảng 3. Quality tối thiểu để còn đọc được và dung lượng trung bình tại mức đó (KB).** "Tệ nhất" là giá trị lớn nhất trong các ảnh cùng cỡ (dùng để khuyến nghị an toàn); dung lượng so với mức q90 và PNG cùng cỡ.

| Cỡ ảnh | Codec | δ | q tối thiểu (trung vị / tệ nhất) | KB tại q tối thiểu | KB tại q90 | KB PNG |
|---|---|---|---|---|---|---|
| 500 px | JPEG 4:2:0 | 1 | 30 / 30 | 17,3 | 48,5 | 86,7 |
| 500 px | JPEG 4:2:0 | 2 | 20 / 30 | 16,2 | 48,5 | 86,7 |
| 500 px | JPEG 4:4:4 | 1 | 30 / 30 | 21,5 | 60,0 | 86,7 |
| 500 px | JPEG 4:4:4 | 2 | 20 / 30 | 20,3 | 60,0 | 86,7 |
| 500 px | WebP lossy | 1 và 2 | ≤ 5 / ≤ 5 | 7,6 | 27,9 | 86,7 |
| 1000 px | JPEG 4:2:0 | 1 và 2 | ≤ 5 / ≤ 5 | 25,1 | 122,4 | 270,7 |
| 1000 px | JPEG 4:4:4 | 1 và 2 | ≤ 5 / ≤ 5 | 36,8 | 153,5 | 270,7 |
| 1000 px | WebP lossy | 1 và 2 | ≤ 5 / ≤ 5 | 16,7 | 63,9 | 270,7 |

Lưu ý: "≤ 5" nghĩa là mọi quality trong lưới (kể cả q5, giá trị thấp nhất đã thử) đều thoả; quality tối thiểu thực sự có thể thấp hơn nhưng không được thí nghiệm này khảo sát. Ở ảnh 1000 px không tìm được điểm "gãy" trong lưới; ở ảnh 500 px, JPEG gãy giữa q10 và q30 (T05 và T07 đạt từ q20 với δ = 2; T06 phải q30).

### 4. Nhận xét và cơ chế
1. **Chữ 26 px rất bền, chữ 14 px thì không.** Ở 1000 px, cả ba codec giữ CER gần mốc (0,93–1,21 % so với 0,93 %) ngay từ q5, dù ở q5 chất lượng chung đã thấp (SSIM trung bình của JPEG q5 là 0,89, sai số màu tuyệt đối trung bình ở vùng tên+giá là 11,3 mức trên thang 0–255). Ở 500 px, JPEG q5 cho CER trung bình 29,0 % (WER 69 %), q10 là 7,4 %, q20 là 2,3 %, chỉ về sát mốc từ q30–q40. Ở q10, CER vùng thông số của ba ảnh 500 px là 6,4–11,4 % trong khi vùng này ở ảnh 1000 px chỉ 0,8 %.
2. **Cơ chế.** Nét chữ là biên sắc, nhiều năng lượng ở tần số cao trong DCT. JPEG chia bảng lượng tử theo quality và lượng tử hoá thô nhất ở hệ số tần cao; q thấp triệt các hệ số này về 0 nên biên bị mờ và sinh nhiễu quanh nét (ringing, nhiễu khối 8×8). Nét chữ 14 px dày khoảng 1–2 px, gần như chỉ gồm thành phần tần cao, và mỗi ký tự chỉ rộng vài ô 8×8, nên bị phá trước; chữ 26 px dày gấp đôi, năng lượng dồn nhiều hơn về tần thấp nên sống sót hơn. Hình `text_crops.png` cho thấy ở JPEG q20, "Pin 4000 mAh" đã có viền mờ/nhiễu quanh nét nhưng còn đọc được (CER 1,1 % cho cả ảnh T05).
3. **Cùng quality, WebP bền hơn, nhưng so sánh công bằng là cùng dung lượng.** Thang quality của hai codec khác nhau nên không so thẳng "q5 với q5". Ở cùng dung lượng ≈ 15 KB (ảnh 500 px, trung bình): JPEG 4:2:0 q20 (15,1 KB) CER 2,31 %, WebP q50 (15,1 KB) CER 0,61 %. Ở ≈ 8 KB: JPEG q5 (8,3 KB) CER 29,0 % so với WebP q5 (7,6 KB) CER 1,03 %. Có thể giải thích (chưa kiểm chứng bằng ablation trong phần này) là WebP dùng dự đoán nội khung và biến đổi 4×4 nên lỗi lượng tử hoá khu trú trong ô nhỏ hơn, cộng bộ lọc khử khối trong vòng lặp; vùng nền phẳng sau dự đoán còn rất ít dư thừa để mã hoá, nhờ vậy dành bit cho biên chữ.
4. **Chroma 4:2:0 không ảnh hưởng OCR nhưng làm lệch màu.** CER của JPEG 4:2:0 và 4:4:4 gần như trùng ở mọi quality (Bảng 2), vì OCR chủ yếu dựa vào độ chói còn 4:2:0 chỉ giảm độ phân giải kênh màu. Tuy nhiên ở vùng chữ đỏ + nền trắng (giá, nhãn giảm giá), sai số màu tuyệt đối trung bình (cột `mae_rgb_nameprice`) của 4:2:0 cao hơn 4:4:4: ví dụ 4,31 so với 3,42 ở 500 px q50 và 2,77 so với 2,10 ở 1000 px q50, nhất quán với hiện tượng chroma "loang" ra ngoài nét chữ do kênh màu bị lấy mẫu giảm một nửa theo mỗi chiều. Cái giá của 4:4:4 là dung lượng tăng khoảng 22 % (500 px q50: 29,1 so với 23,8 KB) đến 27 % (1000 px q50: 78,5 so với 61,6 KB), và tăng tới 46 % ở q5 1000 px. Phép đo này chỉ cho thấy sai khác màu; mức độ khó chịu với mắt người không được đo ở đây.

### 5. Khuyến nghị mức quality tối thiểu cho ảnh có chữ
Các khuyến nghị theo ngưỡng "máy đọc được" (δ = 1 điểm phần trăm, trường hợp xấu nhất trong nhóm), kèm biên an toàn ghi riêng:
- **Ảnh 1000 px, chữ ≥ 26 px:** OCR không phân biệt được các mức q5–q90 (trong lưới). Về mặt đọc chữ có thể nén rất mạnh (WebP q5 ≈ 16,7 KB, JPEG 4:2:0 q5 ≈ 25,1 KB, so với PNG 270,7 KB). Nhưng ngưỡng này chỉ bảo đảm chữ, không bảo đảm phần ảnh sản phẩm hay màu giá; nên dùng biên an toàn do chúng tôi đề xuất (là phán đoán, không phải số đo): WebP q ≥ 40 (≈ 29 KB) hoặc JPEG q ≥ 50 (≈ 62 KB).
- **Ảnh 500 px, chữ 14 px (trường hợp khó):** JPEG tối thiểu **q30** (≈ 17 KB, so với 86,7 KB PNG); dưới q20 chữ mất hẳn (CER 7–29 %). Khuyến nghị thực hành JPEG q ≥ 40–50 (≈ 21–24 KB) để chừa biên. WebP lossy đạt ngưỡng ngay từ q5 (≈ 7,6 KB) nhưng nên dùng q ≥ 40 (≈ 13,6 KB) để chừa biên.
- **Nên dùng WebP lossy** cho ảnh có chữ khi trình duyệt đích hỗ trợ: cùng mức đọc được, dung lượng chỉ bằng 44 % (500 px, q tối thiểu: 7,6 so với 17,3 KB) đến 66 % (1000 px, q5: 16,7 so với 25,1 KB) so với JPEG 4:2:0. Nếu chữ nhỏ hơn 14 px hoặc yêu cầu pixel-chính-xác (mã vạch, bảng giá), dùng WebP lossless/PNG.
- **Dùng 4:4:4 chỉ khi màu quanh chữ đỏ/vàng quan trọng**; đừng dùng nó để cứu khả năng đọc, vì không cải thiện CER mà tốn thêm 22–46 % dung lượng.

### 6. Hạn chế
- **OCR ≠ mắt người.** OCR không nhạy với một số lỗi mắt người thấy rõ (loang màu, viền ringing, vết khối) và ngược lại có thể đọc sai những chữ mắt người suy ra được từ ngữ cảnh. Ngưỡng "gốc + 1 điểm phần trăm" là quy ước của nhóm, không phải ngưỡng tâm lý–thị giác; chưa có thí nghiệm với người đọc.
- **Font tổng hợp.** Chỉ một font (DejaVu Sans, không chân, nét đều), nền trắng/xám nhạt, tương phản cao, chữ đen/xám đậm; ảnh thật có nhiều font, chữ trên nền hoa văn, chữ ngược màu hay chữ nghiêng sẽ khó hơn. Kết luận về q tối thiểu nhiều khả năng lạc quan so với ảnh thực.
- **Mẫu nhỏ và độ phân giải của CER.** Chỉ 7 ảnh (3 ảnh 500 px, 4 ảnh 1000 px); mỗi ảnh có khoảng 150–180 ký tự, nên 1 ký tự sai ≈ 0,56–0,67 điểm phần trăm; các khác biệt dưới 1 điểm (ví dụ 0,84 so với 0,61 %) là nhiễu OCR, không phải khác biệt thật. Ngưỡng δ = 1 chỉ lớn hơn 1–2 ký tự lỗi; vì vậy δ = 1 và δ = 2 cho kết quả gần giống nhau ở 1000 px và JPEG q tối thiểu ở 500 px chỉ nhỏ hơn một nấc (30 → 20) với 2 trong 3 ảnh.
- **Lưới quality có đáy ở 5.** Với ảnh 1000 px và WebP 500 px, q tối thiểu chỉ biết là "≤ 5"; chưa khảo sát q < 5 nên không biết điểm gãy thực.
- **Cấu hình OCR được chọn trên ảnh gốc** (cắt vùng, phóng 2×, psm 6) và vùng cắt cố định theo bố cục đã biết, không có bước phát hiện chữ tự động như trong hệ thống thực tế; phóng 2× bằng LANCZOS có thể làm mịn bớt một phần nhiễu khối của ảnh nén (áp dụng như nhau cho mọi ảnh, nhưng không được đối chứng bằng OCR không phóng cho toàn bộ lưới).
- **Cắt vùng nên CER tuyệt đối thấp hơn thực tế sử dụng**; chỉ nên đọc kết quả theo độ chênh so với ảnh gốc.
