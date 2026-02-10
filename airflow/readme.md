# Hệ thống OCR với Airflow

Hệ thống OCR 3 tầng được quản lý bởi Apache Airflow, gồm:
1. **API Preprocessing** (Port 5000): Tiền xử lý ảnh
2. **API Recognition** (Port 5001): Nhận dạng text từ ảnh
3. **API Postprocessing** (Port 5002): Hậu xử lý và trích xuất thông tin
4. **Airflow** (Port 8080): Quản lý pipeline workflow

## Kiến trúc

```
airflow/
├── dags/                    # Airflow DAGs
│   └── ocr_pipeline.py      # Pipeline chính
├── src/
│   ├── api/                 # Flask API services
│   │   ├── preprocessing_app.py
│   │   ├── recognition_app.py
│   │   └── postprocessing_app.py
│   └── core/                # Core logic (TODO)
├── weights/                 # Model weights (TODO)
├── data/                    # Data files
├── config.py                # Cấu hình hệ thống
├── docker-compose.yaml      # Docker services
├── Dockerfile               # Build image cho API
└── requirements.txt         # Python dependencies
```

## Cài đặt & Chạy

### 0. Tạo file .env (chỉ cần làm 1 lần)

Tạo file `.env` trong thư mục `airflow/` với nội dung:

```bash
AIRFLOW_UID=50000
AIRFLOW_PROJ_DIR=.
AIRFLOW_IMAGE_NAME=apache/airflow:3.1.7
_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow
_PIP_ADDITIONAL_REQUIREMENTS=requests
```

### 1. Khởi động hệ thống

```bash
# Di chuyển vào thư mục dự án
cd airflow

# Tạo các thư mục cần thiết (nếu chưa có)
mkdir -p ./logs ./plugins ./data ./weights

# Khởi động tất cả services
docker-compose up -d
```

### 2. Truy cập các services

- **Airflow Web UI**: http://localhost:8080
  - Username: `airflow`
  - Password: `airflow`

- **API Preprocessing**: http://localhost:5000/health
- **API Recognition**: http://localhost:5001/health
- **API Postprocessing**: http://localhost:5002/health

### 3. Kiểm tra trạng thái

```bash
# Xem logs của tất cả services
docker-compose logs -f

# Xem logs của từng service
docker-compose logs -f api-preprocessing
docker-compose logs -f api-recognition
docker-compose logs -f api-postprocessing
docker-compose logs -f airflow-scheduler
```

### 4. Chạy OCR Pipeline

1. Truy cập Airflow UI: http://localhost:8080
2. Tìm DAG: `ocr_system_pipeline_v2`
3. Bật DAG (toggle ON)
4. Click "Trigger DAG" và cung cấp config:

```json
{
  "image_path": "/data/sample_invoice.jpg",
  "preprocess_model": "default_binarize",
  "recognition_model": "trocr_base",
  "postprocess_model": "regex_invoice_vn"
}
```

### 5. Dừng hệ thống

```bash
# Dừng tất cả services
docker-compose down

# Dừng và xóa volumes (reset hoàn toàn)
docker-compose down -v
```

## Ghi chú

- Hiện tại các API chỉ trả về kết quả giả định (mock data)
- Chưa triển khai logic nạp model thật
- Để thêm model thật, cần cập nhật code trong `src/core/` và API services

## Roadmap

- [ ] Triển khai base model classes
- [ ] Thêm model preprocessing thật
- [ ] Thêm model recognition (YOLO/TrOCR)
- [ ] Thêm logic postprocessing (regex, rules)
- [ ] Thêm model weights vào thư mục weights/
- [ ] Thêm sample data vào thư mục data/

