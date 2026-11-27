# Đường cong tỉ lệ–méo (R–D) và chỉ số Bjøntegaard (BD-rate): WebP so với JPEG

## 1. Mục tiêu

So sánh WebP lossy với JPEG một cách **công bằng**. Tham số `quality` của hai codec không cùng đơn vị (JPEG: hệ số nhân bảng lượng tử hoá IJG; WebP: tham số lượng tử hoá/phân bổ bit của libwebp), nên so sánh "cùng q" không có ý nghĩa. Ví dụ ở q = 75, WebP cho nhóm T ít hơn 48% bit nhưng PSNR cao hơn 1,7 dB (Bảng 3). Cách đúng là so **dung lượng cần để đạt cùng chất lượng**, tức so hai đường cong R–D. BD-rate (Bjøntegaard, VCEG-M33, 2001) tóm tắt việc này trong một con số: phần trăm chênh lệch bitrate trung bình của WebP so với JPEG trên đoạn chất lượng mà hai đường cùng phủ. **Âm nghĩa là WebP tiết kiệm bit hơn.**

## 2. Phương pháp và lý do chọn tham số

**Quét q.** q ∈ {5, 10, 20, 30, 40, 50, 60, 70, 75, 80, 85, 90, 95} trên 20 ảnh, cho JPEG (Pillow mặc định: 4:2:0, bảng Huffman chuẩn, không `optimize`) và WebP lossy (`method=4`), đo bằng `evaluate(..., repeats=0)`. Số liệu thô: `rd_sweep.csv` (520 dòng). Bitrate tính bằng bpp (= 8·byte/số điểm ảnh).

**Công thức BD-rate (cách tính hiện đại).** Với mỗi codec, gọi r = log₁₀(bpp) và nội suy r = f(Q) bằng PCHIP, một nội suy đơn điệu nên không dao động như đa thức bậc 3 của bài gốc. Gọi [Q_lo, Q_hi] là đoạn chất lượng chồng lấn của hai đường. Khi đó:

BD-rate = 10^{ (1/(Q_hi − Q_lo)) · ∫ [ f_WebP(Q) − f_JPEG(Q) ] dQ } − 1  (×100 %).

BD-PSNR (dB) tính đối ngẫu: nội suy Q = g(r) và lấy trung bình hiệu g_WebP − g_JPEG trên đoạn log-rate chồng lấn. Giá trị dương nghĩa là WebP có chất lượng cao hơn ở cùng bitrate. Lấy log-rate vì đường R–D gần tuyến tính theo log(bitrate), và vì chênh lệch cần được biểu diễn dưới dạng tỉ lệ.

**Hai trục chất lượng.** (a) PSNR (dB). (b) SSIM_dB = −10·log₁₀(1 − SSIM). SSIM bị nén trong [0, 1] và tiến sát 1 ở bitrate cao, nên nội suy và tích phân trực tiếp trên SSIM thô sẽ bị chi phối bởi vùng gần 1. Phép đổi dB kéo giãn vùng đó.

**Chọn điểm.** Phép tính chính dùng **6 điểm q ∈ {50, 60, 70, 80, 90, 95}**. Đây là dải trung bình–cao, nơi ảnh sản phẩm thật sự được triển khai, và nằm trong khoảng 4–6 điểm theo thông lệ BD-rate. Ba phân tích độ nhạy được thêm vào: dải thấp {10, 20, 30, 40, 50, 60}, dải cao {70, 75, 80, 85, 90, 95}, và JPEG có `optimize=True` (Huffman tối ưu theo ảnh).

**Kiểm tra hàm** (`bdrate_selftest.csv`, 40 đường R–D thật của JPEG, gồm 20 ảnh × 2 trục): so một đường với chính nó cho BD-rate = 0,000 % (sai số < 10⁻⁹); so với đường dịch bitrate ×0,8 cho −20,000 %. Cả hai được `assert` trong script. Nội suy bậc 3 của bài gốc cho kết quả lệch không quá 0,3 điểm phần trăm so với PCHIP ở trung vị từng nhóm (`main_cubic` trong Bảng 4).

## 3. Kết quả

**Bảng 1. BD-rate của WebP so với JPEG, 6 điểm q 50–95 (trung vị [min, max], %).** Không ảnh nào có BD-rate dương.

| Nhóm (số ảnh) | BD-rate theo PSNR | BD-rate theo SSIM_dB |
|---|---|---|
| P – ảnh chụp nhiều chi tiết (7) | −38,5 [−52,3; −12,6] | −33,4 [−50,1; −10,9] |
| T – ảnh có chữ (7) | −60,2 [−66,4; −52,3] | −61,2 [−69,1; −54,9] |
| G – gradient / nền trơn (6) | −75,3 [−84,4; −67,9] | −69,4 [−84,8; −67,1] |
| Tất cả (20) | −59,4 [−84,4; −12,6] | −60,1 [−84,8; −10,9] |

Số liệu từng ảnh nằm ở `bdrate_per_image.csv`, theo nhóm ở `bdrate_by_group.csv`.

**Bảng 2. BD-PSNR và BD-SSIM_dB (dB, trung vị [min, max]).**

| Nhóm | BD-PSNR | BD-SSIM_dB |
|---|---|---|
| P | +1,99 [0,73; 2,52] | +1,48 [0,54; 1,94] |
| T | +4,39 [4,05; 4,75] | +4,14 [3,97; 4,65] |
| G (chỉ G04–G06) | +0,88 [0,72; 2,11] | +0,09 [0,08; 0,52] |

Với G01–G03 (ảnh sạch) BD-PSNR **không xác định** trong cửa sổ q 50–95. Dải bitrate của WebP (0,05–0,17 bpp ở G01) không giao với dải của JPEG (0,19–0,52 bpp), vì WebP rẻ hơn đến mức hai đường không có bitrate chung. Khi dùng cả 13 điểm q (`bdrate_fullrange_*.csv`), BD-PSNR xác định cho 5 trong 6 ảnh G với trung vị +3,96 dB [2,70; 18,19]. G03 vẫn không xác định. Cũng ở cấu hình 13 điểm, trung vị BD-PSNR là +2,57 dB (P) và +6,28 dB (T). BD-SSIM_dB của G rất nhỏ (≈ 0,1 dB) vì SSIM của nhóm này bão hoà quanh 0,98 ở cả hai codec. Do đó BD-rate theo SSIM_dB ở nhóm G dựa trên đoạn chồng lấn rất hẹp và kém ổn định hơn các nhóm khác.

**Bảng 3. So sánh "cùng q" (trung bình nhóm), thể hiện mức không công bằng của thang q.**

| Nhóm | q | ΔPSNR (WebP − JPEG) | bpp WebP / bpp JPEG |
|---|---|---|---|
| P | 50 / 75 / 90 | +0,60 / +0,16 / +0,74 dB | 0,79 / 0,72 / 0,83 |
| T | 50 / 75 / 90 | +2,88 / +1,66 / +0,80 dB | 0,59 / 0,52 / 0,55 |
| G | 50 / 75 / 90 | +0,60 / −0,19 / −0,48 dB | 0,25 / 0,24 / 0,27 |

**Bảng 4. Độ nhạy của BD-rate theo PSNR (trung vị nhóm, %).**

| Cấu hình | P | T | G |
|---|---|---|---|
| Dải thấp q 10–60 | −38,9 | −62,0 | −79,9 |
| **Chính q 50–95** | **−38,5** | **−60,2** | **−75,3** |
| Dải cao q 70–95 | −37,6 | −59,3 | −72,2 |
| Chính, nội suy bậc 3 | −38,5 | −60,1 | −75,2 |
| Chính, JPEG `optimize=True` | −37,2 | −57,2 | −65,3 |

Kết luận về độ lớn không đổi theo cách chọn điểm hay phương pháp nội suy. Riêng nhóm G, việc bật Huffman tối ưu cho JPEG làm lợi thế của WebP giảm 10 điểm (−75,3 xuống −65,3), tức khoảng 13 % độ lớn của phần chênh đến từ bảng Huffman chuẩn. Phần lớn còn lại đến từ kiến trúc codec (Mục 4).

Hình: `figures/t05/rd_psnr_by_group.png` — Đường R–D (PSNR theo bpp, thang log) trung bình nhóm của JPEG và WebP, đánh dấu q = 50/75/90.
Hình: `figures/t05/rd_ssim_by_group.png` — Như trên với trục SSIM.
Hình: `figures/t05/bdrate_per_image.png` — BD-rate của từng ảnh (trên: PSNR; dưới: SSIM_dB), tô màu theo nhóm, đường 0 đậm.

## 4. Nhận xét và giải thích cơ chế

**WebP có thắng ở mọi ảnh không?** Về BD-rate thì có: cả 20 ảnh và cả hai trục đều âm trong cửa sổ q 50–95 (0/20 dương). Các ảnh thắng ít nhất là **P02_chelsea (−12,6 % PSNR; −10,9 % SSIM_dB)** và **P06_baboon (−26,4 %; −30,5 %)**, đều thuộc nhóm P. Lợi thế của nhóm P nhỏ hơn hẳn nhóm T và G. Chelsea nằm ở vùng PSNR cao nhất của nhóm P (đoạn chồng lấn 36,4–43,3 dB). Baboon có kết cấu lông dày, PSNR thấp nhất nhóm (đoạn chồng lấn 27,9–32,3 dB). Hai ảnh này nằm ở hai đầu của dải mức chi tiết. Cơ chế cho từng ảnh là suy đoán chưa kiểm chứng riêng. Điều chắc chắn là lợi thế co lại khi nội dung có nhiều năng lượng tần số cao, vì khi đó hệ số DCT khác 0 chiếm đa số và phần lợi do dự đoán/mã hoá entropy giảm.

**Nhưng có những vùng WebP không thắng, và chúng nằm ngoài cửa sổ BD-rate:**

1. *Bão hoà chất lượng ở q cao.* BD-rate chỉ đo trên đoạn chồng lấn, nên bỏ qua đoạn chất lượng mà chỉ JPEG đạt tới. Ở q = 95, WebP đạt PSNR thấp hơn JPEG ở 7/20 ảnh (cả 6 ảnh G, và P02). Trung bình nhóm G là 46,4 dB (WebP) so với 47,4 dB (JPEG); riêng G03 chênh 3,2 dB. Ở q = 100 (`saturation_q95_q100.csv`), WebP thấp hơn JPEG ở 13/20 ảnh: P (trung bình −0,95 dB; JPEG 6,5 bpp, WebP 3,6 bpp) và G (−1,68 dB). Đường WebP của nhóm G gần như nằm ngang ở cuối dải: từ q85 lên q95 PSNR chỉ tăng từ 45,3 lên 46,4 dB trong khi bpp tăng 3,6 lần (0,097 lên 0,350; Hình rd_psnr), nên tăng q chỉ tốn thêm bit mà gần như không tăng PSNR. Lợi thế cục bộ cũng co lại: với nhóm G, BD-rate tính riêng trên một phần ba chất lượng cao nhất là −70,7 %, so với −79,0 % ở một phần ba thấp nhất (`bdrate_local_thirds.csv`; nhóm P: −36,7 so với −40,2 %).
2. *Cơ chế của trần PSNR.* Trần này liên quan đến lấy mẫu con sắc độ 4:2:0, mà libwebp lossy luôn dùng. Kiểm chứng trên JPEG q100: với 4:2:0, PSNR trung bình chỉ đạt 38,3 dB (T) và 40,1 dB (P); với 4:4:4 lên 57,3 dB (T) và 51,1 dB (P). Ở nhóm T, WebP q100 (38,30 dB) trùng JPEG q100 4:2:0 (38,30 dB), nên cả hai bị chặn bởi cùng một trần sắc độ (viền chữ cam/đỏ/vàng có sắc độ thay đổi gấp). WebP khác JPEG ở chỗ không có cấu hình 4:4:4 để vượt trần đó. Với nhóm G, chênh lệch còn lớn hơn (WebP 46,7 dB so với JPEG 4:2:0 48,4 dB và 4:4:4 52,6 dB ở q100). Phần trần thêm ngoài sắc độ ở nhóm G chưa được tách riêng; có thể do lượng tử hoá luma và bộ lọc vòng của WebP, nhưng điều này chưa được kiểm chứng.

**Vì sao khoảng cách lớn đến vậy (−38 % đến −75 %)?** Mức này cao hơn con số khoảng 25–35 % thường được trích dẫn cho ảnh chụp (chưa tự đối chiếu ở đây), và có hai lý do đã biết. Thứ nhất, JPEG của Pillow dùng bảng Huffman chuẩn, không trellis và không tối ưu hoá (bật `optimize` giảm lợi thế từ 1 đến 10 điểm, Bảng 4). Thứ hai, ảnh tổng hợp T/G có vùng phẳng rộng. Về kiến trúc, JPEG mã hoá từng khối 8×8 độc lập: mỗi khối luôn trả một hệ số DC sai phân cộng một ký hiệu kết thúc khối, nên có "sàn" bpp. Sàn này thấy rõ ở nhóm G: bpp của JPEG chỉ giảm từ 0,225 (q50) xuống 0,155 (q5), trong khi WebP xuống 0,038. WebP (VP8 intra) dự đoán mỗi khối từ khối lân cận (DC/TM/ngang/dọc), nên vùng phẳng và gradient gần như chỉ còn tốn dư lượng rất nhỏ. Nó cũng dùng mã hoá số học thích nghi theo ngữ cảnh, lượng tử hoá theo phân đoạn, và bộ lọc khử khối trong vòng lặp. Với nhóm T, dự đoán trong ảnh và bộ lọc khử khối hạn chế nhiễu vòng quanh nét chữ, nên cùng bpp WebP đạt PSNR cao hơn đến 2,9 dB ở q50 (Bảng 3).

**Hình dạng đường R–D.** (i) Ở dải trung bình–cao, đường của cả hai codec gần như thẳng theo log(bpp), nên BD-rate gần như không đổi theo cách chọn điểm (Bảng 4, mục chính so với dải cao lệch tối đa 3 điểm (G: −75,3 so với −72,2)). (ii) Câu hỏi "WebP mạnh ở bitrate thấp?" có đáp án có điều kiện: với G, có (−79,9 % ở dải thấp so với −72,2 % ở dải cao, tức mạnh hơn khoảng 8 điểm); với T gần như không đổi (−62,0 so với −59,3 %); với P gần như không đổi (−38,9 so với −37,6 %). Với P, ở q = 5, WebP không dùng ít bit hơn (0,254 so với 0,240 bpp, tức ×1,06) nhưng cao hơn 4,3 dB PSNR. (iii) WebP bão hoà ở q cao (mục 1 ở trên), rõ nhất ở G: PSNR của WebP gần như đứng yên còn JPEG vẫn tăng, nên hai đường tiến lại gần nhau về phía q95.

## 5. Hạn chế

- BD-rate đo PSNR/SSIM trung bình toàn ảnh, **không phản ánh độ đọc được của chữ nhỏ** (nhóm T, đặc biệt ảnh 500 px). Điều đó cần phép đo OCR riêng; lợi thế −60 % ở nhóm T không tự động có nghĩa chữ đọc được ở cùng mức nén.
- Chỉ so ở cấu hình mặc định của Pillow (JPEG chuẩn, WebP `method=4`). Chưa thử mozjpeg, trellis, `method=6` hay các tuỳ chọn WebP khác, nên độ lớn tuyệt đối của BD-rate phụ thuộc cấu hình, trong khi dấu và thứ tự nhóm thì ổn định theo Bảng 4.
- Với G01–G03 hai đường R–D chỉ chồng nhau trên đoạn chất lượng hẹp (4–5 dB) và không chồng nhau về bitrate; BD-PSNR không xác định ở cửa sổ chính. BD-rate theo SSIM_dB của G ít ổn định (ở dải cao 70–95, một ảnh G có giá trị −37,5 % so với trung vị −67,0 %).
- 20 ảnh (7/7/6) là mẫu nhỏ và tổng hợp (T, G), nên trung vị theo nhóm chỉ mang tính mô tả. Ảnh G04–G06 có nhiễu Gauss σ = 1,5 nên PSNR bị chặn quanh 42–44 dB bởi nhiễu.
