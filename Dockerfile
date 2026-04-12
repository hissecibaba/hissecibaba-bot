# 1. Python 3.10-slim kullanarak imaj boyutunu küçük tutuyoruz
FROM python:3.10.12-slim

# 2. Sistem paketlerini kur ve temizle (İmaj boyutunu optimize eder)
RUN apt-get update && apt-get install -y \
    git \
    rsync \
    && rm -rf /var/lib/apt/lists/*

# 3. Çalışma dizini
WORKDIR /app

# 4. Önce sadece gereksinimleri kopyalıyoruz (Docker Cache avantajı)
COPY requirements.txt .

# 5. Pip güncelleme ve paket kurulumu
# --no-cache-dir build süresini biraz uzatır ama imajın şişmesini ve RAM aşımını önler
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6. Tüm proje dosyalarını kopyala
COPY . .

# 7. Render için dinamik port ayarı
ENV PORT=10000
EXPOSE 10000

# 8. Gunicorn Başlatma Komutu
# Burada main.py içindeki Flask objesi 'app' olduğu için main:app kullanıyoruz
CMD gunicorn -b 0.0.0.0:$PORT main:app
