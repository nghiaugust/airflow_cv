# config.py
# Cấu hình URL cho các API Flask services

class Settings:
    """Cấu hình chung cho hệ thống OCR"""
    
    # URL của các API services (sử dụng tên service trong docker-compose)
    PREPROC_URL = "http://api-preprocessing:5000"
    RECOG_URL = "http://api-recognition:5001"
    POST_URL = "http://api-postprocessing:5002"
    
    # Thư mục chứa dữ liệu
    DATA_DIR = "/data"
    WEIGHTS_DIR = "/weights"
    
    # Timeout cho API calls (giây)
    API_TIMEOUT = 300

# Instance để sử dụng
settings = Settings()
