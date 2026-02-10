# src/api/recognition_app.py
from flask import Flask, request, jsonify
import sys
import os

# Thêm đường dẫn cha để import được src.core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

# TODO: Import logic lõi khi cần
# from src.core.detection import YoloDetector

app = Flask(__name__)

# KHO CHỨA MODEL TRONG RAM (Global Variable)
# Key: tên model, Value: instance của class
active_models = {}

@app.route('/health', methods=['GET'])
def health_check():
    """Kiểm tra service hoạt động"""
    return jsonify({"status": "healthy", "service": "recognition"})

@app.route('/load_model', methods=['POST'])
def load_model():
    """Airflow gọi API này để nạp model trước khi chạy"""
    config = request.json
    model_name = config.get('model_name', 'trocr_base')
    
    if model_name in active_models:
        return jsonify({"status": "already_loaded", "model": model_name})

    # TODO: Khởi tạo và nạp logic lõi khi cần
    # detector = YoloDetector()
    # detector.load_model(weight_path)
    
    # Lưu vào kho RAM (hiện tại chỉ lưu tên)
    active_models[model_name] = {"loaded": True, "type": "recognition"}
    
    return jsonify({"status": "loaded", "model": model_name})

@app.route('/predict', methods=['POST'])
def predict():
    """Airflow gọi API này để dự đoán"""
    data = request.json
    model_name = data.get('model_name', 'trocr_base')
    image_path = data.get('image_path')
    
    if not image_path:
        return jsonify({"error": "Missing image_path parameter"}), 400
    
    if model_name not in active_models:
        return jsonify({"error": f"Model {model_name} not loaded. Please load it first"}), 400
    
    # TODO: Lấy model từ RAM ra dùng khi cần
    # model_instance = active_models[model_name]
    # result = model_instance.predict(image_path)
    
    # Hiện tại trả về kết quả giả định
    output_path = image_path.replace('.jpg', '_ocr.json').replace('.png', '_ocr.json')
    
    return jsonify({
        "status": "success",
        "raw_json_path": output_path,
        "model_used": model_name,
        "text_detected": "Sample OCR text result"
    })

@app.route('/unload_model', methods=['POST'])
def unload_model():
    """Giải phóng RAM sau khi chạy xong"""
    model_name = request.json.get('model_name')
    if model_name in active_models:
        del active_models[model_name]
        import gc
        gc.collect()
        return jsonify({"status": "unloaded", "model": model_name})
    return jsonify({"status": "not_found", "model": model_name})

if __name__ == '__main__':
    print("🚀 Starting Recognition API on port 5001...")
    app.run(host='0.0.0.0', port=5001, debug=True)