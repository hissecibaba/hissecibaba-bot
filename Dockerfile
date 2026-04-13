FROM python:3.10.12-slim

WORKDIR /app

# sistem bağımlılıkları (matplotlib + pillow + headless render stabilitesi + git)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libjpeg-dev \
    zlib1g-dev \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# proje kodu
COPY . .

# Flask + Gunicorn production start
CMD ["gunicorn", "main:flask_app", "--bind", "0.0.0.0:8020", "--workers", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
