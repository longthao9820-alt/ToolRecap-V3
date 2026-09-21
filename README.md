# Hướng dẫn sử dụng ToolRecap V3

ToolRecap V3 là ứng dụng Windows Portable giúp tự động tóm tắt và dựng video recap từ video nguồn bằng trí tuệ nhân tạo (AI Gateway) và lồng tiếng tự động (VoiceStudio).

---

## 1. Cách mở ứng dụng

Bạn có thể mở ứng dụng bằng một trong hai cách rất đơn giản bằng chuột, không cần gõ bất kỳ câu lệnh nào:

- **Cách 1 (Khuyên dùng - Thư mục chạy ngay):**
  Vào thư mục [dist/ToolRecapV3](dist/ToolRecapV3) và nhấp đúp chuột vào tệp:
  `ToolRecapV3.exe`

- **Cách 2 (Bản nén phát hành):**
  Mở thư mục [release](release), giải nén tệp [ToolRecapV3-v3.0.1-windows-portable.zip](release/ToolRecapV3-v3.0.1-windows-portable.zip) ra bất kỳ đâu (ví dụ Desktop), rồi nhấp đúp vào `ToolRecapV3.exe` bên trong.

> **Ghi chú:** Ứng dụng đã tích hợp sẵn FFmpeg, FFprobe và bộ kiểm tra hợp lệ, không cần cài đặt thêm Python hay phần mềm phụ trợ bên ngoài.

---

## 2. Dịch vụ bên ngoài cần chuẩn bị (External Services)

Trước khi bấm bắt đầu tạo recap, hãy đảm bảo hai dịch vụ sau đang hoạt động:

1. **AI Gateway (9router):**
   - Dịch vụ cần chạy tại địa chỉ mặc định `http://127.0.0.1:20128`.
   - Model mặc định: `ag/gemini-3.8-flash` (yêu cầu model hỗ trợ nhận diện video).
   - Nhập API key trong cửa sổ **Cài đặt -> 1. AI Gateway**.

2. **VoiceStudio (Tạo giọng đọc):**
   - Chế độ Local: Chạy dịch vụ VoiceStudio tại `http://127.0.0.1:3900`.
   - Chế độ Remote: Cấu hình địa chỉ mạng riêng Tailscale (ví dụ `https://<tên-máy>.ts.net:8443`) kèm khóa xác thực nếu có.

---

## 3. Cách sử dụng (Quy trình 1 chạm A–Z)

1. **Khởi động ứng dụng:** Nhấp đúp chuột vào `ToolRecapV3.exe`. Giao diện chính sẽ hiện lên.
2. **Chọn video nguồn:**
   - Bấm nút **"Chọn tệp"** nếu bạn chỉ muốn tóm tắt 1 video tập phim.
   - Bấm nút **"Chọn thư mục"** nếu bạn muốn tóm tắt nhiều tập trong cùng một thư mục. Ứng dụng sẽ tự động sắp xếp các tập theo thứ tự tự nhiên (tập 1 đến tập 10...) và chỉ lấy các tệp video trực tiếp trong thư mục đó, không quét lộn xộn các thư mục con bên trong.
3. **Kiểm tra Cài đặt & Nhập Kịch bản (BẮT BUỘC):**
   - Bấm nút **"⚙ Cài đặt"** ở góc trên bên phải.
   - **Tab 1 (AI Gateway):** Kiểm tra địa chỉ `http://127.0.0.1:20128` và điền API key.
   - **Tab 2 (Kịch bản - Prompt) — BẮT BUỘC:** Nhập chỉ dẫn kịch bản bạn muốn AI tóm tắt (ví dụ: yêu cầu nội dung tập trung vào tình tiết nào, nhân vật nào, phong cách lời bình ra sao). *Lưu ý: Kịch bản là bắt buộc; các cơ chế xử lý ngoại lệ hình ảnh (visual exceptions), scanner, finalizer và bộ tự sửa lỗi (heuristic repair) của V2 đã hoàn toàn vắng mặt/bị loại bỏ. Phần mềm không tự ý chắp vá hay biên tập lại kịch bản nếu để trống.*
   - **Tab 3 (Giọng đọc):** Chọn giọng đọc (`alloy`, ...) và ngôn ngữ (`vi`, `en-US`, ...).
   - Bấm nút **"Lưu cài đặt"** để hoàn tất cấu hình.
4. **Bắt đầu tạo video recap:**
   - Bấm nút **"BẮT ĐẦU"**.
   - Ứng dụng sẽ tự động thực hiện toàn bộ quy trình: gửi video sang AI Gateway phân tích -> tạo kịch bản Final JSON -> lưu kịch bản vào ổ đĩa -> gọi VoiceStudio tạo giọng đọc -> cắt ghép video và trộn âm thanh bằng FFmpeg -> xuất ra video hoàn chỉnh.
5. **Nhận kết quả:**
   - Bạn có thể thu nhỏ cửa sổ để làm việc khác. Khi hoàn tất, Windows sẽ hiện thông báo góc màn hình và phát âm thanh báo hiệu.
   - Bấm nút **"Mở thư mục xuất"** trên giao diện để mở ngay thư mục chứa các video recap đã dựng xong kèm phụ đề (`.mp4`, `.narration.srt`, `.original.srt`).

---

## 4. Truyền phát video theo luồng (Streaming) & Giới hạn thực tế từ nhà cung cấp

- **Không giới hạn cứng ở ứng dụng (No App Cap):** Khác với phiên bản cũ áp đặt giới hạn 500 MB cho mỗi tệp, ToolRecap V3.0.1 đã loại bỏ giới hạn cứng này (`DEFAULT_MAX_FILE_SIZE_BYTES = None`) và chuyển sang cơ chế truyền phát theo luồng (`StreamingChatPayload`) mã hóa base64 trực tiếp khi gửi request. Kiểm thử thực tế với tệp mẫu 550 MB chứng minh mức sử dụng bộ nhớ đỉnh (peak memory) chỉ khoảng ~0.30 MB.
- **Giới hạn thực tế từ nhà cung cấp (Provider Actual Limits — Không tuyên bố vô hạn):** Mặc dù ứng dụng không còn giới hạn cứng ở phía client, các giới hạn thực tế từ phía hạ tầng AI Gateway và mô hình AI (9router / nhà cung cấp mô hình) vẫn luôn áp dụng (giới hạn kích thước payload HTTP của máy chủ, thời gian chờ mạng, giới hạn số lượng token và độ dài ngữ cảnh). Ứng dụng **không tuyên bố hỗ trợ kích thước vô hạn**.
- **Lưu ý với toàn bộ mùa phim:** Nếu bạn xử lý thư mục nhiều tập có dung lượng hàng gigabyte (GB) hoặc phim 4K chưa nén vượt quá giới hạn của nhà cung cấp, hãy nén hoặc cắt ngắn phù hợp trước khi đưa vào ứng dụng.
- **Hoàn toàn vắng mặt các module V2 cũ:** Các cơ chế xử lý ngoại lệ hình ảnh (visual exceptions), scanner, finalizer, candidate discovery, STT/Whisper, OCR và bộ tự động sửa kịch bản (heuristic repair) của V2 đều đã bị loại bỏ hoàn toàn khỏi hệ thống.

---

## 5. Dữ liệu lưu ở đâu?

Tất cả dữ liệu làm việc, cấu hình và tệp tạm được lưu riêng biệt trong thư mục `%LOCALAPPDATA%\ToolRecapV3\` (thường là `C:\Users\<Tên_bạn>\AppData\Local\ToolRecapV3\`), không làm rác thư mục chứa video gốc của bạn:

- `final/`: Chứa các tệp kịch bản tóm tắt Final JSON đã phân tích thành công (`final/<mã_dự_án>.json`).
- `raw/`: Chứa phản hồi thô nguyên bản từ AI Gateway (`raw/<mã_dự_án>.txt`) dùng để tra cứu hoặc xử lý sự cố.
- `projects/`: Chứa trạng thái và lịch sử xử lý của từng dự án (`projects/<mã_dự_án>.json`).
- `checkpoints/`: Lưu tiến trình xử lý từng bước của dự án (`checkpoints/<mã_dự_án>/<mã_checkpoint>.json`).
- `settings/`: Cài đặt hệ thống (`settings/settings.json`, tuyệt đối không chứa mật khẩu hay API key; mặc định kho cập nhật `longthao9820-alt/ToolRecap-V3`).
- `secrets/`: Chứa khóa bí mật API được mã hóa bảo vệ bởi cơ chế Windows DPAPI (`secrets/credentials.dpapi`), tuyệt đối không lưu văn bản rõ.
- `outputs/`: Thư mục mặc định chứa các video recap hoàn chỉnh đã xuất (`outputs/<mã_dự_án>/`).

---

## 6. Xử lý các sự cố thường gặp

1. **Báo lỗi "Không thể kết nối AI Gateway":**
   - Kiểm tra phần mềm 9router đang chạy trên máy (mặc định tại cổng 20128).
   - Mở **Cài đặt -> 1. AI Gateway** để kiểm tra endpoint và API key đã được lưu chính xác chưa.
2. **Báo lỗi "Kịch bản (Prompt) đang trống":**
   - Mở **Cài đặt -> 2. Kịch bản (Prompt)** và nhập nội dung yêu cầu tóm tắt cho video.
3. **Báo lỗi hoặc bị ngắt kết nối với video dung lượng lớn (Payload / Provider Limits):**
   - Ứng dụng truyền video theo luồng và không giới hạn 500 MB ở phía client (đã kiểm thử luồng 550 MB với đỉnh bộ nhớ chỉ ~0.30 MB).
   - Tuy nhiên, các giới hạn thực tế từ phía nhà cung cấp AI Gateway (kích thước request, token ngữ cảnh, timeout) vẫn áp dụng. Nếu Gateway hoặc nhà cung cấp từ chối kết nối, vui lòng giảm bớt độ phân giải hoặc dung lượng tệp video nguồn trước khi xử lý.
4. **Báo lỗi "VoiceStudio không phản hồi":**
   - Đảm bảo dịch vụ VoiceStudio Local đang bật ở cổng 3900.
   - Nếu dùng từ xa qua Tailscale, đảm bảo mạng Tailscale đang kết nối và địa chỉ HTTPS có kèm cổng (ví dụ: `:8443`).
5. **Bị gián đoạn giữa chừng (mất điện, tắt máy, mạng ngắt):**
   - Khi mở lại ứng dụng, ToolRecap V3 sẽ tự động nhận diện dự án dở dang trong danh sách "Dự án có thể tiếp tục".
   - Bấm nút **"Tiếp tục dự án"**: Ứng dụng sẽ tái sử dụng ngay kịch bản Final JSON đã lưu trong thư mục `final/`, **không gọi lại AI Gateway** (tiết kiệm hoàn toàn chi phí/token) và **không dựng lại những video đã hoàn tất**, chỉ tiếp tục thực hiện các video còn thiếu.
