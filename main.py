# PARÇA 1/5 — Importlar, Ortam Değişkenleri ve Temel Fonksiyonlar
# -- coding: utf-8 --
import os, re, logging, requests, datetime
import matplotlib.pyplot as plt
from flask import Flask, request, jsonify   # ✅ jsonify eklendi
from apscheduler.schedulers.background import BackgroundScheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BOT_TOKEN = os.getenv("BOT_TOKEN")
izinli_raw = os.getenv("IZINLI_ID_LIST", "")
IZINLI_ID_LIST = [int(id.strip()) for id in izinli_raw.split(",") if id.strip().isdigit()]
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# 🔹 Klasör yolları (göreceli hale getirildi)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TXT_DIR = os.path.join(BASE_DIR, "txt_dosyalar")

# ✅ Telegram tarafı: al_listeleri / sat_listeleri
AL_DIR = os.path.join(BASE_DIR, "al_listeleri")
SAT_DIR = os.path.join(BASE_DIR, "sat_listeleri")

# ✅ Mobil tarafı: al / sat
AL_MOBIL_DIR = os.path.join(BASE_DIR, "al")
SAT_MOBIL_DIR = os.path.join(BASE_DIR, "sat")

TAVAN_DIR = os.path.join(BASE_DIR, "tavan_listeleri")
ONERI_DIR = os.path.join(BASE_DIR, "öneri")
MATRIX_DIR = os.path.join(BASE_DIR, "matriks")
BALLI_KAYMAK_DIR = os.path.join(BASE_DIR, "ballikaymak")
BISTTUM_DIR = os.path.join(BASE_DIR, "bisttum")
PERFORMANS_DIR = os.path.join(BASE_DIR, "performans")
CACHE_DIR = os.path.join(BASE_DIR, "gorsel_cache")

# 🔹 Onaylayanlar klasörü sabiti
ONAYLAYANLAR_DIR = os.path.join(BASE_DIR, "onaylayanlar")

# 🔹 Mobil izinliler klasörü sabiti (abonelik kontrolü için)
MOBIL_IZINLILER_DIR = os.path.join(BASE_DIR, "mobil_izinliler")

flask_app = Flask(__name__)

def send_message(chat_id: int, text: str, mobil_mode: bool = False):
    try:
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text, "disable_notification": mobil_mode},
            timeout=10
        )
    except Exception as e:
        logging.error(f"send_message failed: {e}")

def send_photo(chat_id: int, file_path: str, caption: str = None):
    try:
        if not os.path.exists(file_path):
            send_message(chat_id, "❌ Görsel bulunamadı.")
            return
        with open(file_path, "rb") as f:
            files = {"photo": f}
            data = {"chat_id": chat_id}
            if caption:
                data["caption"] = caption
            requests.post(f"{TELEGRAM_API}/sendPhoto", data=data, files=files, timeout=30)
    except Exception as e:
        logging.error(f"send_photo failed: {e}")
        send_message(chat_id, "❌ Görsel gönderimi başarısız.")

# ✅ Yardımcı fonksiyon: cihaz ID → ID NO eşleştirmesi
def find_id_no_by_device(device_id: str):
    """
    Onaylayanlar klasöründe cihaz ID'yi arar ve karşılık gelen ID NO'yu döndürür.
    """
    try:
        for filename in os.listdir(ONAYLAYANLAR_DIR):
            file_path = os.path.join(ONAYLAYANLAR_DIR, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                if f"CIHAZ ID: {device_id}" in content:
                    for line in content.splitlines():
                        if line.startswith("ID NO:"):
                            return line.replace("ID NO:", "").strip()
        return None
    except Exception as e:
        logging.error(f"find_id_no_by_device failed: {e}")
        return None

# PARÇA 2/5 — Dosya Gönderme, Dosya Bulma ve Görsel Üretim Fonksiyonları

def send_document(chat_id: int, file_path: str, caption: str = None, mobil_mode: bool = False):
    try:
        if not os.path.exists(file_path):
            send_message(chat_id, "❌ Dosya bulunamadı.", mobil_mode)
            return
        with open(file_path, "rb") as f:
            files = {"document": f}
            data = {"chat_id": chat_id, "disable_notification": mobil_mode}
            if caption:
                data["caption"] = caption
            requests.post(f"{TELEGRAM_API}/sendDocument", data=data, files=files, timeout=30)
    except Exception as e:
        logging.error(f"send_document failed: {e}")
        send_message(chat_id, "❌ Dosya gönderimi başarısız.", mobil_mode)

def find_latest_file(folder_path: str) -> str:
    try:
        logging.info(f"📂 Klasör içeriği kontrol ediliyor: {folder_path}")
        logging.info(f"📂 Dosyalar: {os.listdir(folder_path)}")
        files = []
        for fn in os.listdir(folder_path):
            if fn.lower().endswith(".txt"):
                full_path = os.path.join(folder_path, fn)
                try:
                    parts = fn[:-4].split("_")
                    if len(parts) >= 3:
                        dt = datetime.datetime.strptime(parts[-2] + parts[-1], "%Y%m%d%H%M")
                        files.append((dt, full_path))
                    else:
                        files.append((datetime.datetime.min, full_path))
                except Exception:
                    files.append((datetime.datetime.min, full_path))
        files.sort(reverse=True)
        if files:
            logging.info(f"✅ Seçilen dosya: {files[0][1]}")
        else:
            logging.warning("❌ Hiç dosya bulunamadı.")
        return files[0][1] if files else None
    except Exception as e:
        logging.error(f"find_latest_file failed: {e}")
        return None

def txt_to_images(file_path, tag, chunk_size=40):
    try:
        logging.info(f"🖼 txt_to_images başladı: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
        logging.info(f"🖼 Dosyadan okunan satır sayısı: {len(lines)}")
        chunks = [lines[i:i+chunk_size] for i in range(0, len(lines), chunk_size)]
        image_paths = []
        for idx, chunk in enumerate(chunks, start=1):
            fig, ax = plt.subplots(figsize=(10, 0.4 * len(chunk)))
            ax.axis("off")
            table_data = [[line] for line in chunk]
            table = ax.table(cellText=table_data, loc="center", cellLoc="left")
            table.scale(1, 1.5)
            for key, cell in table.get_celld().items():
                cell.set_fontsize(10)
            if not os.path.exists(CACHE_DIR):
                os.makedirs(CACHE_DIR)
            img_path = os.path.join(CACHE_DIR, f"{tag}_{idx}.png")
            fig.savefig(img_path, bbox_inches="tight")
            plt.close(fig)
            image_paths.append(img_path)
        logging.info(f"🖼 Üretilen görsel sayısı: {len(image_paths)}")
        return image_paths
    except Exception as e:
        logging.error(f"txt_to_images failed: {e}")
        return []

def find_latest_matrix_file(keyword: str) -> str:
    try:
        logging.info(f"📂 MATRİKS klasörü içeriği: {os.listdir(MATRIX_DIR)}")
        folders = []
        for fn in os.listdir(MATRIX_DIR):
            full_path = os.path.join(MATRIX_DIR, fn)
            if os.path.isdir(full_path):
                try:
                    dt = datetime.datetime.strptime(fn, "%d.%m.%Y").date()
                    folders.append((dt, full_path))
                except Exception:
                    continue
        folders.sort(reverse=True)
        if folders:
            latest_folder = folders[0][1]
            logging.info(f"✅ Seçilen MATRİKS klasörü: {latest_folder}")
            for file in os.listdir(latest_folder):
                if keyword.lower() in file.lower():
                    logging.info(f"✅ MATRİKS dosyası bulundu: {file}")
                    return os.path.join(latest_folder, file)
        logging.warning("❌ MATRİKS dosyası bulunamadı.")
        return None
    except Exception as e:
        logging.error(f"find_latest_matrix_file failed: {e}")
        return None
        
# PARÇA 3A/5 — Bölüm A (Optimize Sync + Empty Commit Fix + Rsync Filter + Status Check)

import os
import logging
import datetime
import uuid
import subprocess

from flask import Flask, request, jsonify

def sync_to_github():
    """Render içindeki klasörleri GitHub repo ile senkronize eder (optimize edilmiş)."""
    try:
        repo_url = os.getenv("GITHUB_REPO")
        token = os.getenv("GITHUB_TOKEN")
        repo_dir = "/tmp/hissecibaba_sync"

        if not repo_url or not token:
            logging.error("❌ GITHUB_REPO veya GITHUB_TOKEN tanımlı değil.")
            return

        # Repo yoksa klonla
        if not os.path.exists(repo_dir):
            subprocess.run([
                "git", "clone",
                f"https://{token}@{repo_url}",
                repo_dir
            ], check=True)

        changed_files = []

        # ✅ Senkronize edilecek klasörler (tam liste, kök dizindeki gerçek klasörler)
        target_dirs = [
            "al", "sat", "al_listeleri", "sat_listeleri", "matriks",
            "tavan_listeleri", "txt_dosyalar", "öneri", "performans",
            "ballikaymak", "bisttum", "gorsel_cache",
            "mobil_izinliler", "onaylayanlar", "assets"
        ]

        for d in target_dirs:
            src = os.path.join(BASE_DIR, d)
            dst = os.path.join(repo_dir, d)
            os.makedirs(dst, exist_ok=True)

            # rsync çıktısını yakala
            result = subprocess.run(
                ["rsync", "-av", src + "/", dst + "/"],
                capture_output=True, text=True, check=True
            )
            logging.info(f"📂 {d.upper()} klasörü senkronize edildi.")

            # rsync çıktısından sadece dosya isimlerini ayıkla
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                if any(skip in line for skip in ["sending", "sent", "total size", "speedup"]):
                    continue
                if line.startswith("./"):
                    continue
                if line.endswith("/"):   # 🔹 klasörleri atla
                    continue
                changed_files.append(os.path.join(d, line))

        # Git kimlik bilgisi ayarları
        subprocess.run(["git", "config", "--global", "user.name", "RenderBot"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "render@hissecibaba.com"], check=True)
        subprocess.run(["git", "-C", repo_dir, "config", "user.name", "RenderBot"], check=True)
        subprocess.run(["git", "-C", repo_dir, "config", "user.email", "render@hissecibaba.com"], check=True)

        # Sadece değişen dosyaları add et ve commit et
        if changed_files:
            for f in changed_files:
                subprocess.run(["git", "-C", repo_dir, "add", f], check=True)

            # 🔹 gerçekten değişiklik var mı kontrol et
            status = subprocess.run(
                ["git", "-C", repo_dir, "status", "--porcelain"],
                capture_output=True, text=True
            )

            if status.stdout.strip():
                commit_msg = f"Auto sync {datetime.date.today()} — {len(changed_files)} file(s) updated"
                subprocess.run(["git", "-C", repo_dir, "commit", "-m", commit_msg], check=True)

                # 🔹 Push öncesi remote ile senkronizasyon
                subprocess.run(["git", "-C", repo_dir, "pull", "--rebase"], check=True)

                # 🔹 Ardından push
                subprocess.run(["git", "-C", repo_dir, "push"], check=True)

                logging.info("✅ GitHub push tamamlandı.")
            else:
                logging.info("ℹ️ No staged changes, commit skipped.")
        else:
            logging.info("ℹ️ No changes detected, commit skipped.")

    except Exception as e:
        logging.error(f"❌ Sync failed: {e}")

# PARÇA 3B/5 — Bölüm B (Consent ve Upload Route)

@flask_app.route("/check", methods=["GET", "POST"])   # ✅ GET eklendi
def check_consent():
    try:
        if request.method == "GET":
            # ✅ Keep-alive ping için basit cevap
            return jsonify({"status": "ok"}), 200

        data = request.get_json(silent=True) or {}
        device_id = data.get("device_id")

        if not device_id:
            return jsonify({"authorized": "false", "error": "device_id eksik"}), 400

        id_no = find_id_no_by_device(device_id)
        if not id_no:
            return jsonify({"authorized": "false", "error": "ID NO bulunamadı"}), 200

        izin_file = os.path.join(MOBIL_IZINLILER_DIR, f"{id_no}.txt")
        if not os.path.exists(izin_file):
            return jsonify({"authorized": "false", "error": "izin dosyası yok"}), 200

        with open(izin_file, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
            end_date_line = [l for l in lines if l.startswith("END_DATE:")][0]
            end_date_str = end_date_line.replace("END_DATE:", "").strip()
            end_date = datetime.datetime.strptime(end_date_str, "%d.%m.%Y %I:%M %p")

        if datetime.datetime.now() > end_date:
            return jsonify({"expired": "true", "end_date": end_date_str}), 200
        else:
            return jsonify({"authorized": "true", "end_date": end_date_str}), 200

    except Exception as e:
        logging.error(f"/check route hatası: {e}")
        return jsonify({"authorized": "false", "error": str(e)}), 500


@flask_app.route("/upload", methods=["POST"])
def upload_file():
    if request.is_json:
        data = request.get_json(silent=True) or {}
        payload = data.get("data", {})

        try:
            subscription = payload.get("subscription", {})
            device_id = subscription.get("device_id")

            # Benzersiz UUID üret
            uuid_val = str(uuid.uuid4())
            id_no = uuid_val[:8]

            # Onay tarihi (Türkiye saati, AM/PM formatı)
            start_dt = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
            start_date = start_dt.strftime("%d.%m.%Y %I:%M %p")

            # END_DATE = START_DATE + 7 gün
            end_dt = start_dt + datetime.timedelta(days=7)
            end_date = end_dt.strftime("%d.%m.%Y %I:%M %p")

            if device_id and uuid_val and id_no:
                # 1️⃣ mobil_izinliler dosyası
                izin_file = os.path.join(MOBIL_IZINLILER_DIR, f"{id_no}.txt")
                with open(izin_file, "w", encoding="utf-8") as f:
                    f.write(f"ID NO: {id_no}\n")
                    f.write(f"START_DATE: {start_date}\n")
                    f.write(f"END_DATE: {end_date}\n")

                # 2️⃣ onaylayanlar dosyası
                onay_file = os.path.join(ONAYLAYANLAR_DIR, f"{uuid_val}.txt")
                with open(onay_file, "w", encoding="utf-8") as f:
                    f.write("Bu dosya Açık Rıza Metninin onaylanması ile otomatik oluşturulmuştur.\n\n")
                    f.write(f"ID NO: {id_no}\n")
                    f.write(f"CIHAZ ID: {device_id}\n")
                    f.write(f"UUID: {uuid_val}\n")
                    f.write(f"ONAY TARİHİ VE SAATİ: {start_date}\n\n")
                    f.write("--- AÇIK RIZA METNİ ---\n")
                    try:
                        consent_path = os.path.join(BASE_DIR, "assets", "AÇIK RIZA METNİ.txt")
                        with open(consent_path, "r", encoding="utf-8") as consent_file:
                            f.write(consent_file.read())
                    except Exception as e:
                        f.write("Açık rıza metni yüklenemedi.\n")
                        logging.error(f"Açık rıza metni okunamadı: {e}")

                logging.info(f"✅ JSON abonelik kaydı oluşturuldu: {izin_file}")
                logging.info(f"✅ Onay dosyası oluşturuldu: {onay_file}")

                # 🔹 Dosya kaydedildikten sonra GitHub senkronizasyonu tetikle
                sync_to_github()

                return "✅ Consent & Subscription saved", 200
            else:
                return "❌ device_id veya UUID eksik", 400
        except Exception as e:
            logging.error(f"Upload JSON failed: {e}")
            return f"Hata: {e}", 500

    # 🔹 Eski form-data mantığı da korundu
    key = request.form.get("key")
    if key != os.getenv("UPLOAD_KEY"):
        return "Unauthorized", 403
    if "file" not in request.files:
        return "No file part", 400
    file = request.files["file"]
    if file.filename == "":
        return "No selected file", 400

    target = request.form.get("target", "txt_dosyalar")
    save_dir = os.path.join(BASE_DIR, target)
    os.makedirs(save_dir, exist_ok=True)

    save_path = os.path.join(save_dir, file.filename)
    try:
        file.save(save_path)
        logging.info(f"✅ File uploaded to {target}: {file.filename}")

        # 🔹 Dosya kaydedildikten sonra GitHub senkronizasyonu tetikle
        sync_to_github()

        return f"✅ File uploaded to {target}", 200
    except Exception as e:
        logging.error(f"Upload failed: {e}")
        return f"Hata: {e}", 500


# PARÇA 4/5 — Bölüm 1 (webhook başlangıcı + yeni route’lar)

@flask_app.route("/get_symbol_files", methods=["POST"])
def get_symbol_files():
    try:
        data = request.get_json(silent=True) or {}
        folder = data.get("folder", "txt_dosyalar")
        dir_path = os.path.join(BASE_DIR, folder)

        if not os.path.exists(dir_path):
            return jsonify([]), 200

        files = [f for f in os.listdir(dir_path) if f.endswith(".txt")]
        return jsonify(files), 200
    except Exception as e:
        logging.error(f"/get_symbol_files hatası: {e}")
        return jsonify([]), 500


@flask_app.route("/get_symbol_file_content", methods=["POST"])
def get_symbol_file_content():
    try:
        data = request.get_json(silent=True) or {}
        folder = data.get("folder", "txt_dosyalar")
        symbol = data.get("symbol", "")
        dir_path = os.path.join(BASE_DIR, folder)
        fp = os.path.join(dir_path, symbol)

        if os.path.exists(fp):
            with open(fp, "r", encoding="utf-8") as f:
                content = f.read()
            return content, 200
        return "❌ Dosya bulunamadı", 200
    except Exception as e:
        logging.error(f"/get_symbol_file_content hatası: {e}")
        return f"Hata: {e}", 500


@flask_app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(silent=True) or {}

        msg = data.get("message", "")
        if isinstance(msg, dict):
            msg_text = msg.get("text", "")
            chat_id = msg.get("chat", {}).get("id", 0)
        else:
            msg_text = msg
            chat_id = data.get("chat_id", 0)

        text_low = str(msg_text).lower()
        mobil_mode = data.get("mobil_mode", False)

        # Türkçe karakter normalize fonksiyonu
        def normalize_tr(text: str) -> str:
            tr_map = str.maketrans("çğıöşü", "cgiosu")
            return text.lower().translate(tr_map)

        text_norm = normalize_tr(text_low)

        # MATRİKS klasörü bulucu
        def find_latest_matrix_folder():
            try:
                folders = []
                for fn in os.listdir(MATRIX_DIR):
                    full_path = os.path.join(MATRIX_DIR, fn)
                    if os.path.isdir(full_path):
                        try:
                            dt = datetime.datetime.strptime(fn, "%d.%m.%Y").date()
                            folders.append((dt, full_path))
                        except Exception:
                            continue
                folders.sort(reverse=True)
                return folders[0][1] if folders else None
            except Exception as e:
                logging.error(f"find_latest_matrix_folder failed: {e}")
                return None

# PARÇA 4/5 — Bölüm 2-A (webhook komutlar başlangıcı)
# --- Komutlar ---
if any(x in text_norm for x in ["oneri", "öneri", "onerı", "önerı"]):
    fp = find_latest_file(ONERI_DIR)
    if fp:
        with open(fp, "r", encoding="utf-8") as f: 
            content = f.read()
        if mobil_mode:
            return jsonify({"content": content}), 200
        else:
            for idx, img in enumerate(txt_to_images(fp, "öneri_listesi"), start=1):
                send_photo(chat_id, img, caption=f"💡 Günlük ÖNERİ listesi (parça {idx})")
            return "OK", 200
    return jsonify({"error": "❌ ÖNERİ listesi bulunamadı."}), 200 if mobil_mode else ("❌ ÖNERİ listesi bulunamadı.", 200)

if text_norm == "tavan":
    fp = find_latest_file(TAVAN_DIR)
    if fp:
        with open(fp, "r", encoding="utf-8") as f: 
            content = f.read()
        if mobil_mode:
            return jsonify({"content": content}), 200
        else:
            for idx, img in enumerate(txt_to_images(fp, "tavan_listesi"), start=1):
                send_photo(chat_id, img, caption=f"🚀 Günlük TAVAN listesi (parça {idx})")
            return "OK", 200
    return jsonify({"error": "❌ TAVAN listesi bulunamadı."}), 200 if mobil_mode else ("❌ TAVAN listesi bulunamadı.", 200)

if text_norm == "temel":
    latest_folder = find_latest_matrix_folder()
    if latest_folder:
        fp = os.path.join(latest_folder, "Temp.xlsx")
        if os.path.exists(fp):
            with open(fp, "r", encoding="utf-8") as f:
                content = f.read()
            if mobil_mode:
                return jsonify({"content": content}), 200
            else:
                send_document(chat_id, fp, caption="📊 TEMEL verisi", mobil_mode=mobil_mode)
                return "OK", 200
    return jsonify({"error": "❌ Temp.xlsx bulunamadı."}), 200 if mobil_mode else ("❌ Temp.xlsx bulunamadı.", 200)

if text_norm == "teknik":
    latest_folder = find_latest_matrix_folder()
    if latest_folder:
        fp = os.path.join(latest_folder, "gunluk_veri.xlsx")
        if os.path.exists(fp):
            with open(fp, "r", encoding="utf-8") as f:
                content = f.read()
            if mobil_mode:
                return jsonify({"content": content}), 200
            else:
                send_document(chat_id, fp, caption="📊 TEKNİK veri", mobil_mode=mobil_mode)
                return "OK", 200
    return jsonify({"error": "❌ gunluk_veri.xlsx bulunamadı."}), 200 if mobil_mode else ("❌ gunluk_veri.xlsx bulunamadı.", 200)

if text_norm == "bofa":
    latest_folder = find_latest_matrix_folder()
    if latest_folder:
        fp = os.path.join(latest_folder, "AlinanSatilan.xlsx")
        if os.path.exists(fp):
            with open(fp, "r", encoding="utf-8") as f:
                content = f.read()
            if mobil_mode:
                return jsonify({"content": content}), 200
            else:
                send_document(chat_id, fp, caption="📊 BOFA verisi", mobil_mode=mobil_mode)
                return "OK", 200
    return jsonify({"error": "❌ AlinanSatilan.xlsx bulunamadı."}), 200 if mobil_mode else ("❌ AlinanSatilan.xlsx bulunamadı.", 200)



# PARÇA 4/5 — Bölüm 2-B (destek/direnç + fallback + görsel üretim)
# 📌 Destek/Direnç
if "destek" in text_norm or "direnc" in text_norm or "destek_direnc" in text_norm:
    fp_fixed = os.path.join(DESTEK_DIRENC_DIR, "destek_direnc.txt")
    target_fp = fp_fixed if os.path.exists(fp_fixed) else find_latest_file(DESTEK_DIRENC_DIR)
    if target_fp:
        with open(target_fp, "r", encoding="utf-8") as f:
            content = f.read()
        if mobil_mode:
            return jsonify({"content": content}), 200
        else:
            send_message(chat_id, content, mobil_mode)
            return "OK", 200
    return jsonify({"error": "❌ Destek/Direnç dosyası bulunamadı."}), 200 if mobil_mode else ("❌ Destek/Direnç dosyası bulunamadı.", 200)

# 📌 Ballı Kaymak
if "balli" in text_norm or "kaymak" in text_norm or "balli_kaymak" in text_norm:
    fp = find_latest_file(BALLI_KAYMAK_DIR)
    if fp:
        with open(fp, "r", encoding="utf-8") as f: 
            content = f.read()
        if mobil_mode:
            return jsonify({"content": content}), 200
        else:
            for idx, img in enumerate(txt_to_images(fp, "balli_kaymak_listesi"), start=1):
                send_photo(chat_id, img, caption=f"🍯 Ballı Kaymak listesi (parça {idx})")
            return "OK", 200
    return jsonify({"error": "❌ Ballı Kaymak listesi bulunamadı."}), 200 if mobil_mode else ("❌ Ballı Kaymak listesi bulunamadı.", 200)

# 📌 Tüm Hisseler
if ("tum" in text_norm and "hisse" in text_norm) or text_norm == "tum_hisseler":
    fp = find_latest_file(BISTTUM_DIR)
    if fp:
        with open(fp, "r", encoding="utf-8") as f: 
            content = f.read()
        if mobil_mode:
            return jsonify({"content": content}), 200
        else:
            send_message(chat_id, content, mobil_mode)
            return "OK", 200
    return jsonify({"error": "❌ Tüm hisseler dosyası bulunamadı."}), 200 if mobil_mode else ("❌ Tüm hisseler dosyası bulunamadı.", 200)

# 📌 Mobil: Bugün AL
if text_norm in ["bugun al", "al_mobil"]:
    fp = find_latest_file(AL_MOBIL_DIR)
    if fp:
        with open(fp, "r", encoding="utf-8") as f: 
            content = f.read()
        if mobil_mode:
            return jsonify({"content": content}), 200
        else:
            send_message(chat_id, content, mobil_mode)
            return "OK", 200
    return jsonify({"error": "❌ Bugün AL listesi bulunamadı."}), 200 if mobil_mode else ("❌ Bugün AL listesi bulunamadı.", 200)

# 📌 Mobil: Bugün SAT
if text_norm in ["bugun sat", "sat_mobil"]:
    fp = find_latest_file(SAT_MOBIL_DIR)
    if fp:
        with open(fp, "r", encoding="utf-8") as f: 
            content = f.read()
        if mobil_mode:
            return jsonify({"content": content}), 200
        else:
            send_message(chat_id, content, mobil_mode)
            return "OK", 200
    return jsonify({"error": "❌ Bugün SAT listesi bulunamadı."}), 200 if mobil_mode else ("❌ Bugün SAT listesi bulunamadı.", 200)

# 📌 Telegram: AL
if text_norm == "al":
    fp = find_latest_file(AL_DIR)
    if fp:
        with open(fp, "r", encoding="utf-8") as f: 
            content = f.read()
        if mobil_mode:
            return jsonify({"content": content}), 200
        else:
            for idx, img in enumerate(txt_to_images(fp, "al_listesi"), start=1):
                send_photo(chat_id, img, caption=f"📈 Günlük AL listesi (parça {idx})")
            return "OK", 200
    return jsonify({"error": "❌ AL listesi bulunamadı."}), 200 if mobil_mode else ("❌ AL listesi bulunamadı.", 200)

# 📌 Telegram: SAT
if text_norm == "sat":
    fp = find_latest_file(SAT_DIR)
    if fp:
        with open(fp, "r", encoding="utf-8") as f: 
            content = f.read()
        if mobil_mode:
            return jsonify({"content": content}), 200
        else:
            for idx, img in enumerate(txt_to_images(fp, "sat_listesi"), start=1):
                send_photo(chat_id, img, caption=f"📉 Günlük SAT listesi (parça {idx})")
            return "OK", 200
    return jsonify({"error": "❌ SAT listesi bulunamadı."}), 200 if mobil_mode else ("❌ SAT listesi bulunamadı.", 200)

# 📌 Sembol bazlı komutlar (txt_dosyalar klasöründen)
SYMBOL_DIR = os.path.join(BASE_DIR, "txt_dosyalar")
for fn in os.listdir(SYMBOL_DIR):
    fn_name = normalize_tr(fn.lower().replace(".txt",""))
    if fn_name == text_norm:
        fp_symbol = os.path.join(SYMBOL_DIR, fn)
        with open(fp_symbol, "r", encoding="utf-8") as f:
            content = f.read()
        if mobil_mode:
            return jsonify({"content": content}), 200
        else:
            send_message(chat_id, content, mobil_mode)
            return "OK", 200

# 📌 Fallback: Diğer mesajlar
if mobil_mode:
    return jsonify({"content": f"Mesajını aldım: {msg_text}"}), 200
else:
    send_message(chat_id, f"Mesajını aldım: {msg_text}", mobil_mode)
    return f"Mesajını aldım: {msg_text}", 200


    except Exception as e:
        logging.error(f"/webhook hatası: {e}")
        return "Internal Server Error", 500


# PARÇA 5a — En güncel dosyayı bul ve görsel üret (24 saat formatı)

import os
import datetime
import logging
from PIL import Image, ImageDraw, ImageFont

def get_latest_file_content_as_image(target_dir):
    """
    Belirtilen klasördeki en güncel tarihli dosyayı bulur,
    içeriğini okur ve görsel haline getirir.
    Görsel 'gorsel_cache' klasörüne kaydedilir.
    """
    try:
        dir_path = os.path.join(BASE_DIR, target_dir)
        if not os.path.exists(dir_path):
            logging.warning(f"❌ Klasör bulunamadı: {dir_path}")
            return None

        files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
        if not files:
            logging.warning(f"❌ Klasörde dosya yok: {dir_path}")
            return None

        latest_file = sorted(files)[-1]
        latest_path = os.path.join(dir_path, latest_file)

        with open(latest_path, "r", encoding="utf-8") as f:
            content = f.read()

        cache_dir = os.path.join(BASE_DIR, "gorsel_cache")
        os.makedirs(cache_dir, exist_ok=True)

        font = ImageFont.load_default()
        lines = content.splitlines()
        width = 1200
        height = 20 * (len(lines) + 2)

        img = Image.new("RGB", (width, height), color="white")
        draw = ImageDraw.Draw(img)

        y = 10
        for line in lines:
            draw.text((10, y), line, font=font, fill="black")
            y += 20

        img_name = f"{target_dir}_{latest_file}.png"
        img_path = os.path.join(cache_dir, img_name)
        img.save(img_path)

        logging.info(f"✅ Görsel üretildi: {img_path}")
        return img_path

    except Exception as e:
        logging.error(f"❌ Görsel üretim hatası: {e}")
        return None



# PARÇA 5a — En güncel dosyayı bul ve görsel üret (24 saat formatı)

import os
import datetime
import logging
from PIL import Image, ImageDraw, ImageFont

def get_latest_file_content_as_image(target_dir):
    """
    Belirtilen klasördeki en güncel tarihli dosyayı bulur,
    içeriğini okur ve görsel haline getirir.
    Görsel 'gorsel_cache' klasörüne kaydedilir.
    """
    try:
        dir_path = os.path.join(BASE_DIR, target_dir)
        if not os.path.exists(dir_path):
            logging.warning(f"❌ Klasör bulunamadı: {dir_path}")
            return None

        files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
        if not files:
            logging.warning(f"❌ Klasörde dosya yok: {dir_path}")
            return None

        # En güncel dosya (isimlere göre sıralama)
        latest_file = sorted(files)[-1]
        latest_path = os.path.join(dir_path, latest_file)

        with open(latest_path, "r", encoding="utf-8") as f:
            content = f.read()

        cache_dir = os.path.join(BASE_DIR, "gorsel_cache")
        os.makedirs(cache_dir, exist_ok=True)

        font = ImageFont.load_default()
        lines = content.splitlines()
        width = 1200
        height = 20 * (len(lines) + 2)

        img = Image.new("RGB", (width, height), color="white")
        draw = ImageDraw.Draw(img)

        y = 10
        for line in lines:
            draw.text((10, y), line, font=font, fill="black")
            y += 20

        img_name = f"{target_dir}_{latest_file}.png"
        img_path = os.path.join(cache_dir, img_name)
        img.save(img_path)

        logging.info(f"✅ Görsel üretildi: {img_path}")
        return img_path

    except Exception as e:
        logging.error(f"❌ Görsel üretim hatası: {e}")
        return None

# PARÇA 5b — Telegram komut entegrasyonu (al/sat → görsel gönder)

import os
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext

def handle_message(update: Update, context: CallbackContext):
    text = update.message.text.strip().lower()

    if text == "al":
        fp = find_latest_file(AL_DIR)
        if fp:
            images = txt_to_images(fp, "al_listesi")
            if images:
                for idx, img in enumerate(images, start=1):
                    update.message.reply_photo(open(img, "rb"), caption=f"📈 Günlük AL listesi (parça {idx})")
            else:
                update.message.reply_text("❌ AL listesi görsel üretilemedi.")
        else:
            update.message.reply_text("❌ AL listesi bulunamadı.")

    elif text == "sat":
        fp = find_latest_file(SAT_DIR)
        if fp:
            images = txt_to_images(fp, "sat_listesi")
            if images:
                for idx, img in enumerate(images, start=1):
                    update.message.reply_photo(open(img, "rb"), caption=f"📉 Günlük SAT listesi (parça {idx})")
            else:
                update.message.reply_text("❌ SAT listesi görsel üretilemedi.")
        else:
            update.message.reply_text("❌ SAT listesi bulunamadı.")

    else:
        update.message.reply_text(f"Mesajını aldım: {text}")

def start_bot():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    updater = Updater(token, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

# PARÇA 5c — Otomatik Mesaj, Scheduler ve Uygulama Çalıştırma

import pytz
import requests

def otomatik_mesaj_telegram():
    logging.info("📢 Otomatik mesaj gönderimi başlatıldı.")
    for chat_id in IZINLI_ID_LIST:
        logging.info(f"📢 Otomatik mesaj gönderiliyor → Chat ID: {chat_id}")
        send_message(
            chat_id,
            "📢 Otomatik Mesaj\n\n"
            "Hissecibaba program verileri güncellenmiştir.\n"
            "Hisse bilgileri için hissenin adını,\n"
            "Günlük AL sinyali verenler için 'AL',\n"
            "Günlük SAT sinyali verenler için 'SAT',\n"
            "Günlük muhtemel TAVAN listesi için 'TAVAN',\n"
            "Günlük ÖNERİ için 'ÖNERİ',\n"
            "Temel veri dosyası için 'TEMEL',\n"
            "Teknik veri dosyası için 'TEKNİK',\n"
            "ve Bank Off Alınan/Satılan için 'BOFA',\n"
            "yazınız. (Yazımlarınızda büyük/küçük harf farketmez)"
        )

# 🔹 Mobil komut kontrolü (abonelik süresi)
def check_subscription(user_id: str) -> bool:
    try:
        logging.info(f"📂 Mobil izinliler klasörü içeriği: {os.listdir(MOBIL_IZINLILER_DIR)}")
        files = [fn for fn in os.listdir(MOBIL_IZINLILER_DIR) if fn.startswith(user_id)]
        if not files:
            logging.warning(f"❌ Abonelik dosyası bulunamadı → User ID: {user_id}")
            return False
        files.sort(reverse=True)
        filepath = os.path.join(MOBIL_IZINLILER_DIR, files[0])
        logging.info(f"✅ Abonelik dosyası bulundu: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        end_line = [ln for ln in lines if ln.startswith("END_DATE")]
        if not end_line:
            logging.warning(f"❌ END_DATE satırı bulunamadı → User ID: {user_id}")
            return False
        end_date_str = end_line[0].split(":", 1)[1].strip()
        end_date = datetime.datetime.strptime(end_date_str, "%d.%m.%Y %H:%M")
        now = datetime.datetime.utcnow() + datetime.timedelta(hours=3)
        logging.info(f"⏳ Abonelik kontrolü → Şimdi: {now}, Bitiş: {end_date}")
        return now <= end_date
    except Exception as e:
        logging.error(f"check_subscription failed: {e}")
        return False

# 🔹 Keep-alive job (Render'ı sürekli uyanık tutmak için)
def keep_alive():
    try:
        # ✅ Artık POST isteği atıyoruz, 405 hatası çözüldü
        requests.post("https://hissecibaba-bot.onrender.com/check", json={})
        logging.info("🔄 Keep-alive ping gönderildi.")
    except Exception as e:
        logging.error(f"Keep-alive ping failed: {e}")

# 🔹 Scheduler ayarı (pytz ile timezone eklenmiş)
scheduler = BackgroundScheduler()
istanbul_tz = pytz.timezone("Europe/Istanbul")

# Otomatik mesaj job'u
scheduler.add_job(
    otomatik_mesaj_telegram,
    "cron",
    day_of_week="mon-fri",
    hour=20,
    minute=30,
    id="otomatik_mesaj",
    replace_existing=True,
    timezone=istanbul_tz
)

# Keep-alive job'u
scheduler.add_job(
    keep_alive,
    "interval",
    minutes=5,
    id="keep_alive_ping",
    replace_existing=True,
    timezone=istanbul_tz
)

scheduler.start()

# 🔹 Flask uygulaması çalıştırma
if __name__ == "__main__":
    logging.info("🚀 Flask uygulaması başlatılıyor...")
    flask_app.run(host="0.0.0.0", port=8020)
