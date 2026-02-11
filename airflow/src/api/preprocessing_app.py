# src/api/preprocessing_app.py
from flask import Flask, request, jsonify
import sys
import os
import logging
import threading

# Thêm đường dẫn cha để import được src.core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.core.detection import SSDMobileNetDetector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# KHO CHỨA MODEL TRONG RAM (Global Variable) - Thread-safe
active_models = {}
models_lock = threading.Lock()  # Prevent race conditions

@app.route('/health', methods=['GET'])
def health_check():
    """Kiểm tra service hoạt động"""
    return jsonify({"status": "healthy", "service": "preprocessing"})

@app.route('/load_model', methods=['POST'])
def load_model():
    """Airflow gọi API này để nạp model trước khi chạy"""
    config = request.json
    model_name = config.get('model_name', 'ssd_mobilenet_v2')
    
    with models_lock:
        if model_name in active_models:
            return jsonify({"status": "already_loaded", "model": model_name})
    
    try:
        if model_name == 'ssd_mobilenet_v2' or model_name == 'ssd':
            # Khởi tạo SSD MobileNet V2
            model_path = config.get('model_path', 'weights/ssd_mobilenet_v2_coco.pb')
            config_path = config.get('config_path', 'weights/ssd_mobilenet_v2_coco.pbtxt')
            confidence_threshold = config.get('confidence_threshold', 0.5)
            nms_threshold = config.get('nms_threshold', 0.4)
            
            detector = SSDMobileNetDetector(
                model_path=model_path,
                config_path=config_path,
                confidence_threshold=confidence_threshold,
                nms_threshold=nms_threshold
            )
            detector.load_model()
            
            with models_lock:
                active_models[model_name] = {
                    "instance": detector,
                    "type": "detection",
                    "loaded": True
                }
            
            logger.info(f"Loaded model: {model_name}")
            return jsonify({"status": "loaded", "model": model_name})
        else:
            # Fallback cho các model khác (skeleton)
            with models_lock:
                active_models[model_name] = {"loaded": True, "type": "preprocessing"}
            return jsonify({"status": "loaded", "model": model_name, "message": "Skeleton model"})
            
    except Exception as e:
        logger.error(f"Failed to load model {model_name}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/process', methods=['POST'])
def process():
    """Airflow gọi API này để tiền xử lý ảnh"""
    data = request.json
    model_name = data.get('model_name', 'ssd_mobilenet_v2')
    image_path = data.get('image_path')
    
    if not image_path:
        return jsonify({"error": "Missing image_path parameter"}), 400
    
    if model_name not in active_models:
        return jsonify({"error": f"Model {model_name} not loaded. Please load it first"}), 400
    
    try:
        model_info = active_models[model_name]
        
        if "instance" in model_info:
            # Model thật đã được load
            detector = model_info["instance"]
            result = detector.detect(image_path)
            
            return jsonify({
                "status": "success",
                "model_used": model_name,
                "data": result,
                "message": f"Detected {result['num_detections']} objects"
            })
        else:
            # Skeleton model
            return jsonify({
                "status": "success",
                "model_used": model_name,
                "data": None,
                "message": "Preprocessing completed (skeleton mode)"
            })
            
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
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
    print("Starting Preprocessing API on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True)
