# Hệ thống OCR với Airflow

Hệ thống OCR 3 tầng được quản lý bởi Apache Airflow, gồm:
1. **Frontend UI** (Port 8501): Giao diện người dùng đơn giản (Streamlit)
2. **API Preprocessing** (Port 5000): Tiền xử lý ảnh
3. **API Recognition** (Port 5001): Nhận dạng text từ ảnh
4. **API Postprocessing** (Port 5002): Hậu xử lý và trích xuất thông tin
5. **Airflow** (Port 8080): Quản lý pipeline workflow (dành cho admin)

## Kiến trúc

```
airflow/
├── dags/                    # Airflow DAGs
│   └── ocr_pipeline.py      # Pipeline chính
├── src/
│   ├── frontend/            # Giao diện người dùng
│   │   └── streamlit_app.py # Streamlit UI
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

#### 🎨 Dành cho người dùng cuối:
- **Giao diện OCR**: http://localhost:8501
  - Upload ảnh và xem kết quả ngay trên UI
  - Không cần đăng nhập
  - Tự động trigger Airflow pipeline

#### 🔧 Dành cho admin/developer:
- **Airflow Web UI**: http://localhost:8080
  - Username: `airflow`
  - Password: `airflow`
  - Quản lý và monitor DAG runs

- **API Health Checks**:
  - Preprocessing: http://localhost:5000/health
  - Recognition: http://localhost:5001/health
  - Postprocessing: http://localhost:5002/health

### 3. Kiểm tra trạng thái

```bash
# Xem logs của tất cả services
docker-compose logs -f

# Xem logs của từng service
docker-compose logs -f frontend
docker-compose logs -f api-preprocessing
docker-compose logs -f api-recognition
docker-compose logs -f api-postprocessing
docker-compose logs -f airflow-scheduler
```

### 4. Sử dụng hệ thống

#### 🎨 Cách 1: Giao diện người dùng (Khuyến nghị cho user)

1. Truy cập: **http://localhost:8501**
2. Upload ảnh hóa đơn/tài liệu (JPG/PNG)
3. Chọn model (hoặc để mặc định):
   - Model tiền xử lý (default: `default_binarize`)
   - Model nhận dạng (default: `trocr_base`)
   - Model hậu xử lý (default: `regex_invoice_vn`)
4. Click **"Bắt đầu xử lý OCR"**
5. Đợi kết quả hiển thị (tự động tracking progress)
6. Tải xuống file JSON kết quả

**Ưu điểm**: Đơn giản, trực quan, không cần kiến thức kỹ thuật

#### ⚙️ Cách 2: Trigger DAG thủ công qua Airflow UI (Dành cho admin)

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

**Ưu điểm**: Chi tiết, có logs, phù hợp debugging

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

## Kiến trúc hệ thống

### Luồng dữ liệu với Frontend UI:

```
User (Browser)
    ↓
[Frontend - Streamlit] (Port 8501)
    ↓ (trigger DAG qua REST API)
[Airflow Webserver] (Port 8080)
    ↓ (schedule tasks)
[Airflow Scheduler + Workers]
    ↓ ↓ ↓ (call APIs)
[API Preprocessing] → [API Recognition] → [API Postprocessing]
    ↓                       ↓                      ↓
cleaned_image.jpg     raw_ocr.json         final_result.json
```

### Lợi ích của kiến trúc này:

1. **Tách biệt UI và Logic**: Frontend đơn giản, Airflow xử lý orchestration phức tạp
2. **Scalable**: Có thể thêm workers để xử lý nhiều requests song song
3. **Monitoring**: Airflow UI theo dõi chi tiết từng bước
4. **Retry & Error Handling**: Tự động retry khi API fails
5. **Flexible**: Dễ dàng thay đổi model mà không ảnh hưởng UI

## Roadmap

- [ ] Triển khai base model classes
- [ ] Thêm model preprocessing thật
- [ ] Thêm model recognition (YOLO/TrOCR)
- [ ] Thêm logic postprocessing (regex, rules)
- [ ] Thêm model weights vào thư mục weights/
- [ ] Thêm sample data vào thư mục data/

# Xóa cache build cũ (optional nhưng khuyến nghị)
docker-compose build --no-cache
# Sau đó khởi động
docker-compose up -d