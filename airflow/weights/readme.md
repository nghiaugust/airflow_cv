# Thư mục Model Weights

Nơi chứa file model weights (.pt, .onnx, .pb, .caffemodel, .bin)

## Models đã tích hợp

### 1. SSD MobileNet V2 (Object Detection)

**Mục đích**: Phát hiện vùng chứa text trong ảnh và trả về tọa độ bounding boxes

**Download pretrained model:**

```bash
# TensorFlow model
wget http://download.tensorflow.org/models/object_detection/ssd_mobilenet_v2_coco_2018_03_29.tar.gz
tar -xvf ssd_mobilenet_v2_coco_2018_03_29.tar.gz

# Copy vào thư mục weights
cp ssd_mobilenet_v2_coco_2018_03_29/frozen_inference_graph.pb weights/ssd_mobilenet_v2.pb
cp ssd_mobilenet_v2_coco_2018_03_29/pipeline.config weights/ssd_mobilenet_v2.pbtxt
```

**Hoặc sử dụng OpenCV build-in** (không cần download):

Code sẽ tự động sử dụng OpenCV DNN nếu không cung cấp model_path.

**Cấu hình trong DAG:**

```json
{
  "image_path": "/data/sample.jpg",
  "preprocess_model": "ssd_mobilenet_v2"
}
```

### 2. EasyOCR (Text Recognition)

**Mục đích**: Nhận diện text tiếng Việt + tiếng Anh trong các vùng đã detect

**Model tự động download**: 

EasyOCR sẽ tự động tải models khi chạy lần đầu tiên (~100-300MB).

**Cache persistent**:
- Models được lưu trong Docker named volume `easyocr-models`
- **KHÔNG mất khi restart Docker** (`docker-compose down/up`)
- **KHÔNG cần download lại** khi thay đổi code hoặc rebuild image
- Chỉ download lại khi xóa volume: `docker volume rm airflow_easyocr-models`

**Ngôn ngữ hỗ trợ**: Vietnamese (vi), English (en)

**Cấu hình trong DAG:**

```json
{
  "recognition_model": "easyocr_vi_en",
  "languages": ["vi", "en"],
  "gpu": false
}
```

## Cách sử dụng custom models

### Thêm model mới cho Detection (ví dụ YOLOv5):

1. Download model weights vào `weights/yolov5.pt`
2. Update `src/core/detection.py` để thêm class YOLOv5Detector
3. Update `src/api/preprocessing_app.py` để handle model mới
4. Update frontend selectbox

### Thêm model mới cho Recognition (ví dụ TrOCR):

1. Download model từ HuggingFace
2. Tạo class TrOCRRecognizer trong `src/core/recognition.py`
3. Update `src/api/recognition_app.py`
4. Update frontend selectbox

## Pipeline hoạt động

```
Input Image
    ↓
[SSD MobileNet V2] → Detect text regions → Bounding boxes
    ↓
[Crop regions]
    ↓
[EasyOCR] → Recognize text in each region → Text + confidence
    ↓
[Combine results] → Full text output
```

## Lưu ý

- **Lần chạy đầu tiên**: EasyOCR sẽ tải models (~2-5 phút tuỳ mạng)
- **Sau đó**: Models được cache vĩnh viễn, không cần tải lại
- **Khi restart Docker** (`docker-compose down/up`): Không mất cache
- **Khi rebuild Docker** (`docker-compose build`): Không mất cache
- **Khi thay đổi code Python**: Chỉ cần `docker-compose restart` (không mất models đã load trong RAM)
- SSD MobileNet có thể dùng OpenCV build-in hoặc custom weights
- Thư mục này được mount vào Docker container qua volumes