## So sánh cùng chất lượng (iso-quality), câu hỏi PSNR hay SSIM và khuyến nghị cho website TMĐT

### 1. Mục tiêu

Các phép so sánh "cùng quality" giữa JPEG và WebP không công bằng vì thang quality của hai bộ mã hoá khác nhau. Phần này so sánh theo cùng chất lượng đo được. Với mỗi ảnh và mỗi codec, tìm quality nhỏ nhất đạt một ngưỡng chất lượng rồi so dung lượng. Trên cơ sở đó, phần này trả lời hai câu hỏi: (i) nên dùng PSNR hay SSIM; (ii) website TMĐT nên dùng định dạng và mức nén nào cho từng loại ảnh, kèm phương án dự phòng.

### 2. Phương pháp và lý do chọn tham số

- **Quét:** quality = 5, 10, ..., 100 (20 mức) × 3 codec × 20 ảnh = 1200 điểm, gọi `common.evaluate(..., repeats=0)` (file `sweep.csv`). Ba codec gồm JPEG 4:2:0 (mặc định của Pillow, cấu hình web phổ biến nhất), JPEG 4:4:4 (`subsampling=0`) và WebP lossy `method=4`. JPEG 4:4:4 được thêm vào để tách riêng ảnh hưởng của giảm mẫu sắc độ.
- **Iso-quality:** với mỗi (ảnh, codec) lấy quality nhỏ nhất trên lưới đạt SSIM ≥ {0,95; 0,98; 0,99} hoặc PSNR ≥ {35; 40 dB}, ghi dung lượng tại điểm đó (`isoquality.csv`). Nếu q = 100 vẫn không đạt thì ghi "không đạt" và không ngoại suy. Vì lưới bước 5 thô nên có thêm cột nội suy `size_interp_kb` để kiểm tra độ nhạy. Tại SSIM 0,95, trung vị % tiết kiệm của WebP so với JPEG 4:2:0 theo nội suy lệch so với theo lưới tối đa 3,4 điểm % (P: 32,0 so với 28,6; T: 62,3 so với 64,4; G: 80,0 so với 80,4; xem `isoquality_by_group.csv`), không đổi kết luận về thứ tự. Số liệu trong bảng lấy theo lưới đúng như đề bài.
- **Baseline không mất mát:** PNG `compress_level=9` và WebP lossless `quality=100, method=4`. WebP lossless được kiểm tra giải mã khớp từng điểm ảnh trên cả 20 ảnh.
- **Tránh thiên lệch do "không đạt":** khi một codec không đạt ngưỡng ở nhiều ảnh, trung bình trên các ảnh còn lại bị lệch. Vì vậy bảng dùng trung vị, ghi rõ số ảnh đạt, và chỉ tính % tiết kiệm trên các cặp ảnh mà cả hai codec cùng đạt. Cột `mean_kb_common` trong CSV cho trung bình trên tập ảnh chung.
- **Khuyến nghị:** với mỗi loại ảnh và hai mức mục tiêu ("tiết kiệm" SSIM ≥ 0,95; "chất lượng cao" SSIM ≥ 0,98), chọn quality nhỏ nhất sao cho **mọi** ảnh trong nhóm đạt (bảo đảm cho ảnh xấu nhất). Sau đó đặt sàn q ≥ 50 như một biên an toàn kinh nghiệm cho lỗi mà PSNR/SSIM đánh giá thấp. Sàn này **không phải kết quả đo**; quan sát bằng mắt trên G01 cho thấy WebP q = 5 có dải màu mờ trên nền gradient. Nhóm G được tách thành G sạch (G01–G03) và G có nhiễu cảm biến (G04–G06) vì hai nhóm con cho kết quả rất khác nhau.

### 3. Kết quả iso-quality

Hình: `figures/t06/iso_ssim_size.png` – Dung lượng trung bình cần để đạt SSIM 0,95 / 0,98 / 0,99 theo nhóm và codec (trục log). Trong ngoặc là số ảnh đạt/tổng số ảnh. Đường nét đứt là dung lượng trung bình của WebP lossless.

**Bảng 1.** Dung lượng tại quality nhỏ nhất đạt ngưỡng SSIM (trung vị, KB; trong ngoặc là số ảnh đạt). Cột cuối là trung vị % tiết kiệm của WebP so với JPEG 4:2:0 (trong ngoặc là số cặp ảnh cùng đạt).

| Nhóm | SSIM | JPEG 4:2:0 | JPEG 4:4:4 | WebP lossy | WebP tiết kiệm (số cặp) |
|---|---|---|---|---|---|
| P | 0,95 | 58,7 (7/7) | 56,7 (7/7) | 42,7 (7/7) | 28,6 % (7) |
| P | 0,98 | 189,7 (5/7) | 154,9 (7/7) | 96,9 (2/7) | 32,1 % (2) |
| P | 0,99 | 162,0 (1/7) | 314,0 (7/7) | không đạt (0/7) | – |
| T | 0,95 | 41,4 (7/7) | 51,2 (7/7) | 14,5 (7/7) | 64,4 % (7) |
| T | 0,98 | 106,7 (7/7) | 102,1 (7/7) | 34,6 (7/7) | 66,4 % (7) |
| T | 0,99 | 276,2 (2/7) | 136,1 (7/7) | 116,6 (1/7) | 57,1 % (1) |
| G | 0,95 | 12,8 (6/6) | 20,0 (6/6) | 2,6 (6/6) | 80,4 % (6) |
| G | 0,98 | 19,3 (3/6) | 151,1 (6/6) | 3,6 (3/6) | 81,5 % (3) |
| G | 0,99 | 22,0 (3/6) | 152,6 (6/6) | 4,1 (3/6) | 81,5 % (3) |
| Cả 20 ảnh | 0,95 | 33,0 (20/20) | 32,7 (20/20) | 14,0 (20/20) | 62,6 % (20) |
| Cả 20 ảnh | 0,98 | 106,7 (15/20) | 111,4 (20/20) | 32,9 (12/20) | 66,4 % (12) |
| Cả 20 ảnh | 0,99 | 92,2 (6/20) | 171,0 (20/20) | 4,6 (4/20) | 79,5 % (4) |

Theo PSNR, trên cả 20 ảnh, ngưỡng 35 dB cần trung vị 43,2 KB (JPEG 4:2:0, 19/20 ảnh đạt), 36,4 KB (JPEG 4:4:4, 20/20) và 20,1 KB (WebP, 19/20). WebP tiết kiệm trung vị 62,3 % so với JPEG 4:2:0 trên 19 cặp. Ngưỡng 40 dB khó hơn nhiều: chỉ 9/20 ảnh đạt với WebP và 11/20 với JPEG 4:2:0. Ảnh không đạt 35 dB ở cả hai codec này là P06_baboon (nhiều chi tiết mịn nhất).

**Nhận xét và cơ chế.**

1. **WebP lossy nhỏ hơn JPEG rõ rệt ở cùng SSIM, nhất là ảnh phẳng.** Mức giảm trung vị so với JPEG 4:2:0 là khoảng 29–32 % cho ảnh chụp, 64–66 % cho ảnh chữ và 80–82 % cho ảnh nền trơn. Cơ chế (giải thích theo nguyên lý thuật toán, không đo riêng trong phần này): WebP lossy dự đoán mỗi khối từ các điểm ảnh lân cận đã giải mã (intra prediction) rồi chỉ mã hoá phần dư, nên vùng phẳng/gradient có phần dư rất nhỏ. JPEG biến đổi DCT 8×8 từng khối gần như độc lập (chỉ mã hoá chênh lệch DC giữa các khối kề nhau), nên mỗi khối vẫn tốn bit cho cả vùng phẳng. Khác biệt này nhỏ lại khi ảnh nhiều chi tiết vì phần dư lớn bất kể bộ dự đoán.
2. **Có "vách đá" giữa SSIM 0,95 và 0,99 với ảnh màu.** WebP lossy chỉ đạt SSIM 0,98 ở 12/20 ảnh và 0,99 ở 4/20 ảnh, trong khi JPEG 4:2:0 đạt lần lượt 15/20 và 6/20; JPEG 4:4:4 đạt cả 20/20. Chẩn đoán trong `mechanism_diagnostic.csv`: ở q = 100, ảnh T06 có SSIM(Y) = 0,999 cho cả ba codec, nhưng SSIM(RGB) chỉ là 0,985 (JPEG 4:2:0) và 0,984 (WebP) so với 0,999 (JPEG 4:4:4). Ảnh P06_baboon cho SSIM(RGB) = 0,964 với JPEG 4:2:0 q = 100, SSIM(Cb) = 0,863 và SSIM(Y) = 0,998. Như vậy trần SSIM do **giảm mẫu sắc độ 4:2:0** gây ra; WebP lossy luôn dùng 4:2:0 nên cũng bị trần này. Chữ đỏ/vàng trên nền cam có biên sắc độ sắc nét nên ảnh T nhạy với trần này (đây là giải thích phù hợp với số đo trên, chưa kiểm chứng riêng bằng thí nghiệm khống chế). Ngoài ra SSIM tính trên từng kênh RGB nên cho trọng số sắc độ cao hơn mắt người (xem mục 5).
3. **Nhiễu cảm biến làm chỉ tiêu SSIM cao trở nên cực đắt.** Với G04–G06 (nhiễu Gauss σ = 1,5, gần như không thấy bằng mắt), WebP q = 50 chỉ cần 2,2 KB để đạt SSIM trung bình 0,958 (sau khi nhiễu bị làm mịn), nhưng SSIM ≥ 0,98 không ảnh nhiễu nào đạt với JPEG 4:2:0 hay WebP lossy (0/3). Chỉ JPEG 4:4:4 q = 100 (275,0 KB) hoặc WebP lossless (260,1 KB) đạt được. SSIM coi nhiễu là một phần cấu trúc cần giữ lại.

**Lossless có thể nhỏ hơn lossy tại SSIM 0,99 không?** Có, ở 13/20 ảnh. Đó là so với codec lossy tốt nhất đạt 0,99 trên ảnh đó (JPEG 4:4:4 q gần 100, vì WebP lossy và JPEG 4:2:0 thường không đạt).

**Bảng 3.** Dung lượng trung bình (KB) của PNG và WebP lossless, và số ảnh mà WebP lossless nhỏ hơn lossy tốt nhất đạt SSIM 0,99.

| Nhóm | PNG (level 9) | WebP lossless | Số ảnh lossless nhỏ hơn |
|---|---|---|---|
| P | 388,2 | 304,9 | 6/7 |
| T | 191,8 | 133,9 | 4/7 (T01, T05, T06, T07) |
| G | 185,0 | 150,5 | 3/6 (chỉ G04–G06 có nhiễu) |
| Cả 20 ảnh | 258,5 | 198,7 | 13/20 |

Điều này trái với dự đoán ban đầu rằng ảnh G sạch có thể là ngoại lệ. Với G sạch (G01–G03), WebP lossy đạt 0,99 chỉ với 3,1–5,1 KB, còn lossless cần 6,9–59,5 KB. Ngược lại, lossless nhỏ hơn ở ảnh chữ 500 px (T05–T07) và ở ảnh chụp thật, vì để đạt 0,99 JPEG 4:4:4 phải dùng q trung vị 95 (nhóm T) và 100 (nhóm P), tức đã tiệm cận không mất mát. PNG nhỏ hơn lossy tốt nhất ở đúng một ảnh (T07: 65,6 KB so với 70,4 KB). WebP lossless nhỏ hơn PNG ở 20/20 ảnh; theo dung lượng trung bình là 198,7 KB so với 258,5 KB, tức tiết kiệm khoảng 23 % (tính trên dung lượng trung bình).

### 4. Câu hỏi mở: PSNR hay SSIM?

Hình: `figures/t06/psnr_vs_ssim.png` – SSIM theo PSNR trên toàn bộ 1200 điểm quét, màu theo nhóm (a: thang tuyến tính; b: SSIM đổi sang thang dB, −10·log10(1 − SSIM)).
Hình: `figures/t06/ssim_map_example.png` – Ví dụ bất đồng trên T06_card500 (cùng ảnh, cùng cỡ tệp). Hàng 1: ảnh gốc và hai bản nén; hàng 2: bản đồ SSIM cục bộ (thang 0,5–1); hàng 3: bản đồ sai số tuyệt đối. Ảnh hiển thị là vùng cắt 160×160; số đo trong tiêu đề cột là trên cả ảnh.

**Số liệu.** Hệ số Spearman giữa PSNR và SSIM trên toàn bộ điểm quét là ρ = 0,848. Theo nhóm là 0,976 (T), 0,905 (P), 0,902 (G); theo codec là 0,858 (JPEG 4:2:0), 0,884 (JPEG 4:4:4) và 0,789 (WebP lossy). Các giá trị này thấp hơn nhiều so với tương quan **trong từng ảnh** (trung bình 20 ảnh là 0,989, thấp nhất 0,958 ở G04). Nói cách khác, hai chỉ số đồng thuận khi so sánh các cấu hình trên **cùng một ảnh**, nhưng không đồng thuận khi so sánh **giữa các ảnh**. Ví dụ P02_chelsea (q = 5, 9,0 KB) và T02_card1000 (q = 5, 36,0 KB) cùng PSNR ≈ 26,0 dB nhưng SSIM là 0,651 so với 0,919 (hiện trong `disagreement_examples.csv`; PSNR của hai ảnh này lệch 0,07 dB). Cùng một ngưỡng "35 dB" hay "40 dB" vì vậy ứng với chất lượng cảm nhận rất khác nhau tuỳ nội dung ảnh.

Trong cùng một ảnh, các cặp cấu hình có PSNR và SSIM đổi chiều (|ΔPSNR| ≥ 0,5 dB và |ΔSSIM| ≥ 0,002) hiếm: 207/30954 cặp (0,67 %), nhiều nhất ở nhóm T (0,90 %) và G (0,93 %), ít nhất ở P (0,25 %).

**Ví dụ bất đồng (T06_card500).** Cấu hình A (JPEG 4:4:4, q = 85) cho PSNR 38,49 dB, SSIM 0,9759, 50,2 KB. Cấu hình B (WebP lossy, q = 100) cho PSNR 36,57 dB, SSIM 0,9842, 44,8 KB. A hơn B 1,91 dB về PSNR nhưng thua 0,0082 về SSIM, và B còn nhỏ hơn khoảng 11 %. Ở vùng cắt hiển thị, chênh lệch PSNR còn lớn hơn (33,9 dB so với 29,5 dB) trong khi SSIM gần nhau (0,924 so với 0,930).

Cơ chế (từ `mechanism_diagnostic.csv`): B bị lỗi chủ yếu là sắc độ do 4:2:0, với PSNR(Cb) 41,2 dB so với 44,9 dB của A. Sai số này có biên độ lớn và tập trung dọc theo các biên màu (hàng 3, cột B), nên phạt nặng PSNR vốn dựa trên bình phương sai số. Độ sáng của B vẫn gần nguyên vẹn (SSIM(Y) = 0,999; PSNR(Y) = 44,5 dB). A có sắc độ tốt nhưng lượng tử hoá DCT q = 85 làm sai số độ sáng (SSIM(Y) = 0,989; PSNR(Y) = 41,0 dB) lan thành các đốm nhỏ nằm rải trên cả vùng phẳng quanh chữ (hàng 3, cột A). Sai số có biên độ nhỏ nhưng phá cấu trúc cục bộ nên bị SSIM phạt. Trong bản đồ SSIM, hư hại của A trải rộng hơn trên thanh tiêu đề và nhãn "-30%", còn của B là các viền hẹp quanh nét chữ. Đây là cách diễn giải từ bản đồ và số đo chẩn đoán, chưa có thí nghiệm khống chế riêng.

**Lập trường.** Dùng **SSIM làm chỉ số chính** để so sánh và đặt ngưỡng chất lượng, và dùng **PSNR làm chỉ số phụ**. Lý do:
1. Mục tiêu của khách hàng TMĐT là thấy được biên, chữ và texture của sản phẩm. Đó là thông tin cấu trúc, và SSIM đo trực tiếp độ tương quan cấu trúc cục bộ, trong khi PSNR chỉ đo năng lượng sai số toàn cục.
2. Trong ví dụ trên, SSIM ưu tiên bản nhỏ hơn và có cấu trúc độ sáng nguyên vẹn hơn (SSIM(Y) 0,999 so với 0,989); PSNR ưu tiên bản ngược lại. Phần này chưa có đánh giá bằng mắt người nên chỉ là lập luận, không phải chứng minh.
3. Bản đồ SSIM cục bộ chỉ ra **chỗ** hỏng (viền chữ, nhãn giảm giá) để sửa, còn PSNR chỉ cho một con số.
4. PSNR vẫn cần giữ lại vì nó nhạy với lệch màu và độ sáng toàn cục, và nó có thang dB thuận tiện.

**Hạn chế của cả hai.**
- Cả hai đều là chỉ số tham chiếu đầy đủ đơn thang đo, không mô hình hoá thị giác người đầy đủ.
- SSIM bão hoà gần 1 (xem Hình, panel b) và chỉ cho thấy khác biệt nhỏ ở ngưỡng cao.
- SSIM RGB cho trọng số sắc độ cao hơn thị giác người nên phạt 4:2:0 nặng hơn mức người dùng cảm nhận.
- SSIM coi nhiễu là cấu trúc (ví dụ nhóm G04–G06).
- Cả hai đều không bắt tốt hiện tượng dải màu (banding) trên nền gradient.
- Cả hai không nói gì về khả năng đọc chữ. Trường hợp ảnh chữ cần thêm kiểm tra bằng OCR (ngoài phạm vi phần này).
- Hướng mở rộng: MS-SSIM (đa thang), Butteraugli và SSIMULACRA2 (mô hình cảm nhận màu), chưa được đo trong phần này.

### 5. Khuyến nghị cho website TMĐT

**Bảng 5.** Khuyến nghị theo loại ảnh. "q đo" là quality nhỏ nhất trên lưới mà mọi ảnh trong nhóm đạt mục tiêu; quality khuyến nghị = max(q đo, 50). Dung lượng, SSIM và PSNR là giá trị TB (min) tại quality khuyến nghị trên các ảnh của nhóm. Dự phòng JPEG dùng cùng quy tắc quality; vì sàn q = 50 áp dụng cho cả hai, cột "so với chính" ở nhóm G sạch/nhiễu không phải so sánh iso-quality (so sánh iso-quality xem Bảng 1).

| Loại ảnh (số ảnh) | SSIM mục tiêu | Định dạng chính, quality (q đo) | Dung lượng TB KB (bpp) | SSIM TB (min) | PSNR TB (min) dB | Dự phòng JPEG trong `<picture>` | WebP lossless / PNG KB |
|---|---|---|---|---|---|---|---|
| Ảnh có chữ T (7) | ≥ 0,95 | WebP lossy q=50 (30) | 25,1 (0,36) | 0,970 (0,960) | 35,0 (32,9) | 4:2:0 q=75, 61,2 KB (+144 %) | 133,9 / 191,8 |
| Ảnh có chữ T (7) | ≥ 0,98 | WebP lossy q=95 (95) | 62,5 (0,88) | 0,986 (0,983) | 38,1 (36,1) | 4:4:4 q=90, 113,5 KB (+82 %) | 133,9 / 191,8 |
| Gradient/nền trơn sạch G01–G03 (3) | ≥ 0,95 và ≥ 0,98 | WebP lossy q=50 (5) | 4,8 (0,04) | 0,994 (0,992) | 45,4 (44,9) | 4:2:0 q=50, 22,7 KB (+376 %) | 41,0 / 69,1 |
| Gradient có nhiễu G04–G06 (3) | ≥ 0,95 | WebP lossy q=50 (20) | 2,2 (0,07) | 0,958 (0,956) | 40,2 (39,4) | 4:2:0 q=50, 8,1 KB (+260 %) | 260,1 / 300,8 |
| Gradient có nhiễu G04–G06 (3) | ≥ 0,98 | WebP lossless | 260,1 (8,52) | 1,000 | – | JPEG 4:4:4 q=100, 275,0 KB (+6 %) | 260,1 / 300,8 |
| Ảnh chụp nhiều chi tiết P (7) | ≥ 0,95 | WebP lossy q=90 (90) | 57,1 (1,87) | 0,963 (0,950) | 37,2 (32,1) | 4:4:4 q=90, 90,4 KB (+58 %) | 304,9 / 388,2 |
| Ảnh chụp nhiều chi tiết P (7) | ≥ 0,98 | WebP lossless | 304,9 (9,99) | 1,000 | – | JPEG 4:4:4 q=100, 326,5 KB (+7 %) | 304,9 / 388,2 |

Bảng đầy đủ nằm ở `results/t06/recommendation.csv`.

**Khuyến nghị cụ thể.**
- **Ảnh chữ (thẻ sản phẩm, banner, bảng thông số):** WebP lossy q ≈ 95 nếu cần SSIM ≥ 0,98 (62,5 KB TB, giảm 53 % so với WebP lossless 133,9 KB). Nếu chấp nhận SSIM ≈ 0,97, q = 50 chỉ nặng 25,1 KB. Ảnh chữ nhỏ (14 px trong ảnh 500 px) nên dùng mức cao và cần kiểm tra OCR/đọc bằng mắt trước khi hạ q. Không nên kỳ vọng SSIM 0,99 từ WebP lossy (chỉ 1/7 ảnh đạt, 4:2:0).
- **Gradient/nền trơn sạch (studio):** WebP lossy q ≈ 50 là lựa chọn hiệu quả nhất (TB 4,8 KB, SSIM TB 0,994). Không hạ xuống q = 5 chỉ vì số liệu cho phép, vì dải màu mờ có thể xuất hiện mà chỉ số không phản ánh. Nếu ảnh có nhiễu cảm biến, nên khử nhiễu trước khi nén để tránh trả giá cho nhiễu (WebP q = 50: 2,2 KB so với lossless 260,1 KB).
- **Ảnh chụp nhiều chi tiết:** WebP lossy q ≈ 90 (57,1 KB TB, SSIM TB 0,963, min 0,950). SSIM ≥ 0,98 không còn kinh tế: chỉ 2/7 ảnh đạt bằng WebP lossy, phần còn lại buộc phải dùng lossless hoặc JPEG q ≈ 100. Nên kiểm tra thêm bằng mắt vì ảnh sản phẩm thật cần giữ texture.
- **Phương án dự phòng (`<picture>`):** WebP làm nguồn chính, JPEG làm dự phòng cho trình duyệt cũ. Theo Bảng 5, dự phòng JPEG nặng hơn bản WebP từ +58 % (ảnh chụp, SSIM ≥ 0,95) đến +144 % (ảnh chữ, SSIM ≥ 0,95) và +376 % (G sạch, có ảnh hưởng của sàn q = 50), trừ các trường hợp phải dùng gần-lossless (+6 đến +7 %). Với ảnh cần SSIM ≥ 0,98 (chữ) dùng JPEG 4:4:4, với ảnh chụp/nền trơn dùng JPEG 4:2:0 là đủ. Với ảnh không thể đạt mục tiêu bằng JPEG 4:2:0 thì dự phòng nên là JPEG 4:4:4 hoặc PNG.

```html
<picture>
  <source srcset="sanpham.webp" type="image/webp">
  <img src="sanpham.jpg" width="1000" height="1000" loading="lazy" alt="Mô tả sản phẩm">
</picture>
```

### 6. Hạn chế

- Chỉ 20 ảnh (nhóm G chỉ có 6, trong đó 3 sạch và 3 nhiễu; nhóm ảnh chữ là ảnh tổng hợp), nên các phần trăm theo nhóm có độ bất định lớn; không kiểm định ý nghĩa thống kê.
- Lưới quality bước 5; dung lượng tại ngưỡng bị thô (độ lệch nội suy được ghi trong CSV).
- WebP lossy chỉ quét ở `method=4`; các mức `method` khác có thể thay đổi dung lượng (không khảo sát ở phần này).
- Sàn q = 50 và việc quan sát dải màu trên G01 là phán đoán kỹ thuật, không phải kết quả đo. Chưa có kiểm tra cảm nhận người dùng (MOS) hay OCR trong phần này.
- Đo bằng RGB-SSIM theo `common.ssim`; kết luận về "vách đá" 4:2:0 phụ thuộc vào cách tính SSIM trên RGB và có thể nhẹ hơn nếu đo theo SSIM(Y) cộng trọng số sắc độ.
- Thời gian nén/giải nén không đo ở phần này (`repeats=0`).

Tệp liên quan: `src/t06_isoquality_recommend.py`; `results/t06/{sweep, isoquality, isoquality_by_group, lossless_vs_lossy, spearman_psnr_ssim, discordant_by_image, disagreement_examples, mechanism_diagnostic, recommendation}.csv`; `figures/t06/{iso_ssim_size, psnr_vs_ssim, ssim_map_example}.png`.
