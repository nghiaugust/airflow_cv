# API Response Schema

Tài liệu mô tả cấu trúc JSON response chuẩn cho các API services.

## Nguyên tắc thiết kế

1. **Đơn giản**: Chỉ có các trường cơ bản cần thiết
2. **Generic**: Có thể áp dụng cho nhiều loại model khác nhau
3. **Null-safe**: Trả về `null` khi không có dữ liệu thay vì hard-code giá trị giả

## 1. Preprocessing API

### Endpoint: `POST /process`

**Request:**
```json
{
  "image_path": "/data/sample.jpg",
  "model_name": "default_binarize"
}
```

**Response:**
```json
{
  "status": "success",
  "model_used": "default_binarize",
  "output_path": null,
  "message": "Preprocessing completed (no actual processing implemented yet)"
}
```

**Giải thích:**
- `status`: Trạng thái xử lý ("success" hoặc "error")
- `model_used`: Tên model đã sử dụng
- `output_path`: Đường dẫn ảnh đã xử lý (null nếu chưa implement)
- `message`: Thông báo bổ sung

## 2. Recognition API

### Endpoint: `POST /predict`

**Request:**
```json
{
  "image_path": "/data/sample_preprocessed.jpg",
  "model_name": "trocr_base"
}
```

**Response:**
```json
{
  "status": "success",
  "model_used": "trocr_base",
  "data": null,
  "message": "Recognition completed (no actual model implemented yet)"
}
```

**Giải thích:**
- `status`: Trạng thái xử lý
- `model_used`: Tên model đã sử dụng
- `data`: Dữ liệu OCR (có thể là string, array, hoặc object tùy model)
  - Với TrOCR: có thể là `{"text": "..."}`
  - Với EasyOCR: có thể là `[{"text": "...", "confidence": 0.95, "bbox": [...]}]`
  - Generic: cho phép nhiều format khác nhau
- `message`: Thông báo bổ sung

## 3. Postprocessing API

### Endpoint: `POST /process`

**Request:**
```json
{
  "input_path": {...},
  "model_name": "regex_invoice_vn"
}
```

**Response:**
```json
{
  "status": "success",
  "model_used": "regex_invoice_vn",
  "data": null,
  "message": "Postprocessing completed (no actual processing implemented yet)"
}
```

**Giải thích:**
- `status`: Trạng thái xử lý
- `model_used`: Tên model/rule đã sử dụng
- `data`: Dữ liệu đã xử lý (format tùy thuộc vào loại postprocessing)
  - Với invoice extraction: `{"invoice_no": "...", "date": "...", ...}`
  - Với entity extraction: `{"entities": [...]}`
  - Với classification: `{"category": "...", "confidence": 0.95}`
- `message`: Thông báo bổ sung

## Khi implement logic thật

### Ví dụ với Recognition API (TrOCR):

```python
# Sau khi model predict
detected_text = model.predict(image_path)

return jsonify({
    "status": "success",
    "model_used": model_name,
    "data": {
        "text": detected_text,
        "confidence": 0.95
    },
    "message": "Text recognized successfully"
})
```

### Ví dụ với Postprocessing API (Invoice):

```python
# Sau khi extract fields
extracted_fields = extract_invoice_fields(input_data)

return jsonify({
    "status": "success",
    "model_used": model_name,
    "data": {
        "invoice_number": extracted_fields.get("invoice_number"),
        "date": extracted_fields.get("date"),
        "total": extracted_fields.get("total"),
        "vendor": extracted_fields.get("vendor")
    },
    "message": "Invoice fields extracted successfully"
})
```

## Error Response (Chung cho tất cả APIs)

```json
{
  "error": "Model xyz not loaded. Please load it first"
}
```

Hoặc:

```json
{
  "error": "Missing image_path parameter"
}
```

## Lưu ý

- Tất cả các field `data` đều nullable - trả về `null` khi không có dữ liệu
- Không hard-code giá trị giả để test
- Schema này linh hoạt để hỗ trợ nhiều loại model khác nhau
- Khi implement model thật, chỉ cần thay đổi giá trị của field `data`
