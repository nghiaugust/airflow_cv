"""
OCR Recognition Module - EasyOCR
Nhận diện text trong ảnh (hoặc các vùng đã detect)
"""

import easyocr
import numpy as np
import cv2
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class EasyOCRRecognizer:
    """
    EasyOCR wrapper cho nhận diện text tiếng Việt và tiếng Anh
    """
    
    def __init__(self, languages=['vi', 'en'], gpu=False):
        """
        Args:
            languages: List các ngôn ngữ cần nhận diện
            gpu: Sử dụng GPU hay không
        """
        self.languages = languages
        self.gpu = gpu
        self.reader = None
        
    def load_model(self):
        """Load EasyOCR model vào RAM"""
        try:
            logger.info(f"Loading EasyOCR for languages: {self.languages}")
            self.reader = easyocr.Reader(
                self.languages,
                gpu=self.gpu,
                verbose=False
            )
            logger.info("EasyOCR loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load EasyOCR: {str(e)}")
            raise
    
    def recognize(self, image_input, detail=1):
        """
        Nhận diện text trong ảnh
        
        Args:
            image_input: Đường dẫn ảnh hoặc numpy array
            detail: 
                - 1: Trả về [bbox, text, confidence]
                - 0: Chỉ trả về text
                
        Returns:
            dict: {
                "text": "Full text",
                "regions": [
                    {
                        "bbox": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
                        "text": "detected text",
                        "confidence": 0.95
                    },
                    ...
                ]
            }
        """
        if self.reader is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        try:
            # Đọc ảnh nếu là đường dẫn
            if isinstance(image_input, (str, Path)):
                image = cv2.imread(str(image_input))
                if image is None:
                    raise ValueError(f"Cannot read image: {image_input}")
            else:
                # Đã là numpy array
                image = image_input
            
            # Nhận diện text
            results = self.reader.readtext(image, detail=detail)
            
            if detail == 0:
                # Chỉ có text
                return {
                    "text": " ".join(results),
                    "regions": []
                }
            else:
                # Có bbox + text + confidence
                regions = []
                full_text_parts = []
                
                for bbox, text, confidence in results:
                    regions.append({
                        "bbox": bbox,
                        "text": text,
                        "confidence": float(confidence)
                    })
                    full_text_parts.append(text)
                
                full_text = " ".join(full_text_parts)
                
                logger.info(f"Recognized {len(regions)} text regions")
                
                return {
                    "text": full_text,
                    "regions": regions,
                    "num_regions": len(regions)
                }
                
        except Exception as e:
            logger.error(f"Recognition failed: {str(e)}")
            raise
    
    def recognize_batch(self, image_list, detail=1):
        """
        Nhận diện text từ nhiều ảnh cùng lúc
        
        Args:
            image_list: List các đường dẫn ảnh hoặc numpy arrays
            detail: 1 hoặc 0
            
        Returns:
            list: Danh sách kết quả cho từng ảnh
        """
        if self.reader is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        results = []
        for image in image_list:
            result = self.recognize(image, detail=detail)
            results.append(result)
        
        return results
    
    def unload_model(self):
        """Giải phóng model khỏi RAM"""
        self.reader = None
        logger.info("EasyOCR unloaded from memory")


# Hàm tiện ích để kết hợp detection + recognition
def detect_and_recognize(image_path, detector, recognizer):
    """
    Pipeline: Detect objects -> Crop -> Recognize text
    
    Args:
        image_path: Đường dẫn ảnh input
        detector: Instance của SSDMobileNetDetector
        recognizer: Instance của EasyOCRRecognizer
        
    Returns:
        dict: Kết quả kết hợp detection + recognition
    """
    # Bước 1: Phát hiện đối tượng
    detection_result = detector.detect(image_path)
    
    if detection_result["num_detections"] == 0:
        return {
            "num_regions": 0,
            "regions": [],
            "full_text": ""
        }
    
    # Bước 2: Crop các vùng detected
    image = cv2.imread(str(image_path))
    regions = []
    full_text_parts = []
    
    for box in detection_result["boxes"]:
        x1, y1, x2, y2 = box["bbox"]
        cropped = image[y1:y2, x1:x2]
        
        # Bước 3: Nhận diện text trong vùng crop
        ocr_result = recognizer.recognize(cropped, detail=1)
        
        regions.append({
            "detection_bbox": box["bbox"],
            "detection_confidence": box["confidence"],
            "ocr_text": ocr_result["text"],
            "ocr_regions": ocr_result["regions"]
        })
        
        full_text_parts.append(ocr_result["text"])
    
    return {
        "num_regions": len(regions),
        "regions": regions,
        "full_text": " ".join(full_text_parts)
    }
