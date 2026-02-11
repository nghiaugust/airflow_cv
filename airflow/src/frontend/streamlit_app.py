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

# Header
st.title("Hệ thống OCR Tự động")
st.markdown("### Upload ảnh hóa đơn/tài liệu và nhận kết quả trích xuất thông tin")

# Sidebar - Cấu hình
with st.sidebar:
    st.header("Cấu hình")
    
    preprocess_model = st.selectbox(
        "Model tiền xử lý",
        ["Không", "default_binarize", "advanced_denoise", "adaptive_threshold"],
        index=0
    )
    
    recognition_model = st.selectbox(
        "Model nhận dạng",
        ["Không", "trocr_base", "trocr_large", "easyocr_vn", "paddleocr"],
        index=0
    )
    
    postprocess_model = st.selectbox(
        "Model hậu xử lý",
        ["Không", "regex_invoice_vn", "regex_invoice_en", "llm_extract"],
        index=0
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
        # Hiển thị ảnh preview
        st.image(uploaded_file, caption="Ảnh đã upload", use_column_width=True)
        
        # Lưu file vào /data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"upload_{timestamp}_{uploaded_file.name}"
        filepath = os.path.join(DATA_DIR, filename)
        
        with open(filepath, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        st.success(f"Đã lưu: {filename}")
        
        # Nút xử lý
        if st.button("Bắt đầu xử lý OCR", type="primary"):
            # Kiểm tra nếu không chọn model nào
            if preprocess_model == "Không" and recognition_model == "Không" and postprocess_model == "Không":
                st.session_state.no_model_selected = True
                st.session_state.processing = False
                st.rerun()
            else:
                config = {
                    "preprocess_model": preprocess_model if preprocess_model != "Không" else "default_binarize",
                    "recognition_model": recognition_model if recognition_model != "Không" else "trocr_base",
                    "postprocess_model": postprocess_model if postprocess_model != "Không" else "regex_invoice_vn"
                }
                
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
