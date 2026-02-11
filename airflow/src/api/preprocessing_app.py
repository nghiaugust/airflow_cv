# src/api/preprocessing_app.py
from flask import Flask, request, jsonify
import sys
import os

# Thêm đường dẫn cha để import được src.core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

app = Flask(__name__)

# KHO CHỨA MODEL TRONG RAM (Global Variable)
active_models = {}

@app.route('/health', methods=['GET'])
def health_check():
    """Kiểm tra service hoạt động"""
    return jsonify({"status": "healthy", "service": "preprocessing"})

@app.route('/load_model', methods=['POST'])
def load_model():
    """Airflow gọi API này để nạp model trước khi chạy"""
    config = request.json
    model_name = config.get('model_name', 'default_binarize')
    
    if model_name in active_models:
        return jsonify({"status": "already_loaded", "model": model_name})
    
    # TODO: Khởi tạo model thật khi cần
    # Hiện tại chỉ lưu tên model vào RAM
    active_models[model_name] = {"loaded": True, "type": "preprocessing"}
    
    return jsonify({"status": "loaded", "model": model_name})

@app.route('/process', methods=['POST'])
def process():
    """Airflow gọi API này để tiền xử lý ảnh"""
    data = request.json
    model_name = data.get('model_name', 'default_binarize')
    image_path = data.get('image_path')
    
    if not image_path:
        return jsonify({"error": "Missing image_path parameter"}), 400
    
    if model_name not in active_models:
        return jsonify({"error": f"Model {model_name} not loaded. Please load it first"}), 400
    
    # TODO: Xử lý ảnh thật khi cần
    # Hiện tại trả về None vì chưa có logic xử lý
    
    return jsonify({
        "status": "success",
        "model_used": model_name,
        "output_path": None,
        "message": "Preprocessing completed (no actual processing implemented yet)"
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
    print("🚀 Starting Preprocessing API on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True)
