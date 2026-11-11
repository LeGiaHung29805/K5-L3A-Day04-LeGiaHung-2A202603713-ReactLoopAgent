# Ghi chú phân tích · Day 04

Họ và tên **Le Gia Hung**

MSSV **2A202603713**

## 1. Case được chọn

- **H2.** Kiểm tra tình trạng GitHub Actions trong snapshot và xác minh incident `t89g2q1800fr` có chứng minh outage hay không.
- Bản đầu trả lời “Hiện tại **GitHub Actions không đang outage**” dựa trên việc incident đã `resolved`.
- Điểm lượt đầu **50/100**. Judge cho 100 điểm thô, còn kiểm tra bằng code áp trần 50 vì trace thiếu `get_status`.

## 2. Bằng chứng trong trace

Trích các trường liên quan từ `eval_before.json`, case H2.

```json
[
  {"event": "model", "step": 1, "finish": "tool_calls"},
  {
    "event": "tool", "step": 1, "name": "get_incident_details",
    "arguments": {"incident_id": "t89g2q1800fr", "provider": "github"},
    "result": {
      "status": "resolved", "components": ["Actions"],
      "captured_at": "2026-11-09T03:50:47.065020+00:00",
      "url": "https://stspg.io/lv4q3xm9r0rk"
    }
  },
  {"event": "model", "step": 2, "finish": "stop"}
]
```

Trường `status` trong observation mô tả vòng đời của incident. Cần truy vấn thêm trạng thái component trong snapshot để có căn cứ cho kết luận về Actions. Trace H7 cũng cho thấy một lỗi khác. Cloudflare trả `TimeoutError` ở bước 2, nhưng câu trả lời suy đoán Spectrum `operational` theo đề nghị của người dùng.

## 3. Thay đổi đã thực hiện

- `SYSTEM_PROMPT` trong `agent.py` yêu cầu dùng `get_status` cho component và `get_incident_details` cho incident khi câu hỏi cần đối chiếu hai loại thông tin. Khi tool gặp lỗi, agent phải báo phần chưa xác minh được.
- Vòng lặp giữ URL từ các kết quả `get_incident_details` thành công. Nếu câu trả lời thiếu URL incident đã quan sát, trace ghi `validation_missing_source` và model nhận yêu cầu sửa trong `max_steps`. Chẳng hạn, ở E4 bản đầu đã đọc được URL `https://stspg.io/pjgptg3cfc6n` nhưng câu trả lời chỉ có ký hiệu `【/commentary】`.
- Với H7, `_answer_after_status_error()` dựng câu trả lời từ observation khi truy vấn trạng thái còn lỗi kết nối hoặc timeout. Agent báo phần chưa xác minh được và vẫn trích nguồn cho kết quả truy vấn thành công. Nhánh này ghi `status_error_answer` vào trace.

## 4. So sánh hai lần chạy

`eval_before.json` và `eval_after.json` đều chấm đủ 22 case. Cả hai dùng Groq `openai/gpt-oss-120b` cho agent và judge, cùng snapshot và `max_steps = 8`. Lượt sau được lưu giữa chừng khi Groq giới hạn API, rồi chạy tiếp các case chưa chấm. Mã agent, dữ liệu và cấu hình đã được đối chiếu khi chạy tiếp.

| Chỉ số | Lượt trước | Lượt sau |
|---|---|---|
| Điểm tổng | 91,32/100 | 97,18/100 |
| H2 | 50/100 | 100/100 |
| H7 | 58/100 | 95/100 |
| Số model calls có usage | 69 agent + 22 judge | 63 agent + 22 judge |
| Token theo usage | 75.819 agent + 56.916 judge | 74.812 agent + 54.209 judge |

- Lượt sau tăng **5,86 điểm**. Tổng usage giảm từ **132.735 xuống 129.021 token**, ít hơn **3.714 token** (khoảng **2,8%**). Phần so sánh chi phí dựa trên token ghi trong báo cáo vì API trả số token sử dụng.
- H2 dùng `get_incident_details` ở bước 1 để xác nhận incident đã `resolved` và `get_status` ở bước 2 để xác nhận `Actions` là `operational` tại thời điểm snapshot. Trace đạt cả hai yêu cầu kiểm tra bằng code.
- A7 có event `validation_missing_source` ở bước 3. Sau yêu cầu sửa, model dẫn URL incident Phoenix trong câu trả lời cuối và nêu rằng chưa đủ bằng chứng liên hệ sự cố với người dùng tại Việt Nam.
- H6 tăng từ **50 lên 100**. Lượt sau có `get_status` và gọi tiếp incident gộp `xr3myzj7ms51` được dẫn trong update.
- H7 tăng từ **58 lên 95**. Trace ghi `TimeoutError` ở bước 2 và `status_error_answer` ở bước 3. Agent báo chưa xác minh được Cloudflare Spectrum và dẫn nguồn cho trạng thái tổng quan GitHub.
- H1 giảm từ **95 xuống 87**. Trace lượt sau đọc hai incident chính, trong khi câu hỏi còn yêu cầu theo liên kết trong incident GitHub. Judge cũng ghi nhận thời gian `resolved` chưa nhất quán và câu trả lời thiếu lưu ý về dữ liệu bị cắt.

## 5. Giới hạn

- Judge và agent dùng cùng model trong bài chính. H2 cho thấy điểm thô của judge có thể bỏ sót thiếu sót trong trace.
- Snapshot ghi nhận dữ liệu tại thời điểm lấy mẫu. Tìm kiếm theo chuỗi chỉ bao phủ tối đa 50 incident gần nhất của mỗi nhà cung cấp. Kết quả chi tiết có thể rút gọn timeline hoặc cắt ngắn nội dung update.
- Validation xác nhận sự hiện diện của ít nhất một URL đã quan sát. Việc mỗi kết luận có nguồn phù hợp và mọi nguồn cần thiết đã được dẫn vẫn cần kiểm tra qua trace.
- Mỗi phiên bản trong bảng so sánh có một bộ kết quả đầy đủ. Kết quả có thể dao động giữa các lần gọi model, nên số điểm và mức sử dụng ghi ở trên chỉ phản ánh hai lượt đánh giá này.

## Bonus

`eval_bonus.json` chấm đủ 10 case bằng Groq `openai/gpt-oss-20b` cho agent và judge, với `max_steps = 16`. Điểm tăng từ **80,60 lên 96,30/100**, tương đương **12,09 lên 14,44/15** theo phép quy đổi của runner.

- **B1, 0 → 100.** Lượt đầu dừng với câu trả lời rỗng sau hai truy vấn. Sau bản sửa, trace ghi `validation_empty_answer` ở bước 4. Vòng lặp yêu cầu model tiếp tục trong giới hạn bước, rồi nhận hai truy vấn còn thiếu cho npm và DigitalOcean. Câu trả lời có trạng thái, thời điểm snapshot và nguồn của cả năm dịch vụ.
- **B6, 50 → 98.** Prompt bonus yêu cầu đọc chi tiết khi đối chiếu phạm vi và thời điểm sự cố. Trace lượt sau có hai `get_status` và hai `get_incident_details`, dẫn nguồn cho Vercel và npm. Trace lưu đủ 160 mục nhiễu. Yêu cầu chấm ban đầu bị Groq từ chối với HTTP 413. Khi chấm lại bằng cùng judge, phần trace được gửi dưới dạng mảng JSON gọn hơn với đầy đủ trường và dữ liệu đã lưu.
- **Pagination và lỗi truy vấn.** B2 dùng `next_offset` và đọc tiếp ở `offset: 3`. B3 phục hồi sau một lỗi 429. B4 dừng sau ba lượt thử Vercel và vẫn báo kết quả GitHub. B5 sửa tham số `offset` và `limit` sau lỗi `INVALID_ARGUMENTS`. Với 429 từ API live, vòng lặp giữ `Retry-After` trong observation và dừng truy vấn nhà cung cấp đó trong run hiện tại.
- **Giới hạn của điểm judge.** B9 đạt 65 dù nhận xét của judge xác nhận agent đã báo rõ giới hạn khi được hỏi về Linear và Slack. Trace và câu trả lời là bằng chứng để đối chiếu điểm này.
