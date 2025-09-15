# Dockerfile

FROM python:3.10-slim

WORKDIR /app

# Copy file requirements
COPY requirements.txt .

# Install dependency
RUN pip install --no-cache-dir -r requirements.txt

# Copy semua kode aplikasi
COPY . .

# Expose port yang digunakan Streamlit
EXPOSE 8501

# Perintah untuk menjalankan Streamlit
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
