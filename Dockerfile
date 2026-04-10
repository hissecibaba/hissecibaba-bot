# Python 3.10.12 tabanlı resmi imajı kullan
FROM python:3.10.12-slim

# Sistem paketlerini güncelle ve git + rsync kur
RUN apt-get update && apt-get install -y git rsync && rm -rf /var/lib/apt/lists/*

# Çalışma dizini ayarla
WORKDIR /app

# Gereksinimleri kopyala ve yükle
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Tüm kodu kopyala
COPY . .

# Render'ın verdiği PORT'u environment variable olarak ayarla
ENV PORT=8020

# Flask uygulamasının dinleyeceği portu expose et
EXPOSE 8020

# Uygulamayı production-ready şekilde başlat
CMD ["gunicorn", "-b", "0.0.0.0:8020", "main:flask_app"]
