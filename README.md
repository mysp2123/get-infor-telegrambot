# News-Facebook AI Agent Workflow System

Hệ thống tự động tổng hợp tin tức và đăng bài lên Facebook sử dụng AI.

## Tính năng chính

- Tự động thu thập tin tức từ nhiều nguồn
- Phân tích và tổng hợp nội dung bằng AI (OpenAI, Groq)
- Tạo bài đăng tự động cho Facebook
- Hệ thống theo dõi thị trường và cảnh báo
- Dashboard tương tác cho người dùng
- Hỗ trợ nhiều API AI (OpenAI, Groq, Google Gemini)

## Yêu cầu hệ thống

- Python 3.9+
- pip
- virtualenv

## Cài đặt

1. Clone repository:
```bash
git clone https://github.com/mysp2123/get-infor-telegrambot.git
cd get-infor-telegrambot
```

2. Tạo và kích hoạt môi trường ảo:
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# HOẶC
.venv\Scripts\activate  # Windows
```

3. Cài đặt các thư viện:
```bash
pip install -r requirements.txt
```

4. Cấu hình:
- Copy `config/ai_providers_config.example.json` thành `config/ai_providers_config.json`
- Thêm API keys vào file cấu hình

## Chạy chương trình

1. Khởi động bot:
```bash
python main.py
```

2. Gửi lệnh `/start` đến bot để xem danh sách các lệnh có sẵn

## Lệnh chính

- `/start` - Xem hướng dẫn sử dụng
- `/news` - Xem tin tức mới nhất
- `/market` - Xem thông tin thị trường
- `/dashboard` - Mở dashboard tương tác (Premium)
- `/alerts` - Thiết lập cảnh báo giá (Premium)

## Lưu ý

- API keys được lưu trong `config/ai_providers_config.json`
- Logs được lưu trong thư mục `logs/`
- Cache được lưu trong thư mục `cache/`
- Hình ảnh được tạo trong thư mục `generated_images/`
