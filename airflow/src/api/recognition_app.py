# src/api/recognition_app.py
from flask import Flask, request, jsonify
import sys
import os
import logging
import threading

# Thêm đường dẫn cha để import được src.core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.core.recognition import EasyOCRRecognizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# KHO CHỨA MODEL TRONG RAM (Global Variable) - Thread-safe
# Key: tên model, Value: instance của class
active_models = {}
models_lock = threading.Lock()  # Prevent race conditions

@app.route('/health', methods=['GET'])
def health_check():
    """Kiểm tra service hoạt động"""
    return jsonify({"status": "healthy", "service": "recognition"})

@app.route('/load_model', methods=['POST'])
def load_model():
    """Airflow gọi API này để nạp model trước khi chạy"""
    config = request.json
    model_name = config.get('model_name', 'easyocr_vi_en')
    
    with models_lock:
        if model_name in active_models:
            return jsonify({"status": "already_loaded", "model": model_name})

    try:
        if model_name == 'easyocr_vi_en' or model_name == 'easyocr':
            # Khởi tạo EasyOCR
            languages = config.get('languages', ['vi', 'en'])
            gpu = config.get('gpu', False)
            
            recognizer = EasyOCRRecognizer(
                languages=languages,
                gpu=gpu
            )
            recognizer.load_model()
            
            with models_lock:
                active_models[model_name] = {
                    "instance": recognizer,
                    "type": "recognition",
                    "loaded": True
                }
            
            logger.info(f"Loaded model: {model_name}")
            return jsonify({"status": "loaded", "model": model_name})
        else:
            # Fallback cho các model khác
            with models_lock:
                active_models[model_name] = {"loaded": True, "type": "recognition"}
            return jsonify({"status": "loaded", "model": model_name, "message": "Skeleton model"})
            
    except Exception as e:
        logger.error(f"Failed to load model {model_name}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/predict', methods=['POST'])
def predict():
    """Airflow gọi API này để dự đoán"""
    data = request.json
    model_name = data.get('model_name', 'easyocr_vi_en')
    image_path = data.get('image_path')
    detection_data = data.get('detection_data')  # Dữ liệu từ preprocessing step
    
    if not image_path:
        return jsonify({"error": "Missing image_path parameter"}), 400
    
    if model_name not in active_models:
        return jsonify({"error": f"Model {model_name} not loaded. Please load it first"}), 400
    
    try:
        model_info = active_models[model_name]
        
        if "instance" in model_info:
            # Model thật đã được load
            recognizer = model_info["instance"]
            
            # Nếu có detection_data từ preprocessing, xử lý theo từng vùng
            if detection_data and detection_data.get('boxes'):
                import cv2
                
                # Crop các vùng detected
                image = cv2.imread(str(image_path))
                results_per_region = []
                full_text_parts = []
                
                for idx, box in enumerate(detection_data['boxes']):
                    x1, y1, x2, y2 = box['bbox']
                    cropped = image[y1:y2, x1:x2]
                    
                    # OCR trên vùng crop
                    ocr_result = recognizer.recognize(cropped, detail=1)
                    
                    results_per_region.append({
                        "region_id": idx,
                        "bbox": box['bbox'],
                        "detection_confidence": box['confidence'],
                        "ocr_text": ocr_result['text'],
                        "ocr_regions": ocr_result['regions']
                    })
                    
                    full_text_parts.append(ocr_result['text'])
                
                return jsonify({
                    "status": "success",
                    "model_used": model_name,
                    "data": {
                        "full_text": " ".join(full_text_parts),
                        "regions": results_per_region,
                        "num_regions": len(results_per_region)
                    },
                    "message": f"Recognized text in {len(results_per_region)} regions"
                })
            else:
                # Không có detection data, OCR toàn bộ ảnh
                result = recognizer.recognize(image_path, detail=1)
                
                return jsonify({
                    "status": "success",
                    "model_used": model_name,
                    "data": result,
                    "message": f"Recognized {result['num_regions']} text regions"
                })
        else:
            # Skeleton model
            return jsonify({
                "status": "success",
                "model_used": model_name,
                "data": None,
                "message": "Recognition completed (skeleton mode)"
            })
            
    except Exception as e:
        logger.error(f"Recognition failed: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/unload_model', methods=['POST'])
def unload_model():
    """Giải phóng RAM sau khi chạy xong"""
    model_name = request.json.get('model_name')
    
    if model_name not in active_models:
        return jsonify({"status": "not_found", "model": model_name})
    
    try:
        model_info = active_models[model_name]
        
        # Gọi unload nếu có instance
        if "instance" in model_info:
            model_info["instance"].unload_model()
        
        with models_lock:
            del active_models[model_name]
        
        import gc
        gc.collect()
        
        logger.info(f"Unloaded model: {model_name}")
        return jsonify({"status": "unloaded", "model": model_name})
        
    except Exception as e:
        logger.error(f"Failed to unload model {model_name}: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Starting Recognition API on port 5001...")
    app.run(host='0.0.0.0', port=5001, debug=True)