# Chương 1. Bài toán và dữ liệu

## 1.1. Mô tả bài toán

Các sàn thương mại điện tử (TMĐT) như Shopee, Lazada lưu và phân phối hàng nghìn ảnh sản phẩm. Nén ảnh quá mạnh làm ảnh mờ, mất chi tiết nhỏ (chữ trong bảng thông số, đường viền), khách hàng khó đánh giá sản phẩm và ít mua hơn. Nén quá nhẹ làm trang tải chậm và khách rời đi. Bài toán là chọn định dạng và mức nén cân bằng giữa hai áp lực này. Đầu vào là 20 ảnh sản phẩm gốc không mất mát (PNG, RGB 8 bit, kích thước 500×500 hoặc 1000×1000). Đầu ra gồm các số đo cho mỗi cấu hình nén (dung lượng KB, PSNR, SSIM, thời gian nén/giải nén) và một bảng khuyến nghị định dạng kèm mức nén theo từng loại ảnh. Người dùng kết quả là nhóm kỹ thuật web của sàn TMĐT, những người cần một quy tắc cấu hình cụ thể cho từng loại ảnh.

## 1.2. Phạm vi

**Thực hiện:** so sánh JPEG, PNG và WebP (có mất mát và không mất mát) trên cùng một bộ ảnh; đo dung lượng, PSNR, SSIM, thời gian nén/giải nén; phân tích lỗi (chi tiết nhỏ, chữ, biên); ablation các tham số của bộ mã hoá (ví dụ chất lượng, chroma subsampling, `method` của WebP); khuyến nghị theo ba nhóm ảnh.

**Không thực hiện:**
- Các định dạng AVIF, JPEG XL, HEIC.
- Thay đổi kích thước ảnh (resize), ảnh đáp ứng nhiều độ phân giải, CDN, cache, đo băng thông mạng thực.
- Đánh giá cảm nhận chủ quan bằng người thật (MOS). Chỉ dùng thước đo khách quan PSNR/SSIM, và OCR để kiểm tra độ đọc được của chữ.
- Huấn luyện bộ nén học sâu.

## 1.3. Giả định

1. Ảnh gốc PNG là tham chiếu không mất mát. Mọi PSNR/SSIM tính giữa ảnh gốc và ảnh sau giải nén. Với hai ảnh P06, P07 điều này chỉ đúng một phần (xem mục 1.4).
2. Mã hoá bằng Pillow 12 với các thư viện mặc định đi kèm (libjpeg-turbo cho JPEG, zlib cho PNG, libwebp cho WebP). Kết quả phụ thuộc phiên bản và tham số mặc định của các thư viện này.
3. Trình duyệt người dùng hiện đại hỗ trợ WebP, nên WebP có thể là định dạng chính. Nếu cần hỗ trợ trình duyệt cũ, phải giữ JPEG/PNG làm phương án dự phòng.
4. Ảnh được xem ở kích thước điểm ảnh gốc (không phóng to), nên suy giảm chi tiết nhỏ có thể nhìn thấy.
5. Thời gian đo trên CPU thông thường, chạy trong bộ nhớ (không tính I/O đĩa).

## 1.4. Mô tả dữ liệu

Bộ dữ liệu gồm 20 ảnh PNG chia thành 3 nhóm, sinh bằng `src/make_dataset.py` (seed 2026). Có 13 ảnh cỡ 500×500 và 7 ảnh cỡ 1000×1000, tổng dung lượng thô 30 029 KB (khoảng 29,3 MB).

- **Nhóm P (7 ảnh, 500×500, ảnh chụp nhiều chi tiết, ảnh thật).** P01–P05 lấy từ `scikit-image` (`coffee`, `chelsea`, `astronaut`, `rocket`, `stereo_motorcycle`, ảnh trái), cắt vuông giữa và thu nhỏ về 500×500 bằng Lanczos. P06 (`baboon.jpg`) và P07 (`fruits.jpg`) lấy từ thư mục mẫu của OpenCV. **Hai ảnh này có nguồn là JPEG**, được thu nhỏ rồi lưu PNG. Vì vậy ảnh "gốc" của chúng đã chịu một lần nén mất mát ở khâu nguồn (dù thu nhỏ làm giảm phần nào vết khối 8×8), và kết quả nén lại của hai ảnh này chịu ảnh hưởng của nén hai lần.
- **Nhóm T (7 ảnh, ảnh có chữ).** T01–T04 cỡ 1000×1000, T05–T07 cỡ 500×500. **Đây là ảnh tổng hợp** mô phỏng thẻ sản phẩm kiểu Shopee: thanh tiêu đề cam, ảnh sản phẩm, giá màu đỏ, nhãn giảm giá đỏ/vàng, bảng thông số chữ tiếng Việt nhỏ (font DejaVu Sans). Ở ảnh 500 px, chữ thông số chỉ cao 14 px, là trường hợp khó cho mọi bộ nén mất mát. Vùng "ảnh sản phẩm" trên thẻ thực chất là ảnh cắt từ chính các ảnh nhóm P (coffee, rocket, astronaut, chelsea, motorcycle), nên nội dung ảnh T và P trùng một phần. Dòng chữ chuẩn nằm trong `data/text_ground_truth.json` để chấm OCR.
- **Nhóm G (6 ảnh, ảnh gradient / nền trơn).** G01–G03 cỡ 1000×1000 sạch; G04–G06 cỡ 500×500 có thêm nhiễu Gauss σ = 1,5 mức xám mô phỏng nhiễu cảm biến. **Đây cũng là ảnh tổng hợp**: nền gradient tuyến tính hoặc xuyên tâm, vật thể (cầu hoặc chai) chiếu sáng kiểu Lambert có phản xạ gương và bóng đổ mềm, làm mờ biên bằng Gauss bán kính 0,6.

**Hạn chế về tính đại diện.** Ảnh T và G không phải ảnh thật crawl từ sàn TMĐT. Chữ vẽ bằng font vector có khử răng cưa nên sạch hơn chữ trên ảnh thật (vốn có nén JPEG sẵn, nhiễu, phối cảnh). Ảnh G không có kết cấu bề mặt thật. Ngoài ra kích thước và nội dung bị gộp lẫn: toàn bộ ảnh nhiễu đều là 500 px còn toàn bộ ảnh sạch đều là 1000 px, nên không thể tách riêng tác động của kích thước khỏi tác động của nhiễu trên bộ này. Chỉ có hai cỡ ảnh, chưa phủ hết các kích thước thực tế. Chúng tôi **khuyến nghị bước tiếp theo thay hoặc bổ sung bằng ảnh thật crawl từ sàn TMĐT** (kiểm tra điều khoản sử dụng và bản quyền) để kiểm chứng các kết luận. Mọi kết luận trong báo cáo chỉ có hiệu lực trên bộ 20 ảnh này.

Hình: `figures/t01/contact_sheet.png` — Lưới 20 ảnh thu nhỏ có nhãn tên, nhóm và kích thước. Viền cam: nhóm T, xanh dương: nhóm P, xanh lá: nhóm G.

## 1.5. Baseline, phương pháp chính và câu hỏi đánh giá

- **Baseline:** JPEG chất lượng 50, 75, 90 (mất mát, DCT 8×8) và PNG (không mất mát, lọc dự đoán + DEFLATE).
- **Phương pháp chính:** WebP, cả chế độ mất mát (dự đoán trong khung kiểu VP8 + biến đổi + lượng tử hoá) và không mất mát (VP8L), so sánh với JPEG và PNG ở cùng điều kiện.
- **Chỉ số:** dung lượng (KB, bpp), PSNR trên RGB, SSIM (Wang 2004, Gauss σ = 1,5), thời gian nén/giải nén (ms).
- **Câu hỏi đánh giá:**
  1. Ở cùng chất lượng (cùng PSNR hoặc SSIM), định dạng nào cho dung lượng nhỏ nhất, và chênh lệch bao nhiêu phần trăm?
  2. Nên chọn PSNR hay SSIM để đánh giá, và vì sao?
  3. Với ảnh có chữ, nén ở mức nào thì vẫn đọc được (đo bằng OCR so với chuẩn)?
  4. Ảnh gradient/nền trơn có nén tốt hơn ảnh nhiều chi tiết thật không, và có hiện tượng vân (banding) hay vết khối không?
  5. Mức nén và định dạng khuyến nghị cho từng nhóm ảnh là gì?

## 1.6. Thống kê dữ liệu

### 1.6.1. Các đặc trưng và vì sao chúng dự báo độ khó nén

Mỗi ảnh được mô tả bằng các đặc trưng tính trực tiếp từ ảnh gốc (`src/t01_dataset_analysis.py`):

- **Entropy Shannon của kênh Y** (bit/pixel), H = −Σ p_k log₂ p_k trên histogram 256 mức của Y = 0,299R + 0,587G + 0,114B. Theo định lý mã hoá nguồn của Shannon, mã hoá entropy không mất mát mà coi các pixel độc lập không thể dùng trung bình ít hơn H bit/pixel. H là chặn dưới của mô hình bậc 0, nên entropy cao nghĩa là ảnh khó nén nếu không khai thác được tương quan không gian. Vì chặn dưới này bỏ qua tương quan giữa các pixel kề nhau, PNG và WebP lossless (dùng bộ dự đoán pixel) có thể đạt dưới H.
- **Entropy của sai khác ngang** Y[x] − Y[x−1] (đặc trưng bổ sung của chúng tôi). Nó xấp xỉ entropy sau bước dự đoán mà bộ lọc PNG và WebP lossless thực hiện, nên phản ánh sát hơn độ khó nén không mất mát.
- **Mật độ biên Canny** (ngưỡng 100/200). Cạnh sắc và chi tiết cục bộ tạo ra sai số dự đoán lớn (nén không mất mát tốn bit) và tạo hệ số DCT lớn ở nhiều tần số (nén mất mát phải giữ hoặc bỏ chúng).
- **Năng lượng tần số cao** (tỉ lệ năng lượng phổ FFT ngoài bán kính 1/4 tần số Nyquist, không tính DC). Biến đổi DCT của JPEG và biến đổi của WebP lossy dồn năng lượng ảnh trơn vào ít hệ số tần số thấp. Hệ số tần số cao nhỏ bị lượng tử hoá về 0 và rất rẻ để mã hoá. Ảnh có nhiều năng lượng cao tần có nhiều hệ số tần số cao lớn, bị lượng tử hoá thô thì sinh méo (nhoè, vòng quanh chữ), còn giữ lại thì tốn bit. Do đó đây là đặc trưng dự báo cho nén mất mát.
- **Số màu phân biệt.** Ảnh ít màu hoặc nền phẳng có nhiều chuỗi lặp mà LZ77/Huffman của DEFLATE khai thác tốt. Nhiễu làm số màu và độ ngẫu nhiên tăng mạnh.
- **Độ lệch chuẩn gradient Sobel.** Đo mức không đồng đều của chi tiết (nền trơn có vài cạnh sắc cho giá trị khác với kết cấu đều).

### 1.6.2. Kết quả theo nhóm

Bảng 1.1. Giá trị trung bình theo nhóm (từ `results/t01/group_means.csv`). Cột "PNG bpp" là kiểm chứng sơ bộ (PNG compress_level = 9), không phải kết quả chính của báo cáo.

| Nhóm | Số ảnh | Dung lượng thô TB (KB) | Entropy Y (bit/px) | Entropy sai khác (bit/px) | Mật độ biên (%) | Năng lượng cao tần (%) | Số màu TB | Std gradient | PNG bpp |
|---|---|---|---|---|---|---|---|---|---|
| P: ảnh chụp chi tiết | 7 | 732 | 7,28 | 4,62 | 9,11 | 8,01 | 119 261 | 9,7 | 12,72 |
| T: ảnh có chữ | 7 | 1988 | 2,92 | 1,54 | 4,07 | 8,01 | 42 861 | 18,4 | 2,48 |
| G: ảnh gradient / nền trơn | 6 | 1831 | 6,68 | 1,77 | 0,37 | 0,61 | 13 503 | 5,1 | 5,21 |

Bảng 1.2. Thống kê từng ảnh (từ `results/t01/dataset_stats.csv`).

| Ảnh | Nhóm | Kích thước | Thô (KB) | Entropy Y | Entropy sai khác | Biên (%) | Cao tần (%) | Số màu | Std grad. | PNG bpp |
|---|---|---|---|---|---|---|---|---|---|---|
| P01_coffee | P | 500×500 | 732 | 7,62 | 4,23 | 5,16 | 2,75 | 85 855 | 9,6 | 12,38 |
| P02_chelsea | P | 500×500 | 732 | 6,91 | 4,52 | 5,14 | 4,50 | 92 812 | 5,1 | 11,52 |
| P03_astronaut | P | 500×500 | 732 | 7,46 | 4,85 | 7,96 | 3,31 | 110 026 | 13,1 | 12,73 |
| P04_rocket | P | 500×500 | 732 | 6,55 | 2,78 | 3,06 | 6,29 | 51 556 | 6,9 | 6,74 |
| P05_motorcycle | P | 500×500 | 732 | 7,72 | 5,22 | 13,51 | 8,42 | 120 157 | 14,4 | 14,34 |
| P06_baboon | P | 500×500 | 732 | 7,36 | 6,31 | 23,52 | 27,54 | 218 650 | 12,6 | 18,71 |
| P07_fruits | P | 500×500 | 732 | 7,36 | 4,47 | 5,43 | 3,25 | 155 768 | 6,5 | 12,63 |
| T01_card1000 | T | 1000×1000 | 2930 | 2,94 | 1,49 | 3,12 | 6,10 | 60 840 | 17,7 | 2,50 |
| T02_card1000 | T | 1000×1000 | 2930 | 2,78 | 1,04 | 2,45 | 4,72 | 35 086 | 16,8 | 1,59 |
| T03_card1000 | T | 1000×1000 | 2930 | 2,88 | 1,49 | 3,35 | 6,04 | 72 742 | 17,2 | 2,37 |
| T04_card1000 | T | 1000×1000 | 2930 | 2,82 | 1,56 | 3,10 | 6,51 | 69 675 | 16,2 | 2,41 |
| T05_card500 | T | 500×500 | 732 | 3,07 | 2,04 | 7,05 | 13,76 | 27 793 | 21,0 | 3,43 |
| T06_card500 | T | 500×500 | 732 | 3,01 | 1,77 | 5,05 | 9,96 | 21 330 | 19,7 | 2,94 |
| T07_card500 | T | 500×500 | 732 | 2,92 | 1,38 | 4,37 | 9,00 | 12 559 | 20,0 | 2,15 |
| G01_studio1000 | G | 1000×1000 | 2930 | 6,89 | 0,53 | 0,20 | 0,25 | 3 181 | 4,1 | 0,81 |
| G02_studio1000 | G | 1000×1000 | 2930 | 6,49 | 1,06 | 0,20 | 0,63 | 2 986 | 3,5 | 0,77 |
| G03_studio1000 | G | 1000×1000 | 2930 | 6,68 | 0,62 | 0,32 | 0,32 | 1 188 | 4,7 | 0,12 |
| G04_studio500_noise | G | 500×500 | 732 | 6,33 | 2,73 | 0,40 | 0,54 | 28 177 | 6,4 | 10,04 |
| G05_studio500_noise | G | 500×500 | 732 | 7,14 | 2,87 | 0,51 | 1,13 | 27 214 | 5,0 | 9,77 |
| G06_studio500_noise | G | 500×500 | 732 | 6,54 | 2,79 | 0,61 | 0,79 | 18 272 | 7,0 | 9,76 |

Hình: `figures/t01/dataset_features.png` — (a) Entropy kênh Y (bit/pixel) so với mật độ biên Canny (%, thang log); (b) năng lượng tần số cao (%, thang log) so với độ lệch chuẩn gradient. Ký hiệu: tròn xanh dương = nhóm P, vuông cam = nhóm T, tam giác xanh lá = nhóm G.

### 1.6.3. Nhận xét

1. **Ba nhóm tách biệt rõ trong không gian đặc trưng.** Nhóm P có entropy cao nhất (6,55–7,72 bit/pixel) và mật độ biên trung bình 9,11 %. Nhóm G có mật độ biên rất thấp (0,20–0,61 %) và năng lượng cao tần chỉ 0,25–1,13 %. Nhóm T có entropy thấp nhất (2,78–3,07 bit/pixel) vì ảnh chỉ có ít mức xám chiếm ưu thế (nền trắng, chữ, các khối màu phẳng), nhưng độ lệch chuẩn gradient cao nhất (16,2–21,0), vì các cạnh chữ rất sắc nằm trên nền phẳng. Điều này khớp với ba loại ảnh mà đề bài yêu cầu khuyến nghị riêng.
2. **Entropy bậc 0 đánh giá sai độ khó nén của nhóm G.** Ảnh G có entropy Y cao (6,49–7,14 bit/pixel, ngang nhóm P) vì gradient mượt trải đều lên nhiều mức xám, nhưng ảnh sạch G01–G03 lại dự đoán rất dễ: entropy sai khác chỉ 0,53–1,06 bit/pixel và PNG đạt 0,12–0,81 bpp. Ngược lại ảnh có nhiễu G04–G06 có entropy sai khác 2,73–2,87 bit/pixel và PNG tốn 9,76–10,04 bpp, tức nhiễu σ = 1,5 (chưa tới 1 % biên độ 255 mức) đi kèm mức PNG cao gấp khoảng 12–81 lần ảnh sạch (so G04–G06 với G01–G03, lưu ý hai nhóm khác kích thước nên đây là so sánh gộp lẫn). Nhiễu cảm biến là chi tiết ngẫu nhiên, không thể dự đoán, nên bộ nén không mất mát phải trả bit cho nó. Nhưng với bộ nén mất mát, nhiễu biên độ nhỏ nằm ở hệ số tần số cao và có thể bị lượng tử hoá bỏ đi. Đây là giả thuyết cần kiểm chứng ở các chương sau, không phải kết luận.
3. **Kiểm chứng sơ bộ (n = 20).** Hệ số tương quan hạng Spearman giữa các đặc trưng và bpp của PNG (`results/t01/correlation.csv`): entropy sai khác 0,98; số màu 0,79; mật độ biên 0,72; entropy Y 0,69; năng lượng cao tần 0,25; độ lệch chuẩn gradient 0,03. Vậy với nén không mất mát, đặc trưng sau dự đoán dự báo tốt nhất, còn entropy bậc 0 chỉ dự báo vừa phải. Năng lượng cao tần và std gradient hầu như không dự báo được PNG, điều này hợp lý vì PNG không dùng biến đổi tần số. Hai đặc trưng này chỉ có ý nghĩa nếu chúng dự báo được độ méo của nén mất mát (JPEG/WebP lossy), và điều đó chưa được kiểm chứng ở chương này. Với cỡ mẫu 20 và các ảnh không độc lập (T chứa lại nội dung P), các hệ số này chỉ mang tính tham khảo.
4. **Ảnh có chữ T nén không mất mát tốt nhưng nhạy với kích thước.** PNG cần 1,59–2,50 bpp ở ảnh 1000 px nhưng 2,15–3,43 bpp ở ảnh 500 px. Bản 500 px có năng lượng cao tần (9,00–13,76 %) và mật độ biên (4,37–7,05 %) cao hơn bản 1000 px (4,72–6,51 % và 2,45–3,35 %) vì chữ cùng nội dung bị thu nhỏ nên cạnh dày đặc hơn trên mỗi pixel. Đây là chiều bất lợi cho nén mất mát: chữ 14 px dễ bị hỏng nhất.
5. **Ngoại lệ trong nhóm P.** P06 (baboon) là ảnh khó nhất trong bộ: mật độ biên 23,52 %, năng lượng cao tần 27,54 % và PNG 18,71 bpp, do lông và râu tạo kết cấu mịn dày đặc. Vì vậy trung bình nhóm P che giấu độ phân tán lớn (mật độ biên 3,06–23,52 %). Hai nhóm P và T có năng lượng cao tần trung bình trùng nhau (8,01 %) chỉ là ngẫu nhiên, vì phân bố khác hẳn (P: 2,75–27,54 %; T: 4,72–13,76 %). P06 và P07 là ảnh nguồn JPEG, nên số liệu của chúng đã chịu ảnh hưởng của lần nén trước.

### 1.6.4. Hạn chế

- Cỡ mẫu nhỏ (20 ảnh, 6–7 ảnh mỗi nhóm) và thang đo chủ yếu là mô tả, chưa kiểm định thống kê.
- Ảnh T và G là tổng hợp; kích thước và nhiễu bị gộp lẫn trong nhóm G (xem mục 1.4).
- Các ngưỡng đặc trưng (Canny 100/200, bán kính 1/4 Nyquist) là lựa chọn quy ước; đổi ngưỡng sẽ đổi giá trị tuyệt đối dù ít đổi thứ tự giữa các nhóm (chưa kiểm tra độ nhạy ngưỡng).
- Entropy tính trên kênh Y, bỏ qua tương quan giữa các kênh màu.
- Cột PNG bpp chỉ dùng để kiểm chứng đặc trưng, với một mức compress_level duy nhất.
