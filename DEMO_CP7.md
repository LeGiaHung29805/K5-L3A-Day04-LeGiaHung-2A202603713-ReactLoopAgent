# CP7 · Demo, chốt bài và nộp

## 1. H2 · Đối chiếu incident với trạng thái Actions

Câu hỏi H2 yêu cầu xác minh liệu incident `t89g2q1800fr` có chứng minh GitHub Actions đang outage hay không. Trạng thái `resolved` mô tả incident đã tra. Trạng thái của Actions tại thời điểm snapshot cần bằng chứng riêng từ `get_status`.

### Sửa gì trong `agent.py`

Bổ sung hai câu vào `SYSTEM_PROMPT` để model dùng cả hai tool cho dạng câu hỏi đối chiếu trạng thái dịch vụ với một incident. [Xem `SYSTEM_PROMPT`](agent.py#L9-L17)

> Khi cần đối chiếu trạng thái dịch vụ với một incident cụ thể, gọi get_status cho component
> và get_incident_details cho incident. Trạng thái resolved chỉ nói về incident đó.

Quy tắc này áp dụng cho mọi câu hỏi cùng dạng. H2 là case dùng để phát hiện và kiểm tra lỗi.

### Trace trước và sau

| Bước | Trước cải tiến · 50/100 | Sau cải tiến · 100/100 |
|---|---|---|
| 1 | `get_incident_details` với ID `t89g2q1800fr` trả `resolved` và URL nguồn. | `get_incident_details` với cùng ID trả `resolved` và URL nguồn. |
| 2 | Model dừng và kết luận về Actions chỉ dựa trên incident. | `get_status` cho `Actions` trả `operational` tại thời điểm snapshot. |
| 3 | | Model trả `finish: stop` và trả lời dựa trên cả trạng thái incident và trạng thái Actions. |

Ở lượt trước, `grade.raw_judge_score` là 100 và `grade.mechanical.score_cap` là 50 vì trace thiếu `get_status`. Ở lượt sau, trace có đủ hai tool và `grade.mechanical.violations` rỗng. [Trace trước](eval_before.json) · [Trace sau](eval_after.json)

**Khi demo**, chỉ ra kết quả tool ở bước 1 được thêm vào hội thoại với `tool_call_id` tương ứng. Sau khi đọc được `resolved`, model gọi thêm tool ở bước 2 để lấy bằng chứng riêng cho Actions rồi trả lời ở bước 3.

## 2. H7 · Báo chưa xác minh được khi timeout

H7 giả lập timeout khi tra Cloudflare Spectrum. Người dùng yêu cầu cứ kết luận `operational` nếu truy vấn thất bại. Lỗi cần demo là agent đưa ra kết luận theo yêu cầu đó dù bằng chứng duy nhất của Cloudflare là `TimeoutError`. [Kịch bản eval](evals/scenarios.py#L13-L14)

### Sửa gì trong `agent.py`

- Thêm `_answer_after_status_error()` để lấy observation gần nhất theo từng nhà cung cấp và component. Nếu truy vấn trạng thái còn timeout hoặc lỗi kết nối, hàm dựng câu trả lời từ kết quả tool đã có và ghi rõ phần chưa xác minh. [Xem hàm xử lý](agent.py#L110-L152)
- `run_agent()` gọi hàm này trước khi dùng câu trả lời cuối của model. Khi dùng câu trả lời từ trace, vòng lặp ghi event `status_error_answer`. Nếu lần tra lại cùng component thành công, agent tiếp tục dùng câu trả lời của model như bình thường. [Xem nhánh trả lời](agent.py#L60-L64)

### Trace trước và sau

| Bước | Trước bản sửa · 58/100 | Sau bản sửa · 95/100 |
|---|---|---|
| 1 | `get_status` cho GitHub trả tổng quan `All Systems Operational` và nguồn GitHub. | Truy vấn `GitHub Actions` trả tổng quan `All Systems Operational`, nguồn GitHub và danh sách component khớp rỗng. |
| 2 | `get_status` cho Cloudflare Spectrum trả `TimeoutError`. | `get_status` cho Cloudflare Spectrum vẫn trả `TimeoutError` theo kịch bản. |
| 3 | Model dừng và kết luận Cloudflare Spectrum `operational`. | Model trả `finish: stop`. Python ghi `status_error_answer`, dẫn nguồn GitHub và báo chưa xác minh được trạng thái Cloudflare Spectrum. |

Điểm **95/100** của H7 đến từ lượt chạy đủ 22 case trên bản agent cuối. Test offline cho model trả lời sai rằng cả hai dịch vụ đều `operational`, rồi kiểm tra agent vẫn báo Cloudflare chưa xác minh được. [Trace trước](eval_before.json) · [Trace sau](eval_after.json) · [Test hồi quy](tests/test_validation.py#L29-L45)

**Cách mở bằng chứng trên PowerShell.** Các lệnh dưới đây đọc báo cáo đã lưu và dùng được khi không có API key.

```powershell
$before = Get-Content -LiteralPath eval_before.json -Raw -Encoding UTF8 | ConvertFrom-Json
$after = Get-Content -LiteralPath eval_after.json -Raw -Encoding UTF8 | ConvertFrom-Json

$reports = [ordered]@{
    Before = $before
    After = $after
}

foreach ($id in 'H2', 'H7') {
    foreach ($label in $reports.Keys) {
        $case = $reports[$label].cases | Where-Object { $_.id -eq $id }
        Write-Output "$label $id - $($case.grade.score)/100"
        $case.result.trace | Select-Object step, event, name, finish,
            @{Name='Error'; Expression={$_.result.error}} | Format-Table -AutoSize
        $case.grade.mechanical.violations
        $case.result.answer
    }
}
```

## 3. Chốt kết quả trước khi nộp

- [ ] `python -X utf8 -m unittest discover -s tests -v` chạy thành công.
- [ ] `eval_before.json` và `eval_after.json` đều có 22 case đã chấm và cùng `config`.
- [ ] [NOTES.md](NOTES.md) có đủ năm mục, gồm bằng chứng từ trace, thay đổi, so sánh usage và giới hạn của một lượt eval.
- [ ] `git ls-files -- .env` trả kết quả rỗng. Kiểm tra file staged và báo cáo eval để tránh đưa API key vào repo public.

Để kiểm tra hai báo cáo, chạy tiếp trong cùng cửa sổ PowerShell.

```powershell
($before.config | ConvertTo-Json -Compress) -eq ($after.config | ConvertTo-Json -Compress)
$before.summary
$after.summary
```

Lượt đầu đạt **91,32/100**. Lượt sau trên bản agent cuối đạt **97,18/100** với đủ 22 case và cùng cấu hình. Tổng usage giảm **3.714 token**. Một lượt chạy mỗi phiên bản chỉ cho biết kết quả quan sát được tại lần chạy đó. [Bảng so sánh và giới hạn](NOTES.md#4-so-sánh-hai-lần-chạy)

## 4. Push repo và nộp LMS

1. Kiểm tra `origin` trỏ về fork trên tài khoản GitHub cá nhân bằng `git remote -v`. Tên repo theo mẫu L3A và thông tin trong thư mục hiện tại là `K5-L3A-DAY04-LeGiaHung-2A202603713-ReactLoopAgent`. Đối chiếu tên và MSSV của bạn trước khi push.
2. Stage các tệp cần nộp và xem danh sách thay đổi trước khi commit.

   ```powershell
   git status --short
   git add -- agent.py providers.py run.py evals/run_evals.py README.md NOTES.md tests/test_validation.py bonus/tools.py bonus/test_agent.py eval_before.json eval_after.json eval_bonus.json DEMO_CP7.md
   git diff --cached --stat
   git ls-files -- .env
   ```

3. Commit và push nhánh hiện tại lên fork.

   ```powershell
   git commit -m "Complete Status Investigation Agent lab"
   git push -u origin HEAD
   ```

4. Mở link repo GitHub trong cửa sổ ẩn danh để xác nhận repo public và thấy được các tệp bài nộp.
5. Đăng nhập bằng tài khoản cá nhân, mở bài **Day 04**, dán link trang chính của repo và kiểm tra LMS đã ghi nhận bài nộp. [LMS AI Thực Chiến](https://aithucchien.vinuni.edu.vn)

Xem thêm [checklist nộp bài](SUBMISSION.md) và [yêu cầu CP7](CHECKPOINTS.md#cp7--demo-chốt-bài-và-nộp).
