# Python 3.10.12 tabanlı resmi imajı kullan
FROM python:3.10.12-slim

# Çalışma dizini ayarla
WORKDIR /app

# Gereksinimleri kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Tüm kodu kopyala
COPY . .

# Uygulamayı başlat
CMD ["python", "main.py"]
