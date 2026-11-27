# Chương 2. Phương pháp: nguyên lý kỹ thuật, chỉ số đánh giá và sơ đồ pipeline

## 2.1. Mục tiêu

Chương này trình bày nguyên lý của ba họ mã hoá được so sánh (JPEG, PNG, WebP lossy/lossless), các chỉ số đo (dung lượng, bpp, tỉ lệ nén, MSE, PSNR, SSIM) và pipeline thí nghiệm. Mục đích là để mọi kết quả ở các chương sau đều giải thích được bằng cơ chế của thuật toán, không coi bộ mã hoá là hộp đen. Phần 2.3 có một ví dụ tính tay JPEG trên một khối 8×8 thật, do script `src/t02_worked_example.py` tự cài bằng numpy/scipy và đối chiếu với libjpeg trong Pillow.

## 2.2. Nguyên lý các kỹ thuật nén

### 2.2.1. JPEG (baseline, mất mát)

Chuỗi xử lý gồm sáu bước.

**(1) Chuyển không gian màu RGB → YCbCr (JFIF/BT.601).** Mắt người nhạy với độ chói hơn sắc độ, nên tách chúng ra để nén sắc độ mạnh hơn:

$$Y=0{,}299R+0{,}587G+0{,}114B,\quad C_b=128-0{,}1687R-0{,}3313G+0{,}5B,\quad C_r=128+0{,}5R-0{,}4187G-0{,}0813B .$$

**(2) Lấy mẫu thưa sắc độ 4:2:0.** Hai kênh $C_b, C_r$ được giảm một nửa theo cả chiều ngang lẫn chiều dọc (trung bình khối 2×2). Số mẫu giảm từ $3WH$ xuống $1{,}5WH$, tức bỏ 50 % dữ liệu trước cả khi biến đổi. Pillow mặc định dùng 4:2:0 (đã kiểm tra bằng `JpegImagePlugin.get_sampling`, kết quả 2; `subsampling=0` cho 4:4:4). Hệ quả: biên màu sắc nét giữa hai màu cùng độ chói, ví dụ chữ giá màu đỏ trên nền trắng, bị "loang màu".

**(3) DCT 8×8.** Mỗi kênh được chia thành khối 8×8, trừ 128 (đưa về $[-128,127]$) rồi biến đổi DCT-II hai chiều trực giao:

$$F(u,v)=\tfrac14 C(u)C(v)\sum_{x=0}^{7}\sum_{y=0}^{7} f(x,y)\cos\frac{(2x+1)u\pi}{16}\cos\frac{(2y+1)v\pi}{16},\qquad C(0)=\tfrac{1}{\sqrt2},\; C(k>0)=1 .$$

Dưới dạng ma trận, $F=C\,f\,C^{\top}$ với $C$ trực giao ($CC^\top=I$), nên biến đổi bảo toàn năng lượng (Parseval) và không gây mất mát. $F(0,0)$ là hệ số DC, bằng 8 lần giá trị trung bình khối. Với ảnh tự nhiên, năng lượng tập trung ở tần số thấp, nên các hệ số tần số cao nhỏ và dễ loại bỏ.

**(4) Lượng tử hoá, bước duy nhất gây mất mát chính.** Mỗi hệ số được chia cho một bước lượng tử $Q'(u,v)$ rồi làm tròn: $F_q=\operatorname{round}(F/Q')$. Bảng $Q'$ lấy từ bảng luminance chuẩn $Q$ (ITU-T T.81, Annex K) nhân hệ số tỉ lệ theo `quality` $q$ (công thức của IJG/libjpeg):

$$S=\begin{cases}5000/q, & q<50\\ 200-2q, & q\ge 50\end{cases}\qquad Q'(u,v)=\operatorname{clip}\!\Big(\Big\lfloor \tfrac{Q(u,v)\,S+50}{100}\Big\rfloor,\,1,\,255\Big).$$

Vậy $q=50$ cho $S=100$ (bảng gốc), $q=75$ cho $S=50$ (bước lượng tử giảm một nửa), $q=90$ cho $S=20$ (bước chỉ còn một phần năm) và $q=100$ cho $S=0$ (mọi bước bằng 1). Bảng $Q$ có bước lớn ở tần số cao (đến 121) vì mắt kém nhạy ở đó (Hình: `figures/t02/jpeg_qtable_scale.png` — Hệ số tỉ lệ $S$ theo quality $q$ từ 1 đến 99, thang log; $q=100$ cho $S=0$). Ta đã kiểm tra bảng $Q'$ tự tính trùng từng phần tử với bảng libjpeg mà Pillow ghi vào tệp, cho $q=1, 10, 25, 49, 50, 75, 90, 95, 99, 100$.

**(5) Quét zigzag, RLE.** 63 hệ số AC được đọc theo đường zigzag từ tần số thấp đến cao để các số 0 nằm liền nhau ở cuối. Chuỗi được mã hoá thành các cặp (số 0 đứng trước, giá trị) và kết thúc bằng ký hiệu EOB. Hệ số DC được mã hoá theo hiệu với DC của khối trước (DPCM).

**(6) Mã hoá entropy Huffman.** Mỗi cặp (run, size) và hiệu DC được mã bằng bảng Huffman. Pillow mặc định `optimize=False` nên dùng bảng chuẩn Annex K. Việc tối ưu bảng hoặc dùng progressive có thể cho dung lượng nhỏ hơn mà không đổi chất lượng, và là một hướng ablation.

**Nguồn gốc lỗi.** *Hiện tượng khối (blocking)*: mỗi khối được lượng tử độc lập nên giá trị trung bình (DC) của hai khối kề nhau lệch nhau, tạo lưới 8×8 nhìn thấy được, rõ nhất ở vùng gradient mịn và $q$ thấp. *Hiện tượng vòng (ringing)*: lượng tử thô làm mất hoặc sai số các hệ số tần số cao cần để dựng biên sắc, nên quanh biên chữ xuất hiện dao động kiểu Gibbs. Ví dụ ở 2.3, khối chữ ở $q=50$ có điểm gốc 40 bị khôi phục thành 19 (sai số 21). Hai lỗi này đều xuất hiện ở mọi ảnh JPEG, nhưng ảnh chữ chịu ảnh hưởng nặng nhất vì biên sắc và chi tiết nhỏ.

### 2.2.2. PNG (không mất mát)

PNG gồm hai giai đoạn. *Giai đoạn 1: bộ lọc dự đoán theo hàng.* Với mỗi hàng, một trong năm bộ lọc được chọn (ghi 1 byte đầu hàng), và byte $x$ được thay bằng phần dư mod 256 so với dự đoán từ ba điểm lân cận: $a$ (trái), $b$ (trên), $c$ (chéo trái-trên).

| Bộ lọc | Dự đoán | Bộ lọc | Dự đoán |
|---|---|---|---|
| None | 0 | Average | $\lfloor (a+b)/2\rfloor$ |
| Sub | $a$ | Paeth | trong $\{a,b,c\}$ chọn giá trị gần $p=a+b-c$ nhất |
| Up | $b$ | | |

Bộ lọc Paeth tính $p=a+b-c$ rồi chọn trong $a,b,c$ giá trị có $|p-\cdot|$ nhỏ nhất (hoà thì ưu tiên $a$, rồi $b$, rồi $c$). Phần mềm mã hoá thường chọn bộ lọc theo heuristic tổng $|{\rm residual}|$ nhỏ nhất cho từng hàng. *Giai đoạn 2: DEFLATE* (RFC 1951) = LZ77 (tìm chuỗi byte lặp trong cửa sổ trượt 32 KB, thay bằng cặp (độ dài 3–258, khoảng cách)) + mã Huffman động cho ký tự và cặp đó. Tham số `compress_level` (0–9) của Pillow chỉ điều khiển mức nỗ lực tìm chuỗi lặp, không đổi ảnh giải mã.

*Vì sao không mất mát:* bộ lọc là phép trừ modulo 256 (khả nghịch hoàn toàn) còn DEFLATE là nén không mất mát, nên giải mã cho ảnh y hệt bản gốc (PSNR = ∞). *Vì sao kém với ảnh chụp có nhiễu:* bộ lọc chỉ thu được số 0 khi các điểm lân cận gần giống nhau. Với ảnh phẳng hoặc chữ trên nền trơn, phần dư gần như toàn số 0 và LZ77 bắt được các chuỗi lặp. Trên chính khối chữ ở 2.3, bộ lọc Up và Paeth cho 44/64 và 51/64 byte bằng 0, trong khi Average chỉ cho 22/64 (`results/t02/png_filter_block.csv`). Với nhiễu cảm biến, phần dư là ngẫu nhiên và chuỗi lặp gần như không tồn tại, nên chỉ còn lại lợi ích của Huffman. Ước lượng giải tích: nhiễu Gauss $\sigma=1{,}5$ (nhóm G04–G06) làm phần dư sau lọc Sub/Up có phương sai $2\sigma^2=4{,}5$, tức entropy $h=\tfrac12\log_2(2\pi e\cdot 4{,}5)\approx 3{,}13$ bit/mẫu ≈ 9,4 bpp. Chỉ riêng nhiễu đã chặn tỉ lệ nén PNG ở khoảng 2,6:1, chưa kể cấu trúc ảnh. Đây là ước lượng lý thuyết, số đo thực nghiệm nằm ở Chương 3.

### 2.2.3. WebP lossy (VP8 intra, mất mát)

WebP lossy là khung hình khoá (key frame) của codec video VP8 (RFC 6386), nên có cấu trúc dự đoán–biến đổi–lượng tử như video nhưng chỉ dùng dự đoán trong khung.

1. **Không gian màu:** luôn YUV 4:2:0, 8 bit (libwebp đổi RGB→Y'CbCr theo BT.601, dải 16–235). Không có tuỳ chọn 4:4:4, nên màu bão hoà bị loang tương tự JPEG.
2. **Dự đoán trong khung theo khối:** ảnh chia thành macroblock 16×16. Mỗi macroblock chọn dự đoán 16×16 với 4 mode (DC, V, H, TM), hoặc chia 16 khối 4×4 với 10 mode (B_DC, B_TM, B_VE, B_HE, B_LD, B_RD, B_VR, B_VL, B_HD, B_HU). Chroma dùng khối 8×8 với 4 mode DC/V/H/TM. DC lấy trung bình điểm lân cận, V/H chép hàng trên hoặc cột trái, TM (TrueMotion) dự đoán $\hat{x}=L+A-P$ (trái + trên − chéo) có cắt ngưỡng. Chỉ phần dư (gốc trừ dự đoán) mới được biến đổi, nên vùng mịn, biên thẳng cần ít bit hơn JPEG, vốn không có dự đoán giữa các khối ngoài DPCM của DC.
3. **Biến đổi:** DCT nguyên 4×4 (xấp xỉ DCT bằng số nguyên, tính chính xác và nhanh, không có sai lệch giữa bộ mã/giải mã). Với macroblock dự đoán 16×16, 16 hệ số DC của 16 khối 4×4 được gộp lại và biến đổi thêm bằng Walsh–Hadamard 4×4 (WHT) để khai thác tương quan giữa các DC.
4. **Lượng tử hoá thích nghi theo segment:** các macroblock được phân tối đa 4 segment theo độ phức tạp; mỗi segment có bước lượng tử và cường độ lọc riêng, nên vùng phẳng (dễ thấy lỗi) được ưu tiên giữ chất lượng hơn vùng nhiều chi tiết. JPEG dùng một bảng duy nhất cho toàn ảnh.
5. **Mã hoá số học nhị phân (boolean arithmetic coder):** mỗi hệ số được chia thành chuỗi quyết định nhị phân theo cây token, mỗi quyết định mã bằng xác suất 8 bit chọn theo ngữ cảnh (loại khối, vị trí tần số, số hệ số khác 0 ở khối trái/trên). Bảng xác suất được tính trước và gửi trong header khung hình. Mã số học cho phép dùng số bit không nguyên cho mỗi ký hiệu, nên hiệu quả hơn Huffman (mỗi ký hiệu tối thiểu 1 bit).
6. **Bộ lọc vòng (loop filter):** bộ lọc làm trơn trên biên khối 4×4 và 16×16 với cường độ phụ thuộc segment, nhằm khử hiệu ứng khối. Vì dự đoán trong khung dùng điểm ảnh chưa lọc, với ảnh tĩnh nó hoạt động như bộ lọc hậu xử lý nằm trong chuẩn. Đổi lại, bộ lọc làm mờ nhẹ biên thật, nên chữ nhỏ bị mờ hơn.

Tổng hợp, WebP lossy tốt hơn JPEG nhờ ba yếu tố: dự đoán trong khung, mã hoá số học và lọc khối. Giá phải trả là chữ nhỏ dễ bị làm mờ hơn do loop filter và 4:2:0 bắt buộc.

### 2.2.4. WebP lossless (VP8L)

VP8L là một codec riêng, không dùng DCT, gồm các biến đổi thuận nghịch rồi mã hoá entropy:

- **Biến đổi dự đoán** (predictor): ảnh chia khối $2^k\times2^k$; mỗi khối chọn một trong 14 mode (lân cận, trung bình, gradient...), chỉ lưu phần dư. Đây là bản mở rộng của bộ lọc PNG với chọn mode theo khối và không chỉ theo hàng.
- **Biến đổi màu** (cross-color) và **subtract green**: trừ kênh G khỏi R và B (và có thể điều chỉnh R/B theo G) để khử tương quan giữa các kênh. Trong ảnh tự nhiên R, G, B tương quan mạnh, nên phần dư R−G, B−G nhỏ và dễ nén.
- **Color indexing** (bảng màu) cho ảnh ít màu, gộp nhiều điểm ảnh vào một byte.
- **LZ77 + color cache + Huffman thích nghi:** mỗi điểm ảnh được mã bằng một trong ba cách: ARGB nguyên, tham chiếu lùi (độ dài, khoảng cách, trong đó khoảng cách được ánh xạ theo lân cận 2D), hoặc chỉ số trong bộ nhớ đệm màu (băm màu gần đây) cho thẻ sản phẩm có ít màu lặp lại. Mã Huffman được chọn riêng theo vùng ảnh (entropy image), tức thích nghi theo nội dung, nên thường nhỏ hơn PNG.

Trong Pillow, tham số `quality` của chế độ `lossless=True` không phải độ trung thực mà là mức nỗ lực nén (cao hơn: chậm hơn, nhỏ hơn), còn ảnh giải mã luôn trùng gốc. Phiên bản thư viện dùng để đo: Pillow 12.3.0, libwebp 1.6.0, libjpeg-turbo 3.1.4, và nén zlib-ng 1.3.1 cho PNG (zlib-ng khác zlib cổ điển ở thuật toán tìm chuỗi lặp, nên dung lượng PNG có thể khác vài phần trăm so với máy khác).

## 2.3. Ví dụ tính tay JPEG trên khối 8×8 thật

Khối được lấy từ kênh Y của `T01_card1000.png` tại $(y,x)=(776,256)$, trên dòng chữ "Chống nước IPX4" (chọn khối căn lưới 8×8 có độ lệch chuẩn lớn nhất trong vùng dòng chữ, std = 99,58), tức là trường hợp khó của DCT. Khối chứa nét đứng, nét ngang và nền, với giá trị từ 40 đến 255:

| | c0 | c1 | c2 | c3 | c4 | c5 | c6 | c7 |
|---|---|---|---|---|---|---|---|---|
| h0–h4 (mỗi hàng giống nhau) | 255 | 255 | 218 | 40 | 40 | 174 | 255 | 255 |
| h5, h6 | 40 | 40 | 40 | 40 | 40 | 40 | 40 | 40 |
| h7 | 255 | 255 | 218 | 40 | 40 | 174 | 255 | 255 |

Sau khi trừ 128 và áp DCT-II chuẩn trực giao, hệ số DC là $F(0,0)=175{,}0=8\times 21{,}875$ (21,875 là trung bình khối đã trừ 128). Tổng bình phương hệ số bằng tổng bình phương điểm ảnh (665 224, Parseval), đúng với tính trực giao. Hàng $u=2$ và $u=6$ bằng 0 chính xác vì khối có dạng $f=-88+I(y)\,s(x)$ với $I(y)$ là hàm chỉ thị của các hàng 0–4 và 7, mà $\sum_y I(y)\cos\frac{(2y+1)2\pi}{16}=0$. Góc 4×4 trên-trái của ma trận $F$ (đơn vị: mức xám):

| $F(u,v)$ | v=0 | v=1 | v=2 | v=3 |
|---|---|---|---|---|
| u=0 | 175,0 | 25,9 | 469,3 | −45,8 |
| u=1 | 287,4 | 8,5 | 153,4 | −15,0 |
| u=2 | 0,0 | 0,0 | 0,0 | 0,0 |
| u=3 | −243,6 | −7,2 | −130,1 | 12,7 |

Chia cho bảng lượng tử và làm tròn. Với $q=50$ ($S=100$, bảng gốc), ví dụ $F(0,2)=469{,}3$, $Q'=10$ cho $46{,}93\to47$; giải lượng tử $47\times10=470$ (sai số 0,7). $F(0,5)=9{,}1$, $Q'=40$ cho $0{,}23\to0$: hệ số tần số cao bị xoá hẳn. Ma trận $F_q$ đầy đủ ở $q=50$:

| $F_q$ (q=50) | v=0 | v=1 | v=2 | v=3 | v=4 | v=5 | v=6 | v=7 |
|---|---|---|---|---|---|---|---|---|
| u=0 | 11 | 2 | 47 | −3 | −10 | 0 | 1 | 1 |
| u=1 | 24 | 1 | 11 | −1 | −3 | 0 | 0 | 0 |
| u=2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| u=3 | −17 | 0 | −6 | 0 | 1 | 0 | 0 | 0 |
| u=4 | 16 | 0 | 4 | 0 | −1 | 0 | 0 | 0 |
| u=5 | −7 | 0 | −2 | 0 | 1 | 0 | 0 | 0 |
| u=6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| u=7 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

Ở $q=90$ ($S=20$, bảng $Q'$ có phần tử từ 2 đến 24), góc trên-trái của $F_q$ là (58, 13, 235, −15 / 144, 4, 51, −4 / 0, 0, 0, 0 / −81, −2, −33, 2), với 37 hệ số khác 0. Kết quả cho khối này (từ `results/t02/worked_example.txt`):

| quality | S | hệ số ≠ 0 (trong 64) | cặp (run, level) của AC | MSE | PSNR (dB) | SSIM khối |
|---|---|---|---|---|---|---|
| 50 | 100 | 22 | 21 + EOB | 90,27 | 28,58 | 0,9955 |
| 90 | 20 | 37 | 36 + EOB | 5,64 | 40,62 | 0,9997 |


Hình: `figures/t02/dct_example.png` — Khối Y gốc 8×8, hệ số DCT, hệ số sau lượng tử hoá q=50 và q=90, và khối khôi phục tương ứng (PSNR 28,6 dB và 40,6 dB).

Ở $q=50$ sai số lớn nhất là 28 mức xám và nằm quanh nét chữ (ringing), còn ở $q=90$ sai số lớn nhất chỉ 7. Giảm quality từ 90 xuống 50 làm số hệ số khác 0 giảm từ 37 xuống 22 (tức chuỗi RLE ngắn hơn, ít bit hơn) với giá là mất 12,0 dB PSNR. Lưu ý SSIM khối (một cửa sổ, trọng số đều) rất gần 1 ngay cả ở $q=50$ vì phương sai tín hiệu của khối rất lớn (≈ 9 900) so với phương sai sai số (≈ 90), trong khi PSNR chỉ đạt 28,6 dB; hai chỉ số có thang đo khác nhau và không thể so trực tiếp giá trị (xem 2.4). Số liệu này chỉ mô phỏng DCT và lượng tử hoá trên kênh Y của một khối. Libjpeg còn thêm chuyển màu, 4:2:0 và mã hoá entropy, nên số liệu cả ảnh (Chương 3) sẽ khác.

## 2.4. Các chỉ số đánh giá

**Dung lượng, bpp, tỉ lệ nén.** Với ảnh $W\times H$ và tệp $B$ byte: dung lượng $=B/1024$ (KB); $\mathrm{bpp}=8B/(WH)$; tỉ lệ nén $\mathrm{CR}=3WH/B=24/\mathrm{bpp}$ (so với RGB 24 bit thô). bpp cho phép so sánh giữa ảnh 500² và 1000².

**MSE và PSNR.** Với ảnh gốc $x$ và ảnh giải mã $y$ ($N=3WH$ mẫu, $L=255$):

$$\mathrm{MSE}=\frac1N\sum_i (x_i-y_i)^2,\qquad \mathrm{PSNR}=10\log_{10}\frac{L^2}{\mathrm{MSE}}\ \text{(dB)} .$$

Ví dụ tính tay: hai khối 3×3 $x=\begin{bmatrix}52&55&61\\68&70&66\\63&59&55\end{bmatrix}$, $y=\begin{bmatrix}50&56&60\\70&72&62\\61&60&57\end{bmatrix}$ có tổng bình phương sai số $4+1+1+4+4+16+4+1+4=39$, nên $\mathrm{MSE}=39/9=4{,}333$ và $\mathrm{PSNR}=10\log_{10}(65025/4{,}333)=41{,}76$ dB. MSE giảm một nửa thì PSNR tăng $10\log_{10}2=3{,}01$ dB. $\mathrm{PSNR}=30$ dB ứng với $\mathrm{MSE}=65{,}0$ và 40 dB ứng với $6{,}50$. Với ảnh trùng khớp, $\mathrm{MSE}=0$ nên PSNR $=\infty$ (trường hợp PNG và WebP lossless).

**SSIM** (Wang và cs., 2004) so sánh độ sáng, tương phản và cấu trúc trong từng cửa sổ cục bộ:

$$\mathrm{SSIM}(x,y)=\frac{(2\mu_x\mu_y+C_1)(2\sigma_{xy}+C_2)}{(\mu_x^2+\mu_y^2+C_1)(\sigma_x^2+\sigma_y^2+C_2)},\quad C_1=(0{,}01L)^2=6{,}5025,\ C_2=(0{,}03L)^2=58{,}5225 .$$

Trong đó $\mu_x=\sum_i w_i x_i$, $\sigma_x^2=\sum_i w_i(x_i-\mu_x)^2$, $\sigma_{xy}=\sum_i w_i(x_i-\mu_x)(y_i-\mu_y)$, và $w_i$ là trọng số Gauss $\sigma=1{,}5$ (chuẩn hoá $\sum w_i=1$). Cài đặt skimage dùng ở `common.py` có `gaussian_weights=True`, `sigma=1.5`, `use_sample_covariance=False`: cửa sổ hiệu dụng 11×11, bỏ viền 5 điểm ảnh, tính trên từng kênh RGB rồi lấy trung bình. Hằng $C_1, C_2$ tránh chia cho 0 ở vùng phẳng. Công thức trên là tích hai thành phần $l\cdot cs$ với $l=\frac{2\mu_x\mu_y+C_1}{\mu_x^2+\mu_y^2+C_1}$ (độ sáng) và $cs=\frac{2\sigma_{xy}+C_2}{\sigma_x^2+\sigma_y^2+C_2}$ (tương phản và cấu trúc).

Ví dụ tính tay (một cửa sổ, thống kê toàn khối của hai khối 3×3 ở trên): $\mu_x=61{,}000$, $\mu_y=60{,}889$, $\sigma_x^2=35{,}111$, $\sigma_y^2=40{,}765$, $\sigma_{xy}=35{,}778$. Từ đó $l=0{,}999998$, $cs=(71{,}556+58{,}523)/(35{,}111+40{,}765+58{,}523)=0{,}96785$, nên $\mathrm{SSIM}=0{,}96785$, trùng `skimage.structural_similarity(win_size=3)` đến 6 chữ số.

| | PSNR | SSIM |
|---|---|---|
| Ưu điểm | đơn giản, có ý nghĩa vật lý (năng lượng sai số), chuẩn hoá rộng rãi, rẻ để tính, đơn điệu theo bit-rate | gần cảm nhận hơn: nhạy với mất cấu trúc (làm mờ, mất biên), chuẩn hoá về [−1, 1] |
| Nhược điểm | tính từng điểm ảnh, bỏ qua cấu trúc không gian; hai ảnh cùng MSE có thể trông rất khác nhau; một chữ bị mờ ít điểm ảnh gần như không làm giảm PSNR của cả ảnh; bằng ∞ khi lossless | phụ thuộc kích thước cửa sổ và $C_1,C_2$; kém nhạy với lệch màu đều và nhiễu nhỏ ở vùng sáng/tối; không phải metric (không có bất đẳng thức tam giác); trung bình toàn ảnh che mất lỗi cục bộ ở chữ; không đo khả năng đọc chữ |

Do cả hai đều có điểm yếu với ảnh chữ, các phần sau báo cáo đồng thời PSNR và SSIM, và bổ sung thước đo trực tiếp là độ chính xác OCR cho nhóm ảnh T. Không dùng một chỉ số đơn lẻ để kết luận. Câu hỏi "nên chọn PSNR hay SSIM" được trả lời bằng số liệu ở chương kết luận.

## 2.5. Sơ đồ pipeline thí nghiệm

Hình: `figures/t02/pipeline.png` — Sơ đồ khối pipeline thí nghiệm: đầu vào, tiền xử lý, xử lý chính, hậu xử lý, đầu ra. Bước 3–4 lặp cho mọi cặp (ảnh, định dạng, tham số).

| Bước | Hàm (thư viện) | Tham số | Lý do chọn |
|---|---|---|---|
| 1. Đầu vào | `common.list_images()` (Pillow `Image.open`) | 20 ảnh PNG: P (7 ảnh chụp, 500²), T (7 thẻ có chữ; 4 ảnh 1000², 3 ảnh 500²), G (6 ảnh gradient; 3 ảnh 1000² sạch, 3 ảnh 500² nhiễu σ=1,5) | gốc PNG không mất mát nên dùng làm tham chiếu để tính PSNR/SSIM; ba nhóm đại diện ba loại nội dung cần khuyến nghị riêng |
| 2. Tiền xử lý | `Image.convert('RGB')`; cắt vuông chính giữa và `Image.resize(..., Image.LANCZOS)` cho các ảnh chụp nguồn (thực hiện một lần khi tạo dữ liệu, `src/make_dataset.py`, seed 2026) | RGB 8 bit/kênh, kích thước 500² hoặc 1000² | chuẩn hoá về cùng định dạng (bỏ kênh alpha, tránh khác biệt do chế độ ảnh); Lanczos giữ độ sắc nét và ít răng cưa khi thu nhỏ; seed cố định để tái lập |
| 3. Xử lý chính | `common.encode` = `Image.save(BytesIO, ...)` (libjpeg-turbo, zlib-ng, libwebp) | JPEG `quality`=50, 75, 90 (4:2:0 mặc định); PNG `compress_level`=9; WebP lossy `quality`=Q, `method`=4; WebP lossless `lossless=True, quality=100, method=4` | JPEG 50/75/90 là baseline theo đề; PNG mức 9 cho dung lượng nhỏ nhất, không ảnh hưởng chất lượng; `method=4` là mặc định cân bằng tốc độ và nén của libwebp (0–6); mã hoá trong bộ nhớ để không phụ thuộc đĩa |
| 4. Hậu xử lý | `common.decode` (`Image.open`, `load`, `convert('RGB')`); `common.psnr` (numpy); `common.ssim` (`skimage.metrics.structural_similarity`); `common.evaluate` | PSNR: MSE trung bình 3 kênh RGB, $L=255$; SSIM: `channel_axis=2, gaussian_weights=True, sigma=1.5, use_sample_covariance=False`; KB $=B/1024$, bpp, tỉ lệ nén; tổng hợp trung bình theo nhóm P/T/G | cùng một hàm đo cho mọi phần nên số liệu nhất quán; cài đặt SSIM đúng bản gốc Wang 2004; đo trên RGB (cái người dùng thấy) thay vì chỉ kênh Y |
| 5. Đầu ra | `pandas.to_csv`, `matplotlib` (300 dpi) | bảng CSV, đồ thị RD (dung lượng/bpp theo PSNR hoặc SSIM), bảng khuyến nghị theo nhóm | RD là cách chuẩn so sánh codec công bằng: so dung lượng tại cùng chất lượng, thay vì cùng giá trị tham số `quality` (không có cùng nghĩa giữa JPEG và WebP) |

Điểm cần lưu ý về công bằng: `quality` của JPEG và của WebP là hai thang khác nhau, nên so sánh phải dựa trên đường RD (dung lượng so với PSNR/SSIM) chứ không phải cùng giá trị `quality`. Thời gian mã hoá/giải mã chỉ đo ở các thí nghiệm riêng, chạy tuần tự để tránh nhiễu.

## 2.6. Hạn chế của phần này

(i) Ví dụ tính tay chỉ minh hoạ kênh Y của một khối, chưa gồm 4:2:0 và mã hoá entropy, nên không dùng để suy ra dung lượng cả ảnh. (ii) Mô tả VP8/VP8L dựa trên đặc tả (RFC 6386, tài liệu WebP Lossless Bitstream); Pillow không phơi bày các tham số nội bộ của libwebp (segment, strength của loop filter) nên không thể ablation riêng từng thành phần ở mức này, chỉ có thể so sánh qua `quality` và `method`. (iii) Ước lượng entropy của PNG trên ảnh nhiễu là giải tích, chưa kiểm chứng ở đây. (iv) Khối minh hoạ được chọn là khối có tương phản cao nhất của dòng chữ, nên cho thấy trường hợp xấu, không đại diện cho mọi khối.

**Tài liệu tham khảo (chương 2).** G. K. Wallace, "The JPEG still picture compression standard", *IEEE Trans. Consumer Electron.*, 1992; ITU-T T.81 (JPEG), Annex K; ISO/IEC 15948 (PNG) và RFC 1951 (DEFLATE); J. Bankoski và cs., RFC 6386 (VP8); Google, *WebP Lossless Bitstream Specification*; Z. Wang và cs., "Image quality assessment: from error visibility to structural similarity", *IEEE Trans. Image Process.*, 13(4), 2004.
