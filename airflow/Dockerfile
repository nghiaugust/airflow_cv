# Dockerfile cho các Flask API services
FROM python:3.10-slim

WORKDIR /app

# Copy requirements và install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code (logs/, data/, plugins/ sẽ bị loại trừ bởi .dockerignore)
COPY src/ ./src/
COPY config.py .

# Tạo thư mục cần thiết (sẽ được mount từ host)
RUN mkdir -p /data /weights

# Expose ports (sẽ được overwrite trong docker-compose)
EXPOSE 5000 5001 5002

# Default command (sẽ được overwrite trong docker-compose)
CMD ["python", "src/api/preprocessing_app.py"]
