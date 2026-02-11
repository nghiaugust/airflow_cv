"""
Object Detection Module - SSD MobileNet V2
Phát hiện đối tượng trong ảnh và trả về tọa độ bounding boxes
"""

import cv2
import numpy as np
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class SSDMobileNetDetector:
    """
    SSD MobileNet V2 detector sử dụng OpenCV DNN
    """
    
    def __init__(self, model_path=None, config_path=None, confidence_threshold=0.5):
        """
        Args:
            model_path: Đường dẫn đến file .pb hoặc .caffemodel
            config_path: Đường dẫn đến file config (.pbtxt hoặc .prototxt)
            confidence_threshold: Ngưỡng confidence để filter detections
        """
        self.model_path = model_path
        self.config_path = config_path
        self.confidence_threshold = confidence_threshold
        self.net = None
        
    def load_model(self):
        """Load model vào RAM"""
        try:
            if self.model_path and self.config_path:
                logger.info(f"Loading SSD MobileNet V2 from {self.model_path}")
                
                # Detect model type
                if self.model_path.endswith('.pb'):
                    # TensorFlow model
                    self.net = cv2.dnn.readNetFromTensorflow(self.model_path, self.config_path)
                elif self.model_path.endswith('.caffemodel'):
                    # Caffe model
                    self.net = cv2.dnn.readNetFromCaffe(self.config_path, self.model_path)
                else:
                    raise ValueError(f"Unsupported model format: {self.model_path}")
                
                logger.info("SSD MobileNet V2 loaded successfully")
            else:
                # Sử dụng pretrained model từ OpenCV (nếu có)
                logger.warning("No model path provided. Using default OpenCV model if available.")
                # TODO: Download pretrained model if needed
                
        except Exception as e:
            logger.error(f"Failed to load SSD model: {str(e)}")
            raise
    
    def detect(self, image_path):
        """
        Phát hiện đối tượng trong ảnh
        
        Args:
            image_path: Đường dẫn đến ảnh input
            
        Returns:
            dict: {
                "boxes": [
                    {
                        "class": "text",
                        "confidence": 0.95,
                        "bbox": [x1, y1, x2, y2]
                    },
                    ...
                ],
                "image_shape": [height, width, channels]
            }
        """
        if self.net is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        try:
            # Đọc ảnh
            image = cv2.imread(str(image_path))
            if image is None:
                raise ValueError(f"Cannot read image: {image_path}")
            
            h, w = image.shape[:2]
            
            # Tạo blob từ ảnh
            blob = cv2.dnn.blobFromImage(
                image, 
                size=(300, 300),  # SSD MobileNet V2 standard input
                mean=(127.5, 127.5, 127.5),
                scalefactor=1.0/127.5,
                swapRB=True,
                crop=False
            )
            
            # Forward pass
            self.net.setInput(blob)
            detections = self.net.forward()
            
            # Parse detections
            boxes = []
            for i in range(detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                
                if confidence > self.confidence_threshold:
                    # Get bounding box coordinates
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    x1, y1, x2, y2 = box.astype(int)
                    
                    # Class ID (1 = text for some models)
                    class_id = int(detections[0, 0, i, 1])
                    
                    boxes.append({
                        "class_id": class_id,
                        "class": "text",  # Default to text
                        "confidence": float(confidence),
                        "bbox": [int(x1), int(y1), int(x2), int(y2)]
                    })
            
            logger.info(f"Detected {len(boxes)} objects in {image_path}")
            
            return {
                "boxes": boxes,
                "image_shape": [h, w, 3],
                "num_detections": len(boxes)
            }
            
        except Exception as e:
            logger.error(f"Detection failed: {str(e)}")
            raise
    
    def unload_model(self):
        """Giải phóng model khỏi RAM"""
        self.net = None
        logger.info("SSD MobileNet V2 unloaded from memory")


# Hàm tiện ích để crop ảnh theo bounding boxes
def crop_detections(image_path, boxes, output_dir=None):
    """
    Crop các vùng detected từ ảnh gốc
    
    Args:
        image_path: Đường dẫn ảnh gốc
        boxes: List các bounding boxes từ detector
        output_dir: Thư mục lưu ảnh crop (optional)
        
    Returns:
        list: Danh sách numpy arrays của các ảnh đã crop
    """
    image = cv2.imread(str(image_path))
    cropped_images = []
    
    for idx, box in enumerate(boxes):
        x1, y1, x2, y2 = box["bbox"]
        cropped = image[y1:y2, x1:x2]
        cropped_images.append(cropped)
        
        # Lưu file nếu có output_dir
        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            output_path = Path(output_dir) / f"crop_{idx}.jpg"
            cv2.imwrite(str(output_path), cropped)
    
    return cropped_images
