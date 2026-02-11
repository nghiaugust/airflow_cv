import sys
import os
import logging
from datetime import timedelta
from airflow.decorators import dag, task
import pendulum
import requests

# --- CẤU HÌNH ĐƯỜNG DẪN IMPORT ---
# Thêm thư mục cha vào sys.path để import được file config.py nằm ngoài folder dags
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from config import settings
except ImportError:
    # Fallback nếu không tìm thấy file config (để tránh lỗi import khi IDE check)
    logging.warning("Không tìm thấy config.py, sử dụng cấu hình mặc định.")
    class MockSettings:
        PREPROC_URL = "http://api-preprocessing:5000"
        RECOG_URL = "http://api-recognition:5001"
        POST_URL = "http://api-postprocessing:5002"
    settings = MockSettings()

# --- ĐỊNH NGHĨA CÁC THAM SỐ MẶC ĐỊNH ---
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}

@dag(
    dag_id='ocr_system_pipeline_v2',
    default_args=default_args,
    description='Pipeline OCR 3 bước: Preprocess -> Recognition -> Postprocess (Dynamic Model Loading)',
    schedule=None,  # ✅ Đổi từ schedule_interval thành schedule
    start_date=pendulum.today('UTC').add(days=-1),
    tags=['ocr', 'mlops', 'dynamic-loading'],
    catchup=False
)
def ocr_pipeline():

    # --- HÀM HELPER ĐỂ GỌI API ---
    def call_api_step(url_base, endpoint, payload, task_name):
        """Hàm chung để gọi API và xử lý lỗi cơ bản"""
        full_url = f"{url_base}/{endpoint}"
        logging.info(f"[{task_name}] Calling: {full_url} with payload: {payload}")
        
        try:
            response = requests.post(full_url, json=payload, timeout=300) # Timeout 5 phút cho model nặng
            response.raise_for_status() # Báo lỗi nếu status != 200
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"[{task_name}] Failed: {str(e)}")
            raise e

    # --- TASK 1: TIỀN XỬ LÝ (PREPROCESSING) ---
    @task(task_id="preprocessing_step")
    def preprocess_image(**context):
        # 1. Lấy thông tin từ Trigger Configuration
        conf = context['dag_run'].conf
        image_path = conf.get('image_path')
        model_name = conf.get('preprocess_model', 'default_binarize') # Mặc định nếu không gửi
        
        if not image_path:
            raise ValueError("Thiếu tham số 'image_path' trong cấu hình Trigger!")

        # 2. Bước Load Model (Nếu chưa load)
        call_api_step(settings.PREPROC_URL, "load_model", {"model_name": model_name}, "Preproc-Load")
        
        # 3. Bước Xử lý ảnh
        result = call_api_step(
            settings.PREPROC_URL, 
            "process", 
            {"image_path": image_path, "model_name": model_name}, 
            "Preproc-Exec"
        )
        
        logging.info(f"Preprocessing Output: {result}")
        # Trả về image_path để task sau dùng (hoặc output_path nếu có)
        return result.get('output_path') or image_path

    # --- TASK 2: NHẬN DIỆN (RECOGNITION) ---
    @task(task_id="recognition_step")
    def recognize_text(cleaned_image_path, **context):
        conf = context['dag_run'].conf
        model_name = conf.get('recognition_model', 'trocr_base')
        
        # 1. Load Model
        call_api_step(settings.RECOG_URL, "load_model", {"model_name": model_name}, "Recog-Load")
        
        # 2. Dự đoán (Predict)
        result = call_api_step(
            settings.RECOG_URL, 
            "predict", 
            {"image_path": cleaned_image_path, "model_name": model_name}, 
            "Recog-Exec"
        )
        
        logging.info(f"Recognition Output: {result}")
        # Trả về data hoặc một placeholder để task sau có thể xử lý
        return result.get('data')

    # --- TASK 3: HẬU XỬ LÝ (POSTPROCESSING) ---
    @task(task_id="postprocessing_step")
    def post_process(recognition_data, **context):
        conf = context['dag_run'].conf
        model_name = conf.get('postprocess_model', 'regex_invoice_vn')
        
        # 1. Load Logic/Rule
        call_api_step(settings.POST_URL, "load_model", {"model_name": model_name}, "Post-Load")
        
        # 2. Chạy hậu xử lý
        result = call_api_step(
            settings.POST_URL, 
            "process", 
            {"input_path": recognition_data, "model_name": model_name}, 
            "Post-Exec"
        )
        
        logging.info(f"FINAL RESULT: {result}")
        return result

    # --- ĐỊNH NGHĨA LUỒNG DỮ LIỆU (DATA FLOW) ---
    
    # Task 1 chạy -> kết quả truyền vào Task 2
    step1_output = preprocess_image()
    
    # Task 2 chạy -> kết quả truyền vào Task 3
    step2_output = recognize_text(step1_output)
    
    # Task 3 chạy -> Ra kết quả cuối cùng
    final_output = post_process(step2_output)

# Khởi tạo DAG
ocr_dag = ocr_pipeline()