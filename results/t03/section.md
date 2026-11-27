## Kết quả baseline: JPEG (q = 50, 75, 90) và PNG không mất mát

### 1. Mục tiêu

Phần này lập **mốc so sánh (baseline)** cho toàn bộ 20 ảnh sản phẩm (7 ảnh P, 7 ảnh T, 6 ảnh G): ba mức chất lượng JPEG điển hình và PNG không mất mát. Kết quả là mốc để đối chiếu với WebP (có mất mát và không mất mát) ở phần t04: WebP chỉ có ý nghĩa nếu cho cùng chất lượng với dung lượng nhỏ hơn các số trong bảng dưới đây. Phần này **không đo thời gian** (thuộc t10).

### 2. Phương pháp và tham số

Mỗi ảnh được mã hoá và giải mã trong bộ nhớ bằng Pillow qua hàm `evaluate()` của `common.py`. Dung lượng tính theo KB (1024 byte), bpp = 8·byte/(W·H), tỉ lệ nén = W·H·3/byte, PSNR tính trên 3 kênh RGB, SSIM theo Wang và cộng sự (2004) trên RGB.

- **JPEG**: `quality` ∈ {50, 75, 90} với các tham số mặc định của Pillow, ghi tường minh trong mã: lấy mẫu sắc độ **4:2:0**, `optimize=False` (bảng Huffman chuẩn), `progressive=False`. Chọn cấu hình mặc định vì đây là cách dùng phổ biến nhất khi một website chỉ chọn "quality"; các biến thể (4:4:4, tối ưu Huffman) thuộc các thí nghiệm ablation riêng, để baseline không bị "tinh chỉnh sẵn" và so sánh với WebP công bằng.
- **PNG**: `compress_level=9` (zlib mạnh nhất), `optimize=False`. Kết quả được kiểm tra `PSNR = ∞`, `SSIM = 1` cho cả 20 ảnh (khôi phục chính xác từng bit).
- Bảng theo nhóm là trung bình ± độ lệch chuẩn mẫu (n−1) **giữa các ảnh**; tỉ lệ nén là trung bình của tỉ lệ từng ảnh. PSNR của PNG là vô cực nên không đưa vào trung bình. Chỉ có 6–7 ảnh mỗi nhóm nên độ lệch chuẩn lớn và mọi kết luận về nhóm chỉ mang tính định hướng.

Số liệu: `results/t03/baseline_per_image.csv` (80 dòng), `results/t03/baseline_by_group.csv`, `results/t03/baseline_channel_error.csv` (phân tích sai số theo kênh YCbCr, mục 4). Mã: `src/t03_baseline.py` (chạy lại cho kết quả giống hệt, không có yếu tố ngẫu nhiên).

### 3. Kết quả

**Bảng 1.** Kết quả baseline theo nhóm (trung bình ± độ lệch chuẩn giữa các ảnh).

| Nhóm | Cấu hình | Dung lượng (KB) | bpp | Tỉ lệ nén (lần) | PSNR (dB) | SSIM |
|---|---|---|---|---|---|---|
| P (n=7) | JPEG q50 | 27,4 ± 11,0 | 0,90 | 30,9 | 32,0 ± 3,2 | 0,904 ± 0,039 |
| P | JPEG q75 | 40,5 ± 16,7 | 1,33 | 21,0 | 33,9 ± 3,3 | 0,931 ± 0,028 |
| P | JPEG q90 | 68,6 ± 27,8 | 2,25 | 12,2 | 36,5 ± 3,3 | 0,957 ± 0,016 |
| P | PNG | 388,2 ± 108,5 | 12,72 | 2,05 | ∞ | 1 |
| T (n=7) | JPEG q50 | 45,4 ± 20,5 | 0,62 | 40,6 | 32,1 ± 1,7 | 0,952 ± 0,013 |
| T | JPEG q75 | 61,2 ± 27,1 | 0,85 | 30,0 | 34,5 ± 1,5 | 0,966 ± 0,008 |
| T | JPEG q90 | 90,7 ± 40,4 | 1,26 | 20,3 | 36,9 ± 1,5 | 0,979 ± 0,004 |
| T | PNG | 191,8 ± 105,5 | 2,48 | 10,2 | ∞ | 1 |
| G (n=6) | JPEG q50 | 15,4 ± 8,0 | 0,23 | 110,0 | 42,2 ± 3,1 | 0,973 ± 0,021 |
| G | JPEG q75 | 19,1 ± 9,3 | 0,29 | 87,8 | 44,3 ± 3,8 | 0,977 ± 0,020 |
| G | JPEG q90 | 30,8 ± 11,0 | 0,51 | 53,8 | 46,6 ± 4,7 | 0,980 ± 0,019 |
| G | PNG | 185,0 ± 130,4 | 5,21 | 43,6 | ∞ | 1 |
| Toàn bộ (n=20) | JPEG q50 | 30,1 ± 18,6 | 0,60 | 58,0 | 35,1 ± 5,4 | 0,942 ± 0,039 |
| Toàn bộ | JPEG q75 | 41,3 ± 25,4 | 0,85 | 44,2 | 37,2 ± 5,5 | 0,957 ± 0,028 |
| Toàn bộ | JPEG q90 | 65,0 ± 37,5 | 1,38 | 27,5 | 39,7 ± 5,6 | 0,972 ± 0,017 |
| Toàn bộ | PNG | 258,5 ± 145,8 | 6,89 | 17,4 | ∞ | 1 |

Lưu ý: dung lượng KB trung bình của nhóm T và G bị ảnh hưởng bởi việc nhóm gồm cả ảnh 500×500 và 1000×1000 (đó là lý do độ lệch chuẩn của KB lớn); bpp và tỉ lệ nén so sánh công bằng hơn.

Hình: `figures/t03/baseline_size_by_group.png` — Dung lượng trung bình (bpp và KB, thang log, thanh sai số = độ lệch chuẩn giữa các ảnh) theo nhóm và cấu hình nén.

Hình: `figures/t03/baseline_quality.png` — PSNR (dB) và SSIM của JPEG q50/75/90 theo nhóm ảnh (PNG: PSNR = ∞, SSIM = 1).

Hình: `figures/t03/baseline_visual.png` — Vùng cắt 128×128 phóng nearest ×3 của T05 (giá "890.000", nhãn "−25%", dòng "Đã bán") và P06 (mắt, lông khỉ) ở ảnh gốc và JPEG q50/75/90; nhãn ghi dung lượng toàn ảnh, PSNR và SSIM của toàn ảnh.

### 4. Nhận xét và giải thích cơ chế

**PNG: tỉ lệ nén phụ thuộc mạnh vào nội dung.** PNG đạt tỉ lệ nén trung bình **2,05 lần** ở nhóm P (12,7 bpp; riêng P06 baboon chỉ 1,28 lần, 18,7 bpp), **10,2 lần** ở nhóm T (khoảng 7,0–15,1) và **43,6 lần** ở nhóm G, nhưng nhóm G phân đôi rõ rệt: ba ảnh sạch G01–G03 đạt 84,8 lần (0,57 bpp) trong khi ba ảnh nhiễu G04–G06 chỉ đạt 2,4 lần (9,86 bpp). Cơ chế: PNG dự đoán mỗi điểm ảnh từ lân cận (bộ lọc dòng Sub/Up/Average/Paeth) rồi nén phần dư bằng DEFLATE (LZ77 + Huffman). Ở vùng nền trơn hoặc gradient trơn, phần dư gần bằng 0 và lặp lại nên nén rất tốt. Ở ảnh chụp, kết cấu và nhiễu cảm biến khiến phần dư gần như ngẫu nhiên nên entropy còn rất cao. Với nhiễu Gauss σ = 1,5 mỗi kênh, ước lượng giải tích 3·log₂(σ√(2πe)) ≈ 7,9 bpp là cận dưới nếu dự đoán hoàn hảo (bộ dự đoán dùng điểm lân cận cũng có nhiễu nên phần dư lớn hơn), và kết quả 9,86 bpp phù hợp với ước lượng này. Chỉ thêm nhiễu vô hình bằng mắt (σ = 1,5 trên thang 255) đã làm bpp của PNG tăng khoảng 17 lần. Nhóm T nằm giữa vì thẻ gồm vùng nền phẳng và chữ (nén tốt) cùng một khối ảnh sản phẩm chụp thật (gần không nén được).

**Ngoại lệ đáng ghi nhận: G03.** Đây là ảnh duy nhất mà PNG (15,2 KB, 0,12 bpp) **nhỏ hơn cả JPEG q50** (22,4 KB), và cũng nhỏ hơn q75, q90. Ảnh chỉ có 1188 màu phân biệt, gradient chủ yếu một chiều (dọc theo nền, ngang theo thân chai) nên bộ lọc Up/Sub dự đoán gần như hoàn hảo; ngược lại JPEG phải mã hoá mọi khối 8×8 (kể cả khối phẳng) với chi phí cố định cho hệ số DC và ký hiệu kết thúc khối, nên có "sàn" dung lượng. Cơ chế "sàn" này là suy luận từ cấu trúc thuật toán, chưa được kiểm chứng riêng bằng thí nghiệm. Kết luận: ngay cả với ảnh gradient, "JPEG luôn nhỏ hơn PNG" không đúng; ảnh nền trơn vẽ tay dạng này nên thử cả hai định dạng.

**JPEG: q50 → q90.** Dung lượng tăng trung bình **2,24 lần** (trung bình của tỉ số từng ảnh; tỉ số của hai dung lượng trung bình toàn bộ là 2,16): nhóm P ×2,52 (2,40–2,64), nhóm T ×2,01 (1,95–2,07), nhóm G ×2,20 (1,61–2,71). Từ q50 lên q75 chỉ tăng ×1,27–1,48 tuỳ nhóm. Mức tăng phù hợp với việc thư viện libjpeg co bước lượng tử theo hệ số 100% (q50), 50% (q75), 20% (q90) so với bảng chuẩn: bước nhỏ hơn thì nhiều hệ số DCT khác 0 hơn và mỗi hệ số cần nhiều bit hơn. PSNR tăng đều **4,4–4,8 dB** (trung bình 4,56 dB) từ q50 lên q90 ở cả ba nhóm, còn SSIM tăng không đều: nhóm P +0,053, nhóm T +0,027, nhóm G chỉ +0,007 (vì SSIM của G đã gần bão hoà 0,973 ở q50). Theo CSV từng ảnh, PSNR thấp nhất ở q50 là 26,3 dB (P06 baboon) và thấp nhất ở q90 của nhóm P là 30,7 dB (cũng P06): ảnh nhiều chi tiết là nhóm khó nhất với JPEG, vì nhiều năng lượng nằm ở tần số cao, đúng phần bảng lượng tử bỏ đi mạnh nhất. So với PNG, JPEG q75 nhỏ hơn trung bình (theo từng ảnh) 10,0 lần ở nhóm P, 3,0 lần ở nhóm T và 15,4 lần ở nhóm G (con số của G bị kéo lên bởi nhóm nhiễu G04–G06 và bị kéo xuống bởi G03, xem trên). PSNR giữa các nhóm cũng **không so sánh trực tiếp được** (G đạt 42–47 dB phần lớn do diện tích nền trơn rất lớn, không phải do giữ chi tiết tốt hơn).

**Ảnh có chữ: ringing và màu loang.** Ở phóng ×3 (hình `baseline_visual.png`, hàng T05) q50 để lại quầng nhiễu quanh chữ số của giá đỏ và làm mờ dòng chữ xám nhỏ, còn viền nhãn "−25%" kém sắc nét hơn; q90 gần như không còn thấy khác biệt bằng mắt thường. Có hai cơ chế độc lập:

1. *Ringing (Gibbs) do lượng tử DCT*: cạnh sắc của nét chữ chứa năng lượng ở nhiều tần số; lượng tử thô các hệ số tần số cao làm tổng cosin không dựng lại được bước nhảy, sinh dao động tắt dần trong cả khối 8×8 chứa cạnh.
2. *Màu loang do lấy mẫu thưa sắc độ 4:2:0*: Cb, Cr bị lấy mẫu giảm còn một nửa theo mỗi chiều, nên nét đỏ rộng 1–3 điểm ảnh bị trung bình với nền trắng và màu "chảy" sang điểm lân cận.

Số đo ở `baseline_channel_error.csv` (nhóm T, sai số bình phương trung bình MSE trong vùng cách cạnh ≤ 3 px, chiếm khoảng 17% số điểm ảnh; "cạnh" được định nghĩa bằng ngưỡng gradient độ sáng > 40, một lựa chọn kinh nghiệm) cho thấy: MSE độ sáng Y ở vùng này giảm từ 109,0 (q50) xuống 16,2 (q90), tức giảm khoảng 6,7 lần, trong khi MSE sắc độ Cr chỉ giảm từ 80,7 xuống 46,5 (khoảng 1,7 lần) và Cb từ 44,9 xuống 22,1. Nghĩa là ở q90, sai số sắc độ quanh chữ đỏ (46,5 cho Cr) vượt xa sai số độ sáng (16,2): tăng quality gần như không cứu được màu loang vì nguyên nhân chính là lấy mẫu 4:2:0, không phải lượng tử. Ở q50 thì sai số độ sáng (ringing) vẫn lớn hơn sai số từng kênh sắc độ. Ngoài vùng cạnh (cách cạnh > 3 px) sai số của nhóm T rất nhỏ (MSE Y 3,8 ở q50, 0,77 ở q90), nên sai số tập trung gần chữ. Điều này gợi ý các thí nghiệm ablation: (a) tắt lấy mẫu sắc độ (4:4:4) cho ảnh có chữ màu, (b) so với WebP ở t04.

### 5. Hạn chế

- Mới đánh giá một cấu hình JPEG (4:2:0, Huffman chuẩn) của một thư viện (Pillow/libjpeg-turbo); kết luận về "JPEG" gắn với cấu hình này.
- Mẫu nhỏ (6–7 ảnh/nhóm), ảnh T và G là ảnh tổng hợp nên chưa đại diện đầy đủ cho ảnh thương mại thật; ảnh nhóm P06 và P07 có nguồn JPEG (đã thu nhỏ) nên có thể mang sẵn dấu vết nén.
- Độ lệch chuẩn tính giữa các ảnh khác kích thước, nên không phản ánh sai số đo.
- PSNR/SSIM không đo khả năng đọc chữ; ngưỡng đọc được của chữ nhỏ (14 px ở ảnh 500×500) cần đánh giá riêng bằng OCR ở phần sau.
- Mọi số ở đây là **mốc cho WebP (t04)**: WebP cần cho SSIM/PSNR tương đương q50–q90 với dung lượng nhỏ hơn các giá trị JPEG ở Bảng 1, và với chế độ không mất mát cần nhỏ hơn PNG (ví dụ trung bình 2,05 lần ở P, 10,2 lần ở T, 2,4 lần ở G nhiễu).
