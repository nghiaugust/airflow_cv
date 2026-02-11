"""
Giao diện người dùng đơn giản cho hệ thống OCR
Upload ảnh → Xử lý qua Airflow → Hiển thị kết quả
"""

import streamlit as st
import requests
import time
import os
from datetime import datetime
from pathlib import Path
import json

# Cấu hình
AIRFLOW_URL = "http://airflow-apiserver:8080"
AIRFLOW_USER = "airflow"
AIRFLOW_PASS = "airflow"
DATA_DIR = "/data"
MAX_FILE_SIZE_MB = 10  # Giới hạn file upload 10MB

# API URLs - Phải khớp với service name trong docker-compose.yaml
PREPROCESS_API = "http://api-preprocessing:5000"
RECOGNITION_API = "http://api-recognition:5001"
POSTPROCESS_API = "http://api-postprocessing:5002"

# Cấu hình trang
st.set_page_config(
    page_title="OCR System",
    layout="wide"
)

def trigger_airflow_dag(image_filename, config):
    """Trigger Airflow DAG qua REST API"""
    url = f"{AIRFLOW_URL}/api/v1/dags/ocr_system_pipeline_v2/dagRuns"
    
    payload = {
        "conf": {
            "image_path": f"/data/{image_filename}",
            "preprocess_model": config.get("preprocess_model", "default_binarize"),
            "recognition_model": config.get("recognition_model", "trocr_base"),
            "postprocess_model": config.get("postprocess_model", "regex_invoice_vn")
        }
    }
    
    try:
        response = requests.post(
            url,
            json=payload,
            auth=(AIRFLOW_USER, AIRFLOW_PASS),
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Lỗi khi trigger DAG: {str(e)}")
        return None

def get_dag_run_status(dag_run_id):
    """Kiểm tra trạng thái DAG run"""
    url = f"{AIRFLOW_URL}/api/v1/dags/ocr_system_pipeline_v2/dagRuns/{dag_run_id}"
    
    try:
        response = requests.get(
            url,
            auth=(AIRFLOW_USER, AIRFLOW_PASS)
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Lỗi khi kiểm tra status: {str(e)}")
        return None

def get_task_logs(dag_run_id, task_id):
    """Lấy logs của task cụ thể"""
    url = f"{AIRFLOW_URL}/api/v1/dags/ocr_system_pipeline_v2/dagRuns/{dag_run_id}/taskInstances/{task_id}/logs/1"
    
    try:
        response = requests.get(
            url,
            auth=(AIRFLOW_USER, AIRFLOW_PASS)
        )
        if response.status_code == 200:
            return response.text
        return None
    except:
        return None

def load_model_api(service_url, model_name, config=None):
    """Gọi API để load model vào RAM"""
    url = f"{service_url}/load_model"
    payload = {"model_name": model_name}
    if config:
        payload.update(config)
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def unload_model_api(service_url, model_name):
    """Gọi API để unload model khỏi RAM"""
    url = f"{service_url}/unload_model"
    
    try:
        response = requests.post(url, json={"model_name": model_name}, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def check_api_health(service_url):
    """Kiểm tra API service có hoạt động không"""
    try:
        response = requests.get(f"{service_url}/health", timeout=3)
        return response.status_code == 200
    except:
        return False

# Header
st.title("Hệ thống OCR Tự động")
st.markdown("### Upload ảnh hóa đơn/tài liệu và nhận kết quả trích xuất thông tin")

# Initialize session state
if "loaded_models" not in st.session_state:
    st.session_state.loaded_models = {
        "preprocess": None,
        "recognition": None,
        "postprocess": None
    }

# Section: Quản lý Models
with st.expander("⚙️ Quản lý Models (Load/Unload)", expanded=False):
    st.markdown("**Nạp models vào RAM trước khi xử lý để tăng tốc độ**")
    
    col_model1, col_model2, col_model3 = st.columns(3)
    
    # Detection Model
    with col_model1:
        st.markdown("**Detection Model**")
        detection_choice = st.selectbox(
            "Chọn model",
            ["ssd_mobilenet_v2", "yolov5", "faster_rcnn"],
            key="detection_choice"
        )
        
        is_loaded = st.session_state.loaded_models["preprocess"] == detection_choice
        
        if is_loaded:
            st.success(f"✓ Đã load: {detection_choice}")
            if st.button("Unload", key="unload_detect"):
                with st.spinner("Đang unload..."):
                    result = unload_model_api(PREPROCESS_API, detection_choice)
                    if "error" not in result:
                        st.session_state.loaded_models["preprocess"] = None
                        st.success("Đã unload thành công!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Lỗi: {result['error']}")
        else:
            if st.button("Load Model", key="load_detect", type="primary"):
                with st.spinner(f"Đang load {detection_choice}..."):
                    config = {
                        "confidence_threshold": 0.5,
                        "nms_threshold": 0.4
                    }
                    result = load_model_api(PREPROCESS_API, detection_choice, config)
                    if "error" not in result:
                        st.session_state.loaded_models["preprocess"] = detection_choice
                        st.success(f"Đã load {detection_choice} thành công!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Lỗi: {result['error']}")
    
    # Recognition Model
    with col_model2:
        st.markdown("**Recognition Model**")
        recognition_choice = st.selectbox(
            "Chọn model",
            ["easyocr_vi_en", "trocr_base", "paddleocr"],
            key="recognition_choice"
        )
        
        is_loaded = st.session_state.loaded_models["recognition"] == recognition_choice
        
        if is_loaded:
            st.success(f"✓ Đã load: {recognition_choice}")
            if st.button("Unload", key="unload_recog"):
                with st.spinner("Đang unload..."):
                    result = unload_model_api(RECOGNITION_API, recognition_choice)
                    if "error" not in result:
                        st.session_state.loaded_models["recognition"] = None
                        st.success("Đã unload thành công!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Lỗi: {result['error']}")
        else:
            if st.button("Load Model", key="load_recog", type="primary"):
                with st.spinner(f"Đang load {recognition_choice}..."):
                    config = {
                        "languages": ["vi", "en"],
                        "gpu": False
                    }
                    result = load_model_api(RECOGNITION_API, recognition_choice, config)
                    if "error" not in result:
                        st.session_state.loaded_models["recognition"] = recognition_choice
                        st.success(f"Đã load {recognition_choice} thành công!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Lỗi: {result['error']}")
    
    # Postprocess Model
    with col_model3:
        st.markdown("**Postprocess Model**")
        postprocess_choice = st.selectbox(
            "Chọn model",
            ["regex_invoice_vn", "regex_invoice_en", "llm_extract"],
            key="postprocess_choice"
        )
        
        is_loaded = st.session_state.loaded_models["postprocess"] == postprocess_choice
        
        if is_loaded:
            st.success(f"✓ Đã load: {postprocess_choice}")
            if st.button("Unload", key="unload_post"):
                with st.spinner("Đang unload..."):
                    result = unload_model_api(POSTPROCESS_API, postprocess_choice)
                    if "error" not in result:
                        st.session_state.loaded_models["postprocess"] = None
                        st.success("Đã unload thành công!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Lỗi: {result['error']}")
        else:
            if st.button("Load Model", key="load_post", type="primary"):
                with st.spinner(f"Đang load {postprocess_choice}..."):
                    result = load_model_api(POSTPROCESS_API, postprocess_choice)
                    if "error" not in result:
                        st.session_state.loaded_models["postprocess"] = postprocess_choice
                        st.success(f"Đã load {postprocess_choice} thành công!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Lỗi: {result['error']}")
    
    st.markdown("---")
    st.caption("Load model trước sẽ giúp tăng tốc độ xử lý vì model đã nằm sẵn trong RAM")

st.markdown("---")

# Sidebar - Cấu hình
with st.sidebar:
    st.header("Cấu hình")
    
    preprocess_model = st.selectbox(
        "Model tiền xử lý (Detection)",
        ["Không", "ssd_mobilenet_v2", "yolov5", "faster_rcnn"],
        index=0,
        help="SSD MobileNet V2: Phát hiện vùng text và trả về tọa độ"
    )
    
    recognition_model = st.selectbox(
        "Model nhận diện (OCR)",
        ["Không", "easyocr_vi_en", "trocr_base", "paddleocr"],
        index=0,
        help="EasyOCR: Nhận diện text tiếng Việt + tiếng Anh trong các vùng detected"
    )
    
    postprocess_model = st.selectbox(
        "Model hậu xử lý",
        ["Không", "regex_invoice_vn", "regex_invoice_en", "llm_extract"],
        index=0,
        help="Trích xuất thông tin có cấu trúc từ text đã nhận dạng"
    )
    
    st.markdown("---")
    st.caption(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Upload ảnh")
    
    uploaded_file = st.file_uploader(
        "Chọn ảnh (JPG, PNG)",
        type=["jpg", "jpeg", "png"],
        help="Upload ảnh hóa đơn hoặc tài liệu cần OCR"
    )
    
    if uploaded_file:
        # Kiểm tra kích thước file
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            st.error(f"❌ File quá lớn! ({file_size_mb:.2f}MB). Giới hạn: {MAX_FILE_SIZE_MB}MB")
        else:
            # Hiển thị ảnh preview
            st.image(uploaded_file, caption="Ảnh đã upload", use_column_width=True)
            st.caption(f"Kích thước: {file_size_mb:.2f}MB")
            
            # Lưu file vào /data
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"upload_{timestamp}_{uploaded_file.name}"
            filepath = os.path.join(DATA_DIR, filename)
            
            with open(filepath, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.success(f"✓ Đã lưu: {filename}")
        
            # Nút xử lý
            if st.button("Bắt đầu xử lý OCR", type="primary"):
                # Kiểm tra nếu không chọn model nào
                if preprocess_model == "Không" and recognition_model == "Không" and postprocess_model == "Không":
                    st.session_state.no_model_selected = True
                    st.session_state.processing = False
                    st.rerun()
                else:
                    # Sử dụng models đã load hoặc chọn từ sidebar
                    selected_preprocess = st.session_state.loaded_models["preprocess"] or (preprocess_model if preprocess_model != "Không" else "ssd_mobilenet_v2")
                    selected_recognition = st.session_state.loaded_models["recognition"] or (recognition_model if recognition_model != "Không" else "easyocr_vi_en")
                    selected_postprocess = st.session_state.loaded_models["postprocess"] or (postprocess_model if postprocess_model != "Không" else "regex_invoice_vn")
                    
                    config = {
                        "preprocess_model": selected_preprocess,
                        "recognition_model": selected_recognition,
                        "postprocess_model": selected_postprocess
                    }
                    
                    # Hiển thị thông báo về models sẽ được sử dụng
                    st.info(f"Sử dụng models: {selected_preprocess} → {selected_recognition} → {selected_postprocess}")
                    
                    with st.spinner("Đang gửi yêu cầu đến Airflow..."):
                        result = trigger_airflow_dag(filename, config)
            
                if result:
                    dag_run_id = result.get("dag_run_id")
                    st.session_state.dag_run_id = dag_run_id
                    st.session_state.processing = True
                    st.rerun()

with col2:
    st.subheader("Kết quả")
    
    # Kiểm tra nếu không chọn model nào
    if "no_model_selected" in st.session_state and st.session_state.no_model_selected:
        st.warning("Không có mô hình nào được chọn để xử lý")
        st.session_state.no_model_selected = False
    # Kiểm tra nếu đang xử lý
    elif "processing" in st.session_state and st.session_state.processing:
        dag_run_id = st.session_state.dag_run_id
        
        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Poll DAG status
        max_attempts = 60  # 5 phút (mỗi 5s check 1 lần)
        for attempt in range(max_attempts):
            status_data = get_dag_run_status(dag_run_id)
            
            if status_data:
                state = status_data.get("state")
                
                if state == "success":
                    progress_bar.progress(100)
                    status_text.success("Xử lý hoàn tất!")
                    
                    # Lấy kết quả từ logs của task cuối
                    logs = get_task_logs(dag_run_id, "postprocessing_step")
                    
                    st.markdown("### Kết quả xử lý")
                    
                    # Hiển thị thông báo hoàn thành
                    st.info("Pipeline đã chạy thành công qua 3 bước: Preprocessing → Recognition → Postprocessing")
                    
                    # Hiển thị logs nếu có
                    if logs:
                        with st.expander("Xem logs chi tiết"):
                            st.code(logs, language="log")
                    
                    st.caption("Lưu ý: Hiện tại các API chỉ thực hiện skeleton processing. Cần implement logic thật vào src/core/")
                    
                    st.session_state.processing = False
                    break
                    
                elif state == "failed":
                    progress_bar.progress(100)
                    status_text.error("Xử lý thất bại!")
                    
                    with st.expander("Xem logs lỗi"):
                        for task in ["preprocessing_step", "recognition_step", "postprocessing_step"]:
                            logs = get_task_logs(dag_run_id, task)
                            if logs:
                                st.code(logs, language="log")
                    
                    st.session_state.processing = False
                    break
                    
                elif state == "running":
                    progress = min(30 + attempt * 2, 90)
                    progress_bar.progress(progress)
                    status_text.info(f"Đang xử lý... ({state})")
                
            time.sleep(5)  # Đợi 5 giây trước khi check lại
        
        else:
            # Timeout
            status_text.warning("Timeout! Vui lòng kiểm tra Airflow UI để xem chi tiết.")
            st.session_state.processing = False
    
    else:
        st.info("Upload ảnh và nhấn 'Bắt đầu xử lý' để xem kết quả")

# Footer
st.markdown("---")
col_a, col_b, col_c = st.columns(3)
with col_a:
    st.caption("[Airflow UI](http://localhost:8080)")
with col_b:
    st.caption("[API Health Check](http://localhost:5000/health)")
with col_c:
    if st.button("Làm mới trang"):
        st.rerun()
