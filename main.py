raise SystemExit("DEBUG: Bu dosya güncel versiyon")
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

# 🔹 Klasör yolları
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TXT_DIR = os.path.join(BASE_DIR, "txt_dosyalar")

AL_DIR = os.path.join(BASE_DIR, "al_listeleri")
SAT_DIR = os.path.join(BASE_DIR, "sat_listeleri")

AL_MOBIL_DIR = os.path.join(BASE_DIR, "al")
SAT_MOBIL_DIR = os.path.join(BASE_DIR, "sat")

TAVAN_DIR = os.path.join(BASE_DIR, "tavan_listeleri")
ONERI_DIR = os.path.join(BASE_DIR, "öneri")
MATRIX_DIR = os.path.join(BASE_DIR, "matriks")
BALLI_KAYMAK_DIR = os.path.join(BASE_DIR, "ballikaymak")
BISTTUM_DIR = os.path.join(BASE_DIR, "bisttum")
PERFORMANS_DIR = os.path.join(BASE_DIR, "performans")
CACHE_DIR = os.path.join(BASE_DIR, "gorsel_cache")

DESTEK_DIRENC_DIR = os.path.join(BASE_DIR, "destek_direnc")
ONAYLAYANLAR_DIR = os.path.join(BASE_DIR, "onaylayanlar")
MOBIL_IZINLILER_DIR = os.path.join(BASE_DIR, "mobil_izinliler")

flask_app = Flask(__name__)

def send_message(chat_id: int, text: str, mobil_mode: bool = False):
    """
    Telegram için mesaj gönderir. Mobil_mode True ise JSON dönüş üst katmanda yapılmalı.
    """
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

def find_id_no_by_device(device_id: str):
    """
    Onaylayanlar klasöründe cihaz ID'yi arar ve karşılık gelen ID NO'yu döndürür.
    """
    try:
        if not os.path.exists(ONAYLAYANLAR_DIR): return None
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

def get_symbol_file_content(symbol: str):
    """
    txt_dosyalar klasöründen sembol.txt dosyasını okur.
    Flutter'dan gelen ismin büyük/küçük harf durumunu ve .txt uzantısını kontrol eder.
    """
    try:
        # Flutter'dan "THYAO.txt" veya "THYAO" gelebilir. Temizleyelim:
        clean_symbol = symbol.replace(".txt", "").replace(".TXT", "")
        
        # Hem küçük harf hem büyük harf olasılığını kontrol edelim
        potential_files = [f"{clean_symbol}.txt", f"{clean_symbol.lower()}.txt", f"{clean_symbol.upper()}.txt"]
        
        for file_name in potential_files:
            fp = os.path.join(TXT_DIR, file_name)
            if os.path.exists(fp):
                with open(fp, "r", encoding="utf-8") as f:
                    return f.read()
        return None
    except Exception as e:
        logging.error(f"get_symbol_file_content failed: {e}")
        return None

# PARÇA 2/5 — Dosya Gönderme, Dosya Bulma ve Görsel Üretim Fonksiyonları

import datetime

def send_document(chat_id: int, file_path: str, caption: str = None, mobil_mode: bool = False):
    """
    Mobil modda ise dosyanın içeriğini metin olarak döner (Flutter'da görüntülemek için), 
    Telegram'da ise doküman olarak gönderir.
    """
    try:
        if not os.path.exists(file_path):
            if mobil_mode:
                return jsonify({"content": "❌ Dosya henüz mevcut değil."}), 200
            else:
                send_message(chat_id, "❌ Dosya bulunamadı.", mobil_mode)
                return "❌ Dosya bulunamadı.", 200

        if mobil_mode:
            # Flutter tarafı içerik beklediği için dosyayı okuyup metin olarak dönüyoruz
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return jsonify({"content": content}), 200
        else:
            with open(file_path, "rb") as f:
                files = {"document": f}
                data = {"chat_id": chat_id, "disable_notification": mobil_mode}
                if caption:
                    data["caption"] = caption
                requests.post(f"{TELEGRAM_API}/sendDocument", data=data, files=files, timeout=30)
            return "OK", 200
    except Exception as e:
        logging.error(f"send_document failed: {e}")
        if mobil_mode:
            return jsonify({"content": "❌ Dosya içeriği okunamadı."}), 500
        else:
            send_message(chat_id, "❌ Dosya gönderimi başarısız.", mobil_mode)
            return "❌ Dosya gönderimi başarısız.", 500

def find_latest_file(folder_path: str) -> str:
    """
    Klasördeki .txt dosyalarını tarihlerine göre (dosya adı veya sistem saati) sıralayıp en güncelini döner.
    """
    try:
        if not os.path.exists(folder_path):
            logging.warning(f"❌ Klasör yok: {folder_path}")
            return None
            
        files = []
        for fn in os.listdir(folder_path):
            if fn.lower().endswith(".txt"):
                full_path = os.path.join(folder_path, fn)
                # Önce dosya adından tarih parse etmeyi dene (09.04.2026.txt gibi)
                date_str = fn.replace(".txt", "").replace(".TXT", "")
                try:
                    try:
                        dt = datetime.datetime.strptime(date_str, "%d.%m.%Y")
                    except ValueError:
                        dt = datetime.datetime.strptime(date_str, "%d.%m.%Y_%H%M")
                except Exception:
                    # Eğer isimden tarih çıkmazsa (örn: THYAO.txt), dosyanın son değiştirilme tarihini kullan
                    dt = datetime.datetime.fromtimestamp(os.path.getmtime(full_path))
                
                files.append((dt, full_path))
        
        files.sort(reverse=True, key=lambda x: x[0])
        if files:
            return files[0][1]
        return None
    except Exception as e:
        logging.error(f"find_latest_file failed: {e}")
        return None

def txt_to_images(file_path, tag, chunk_size=40):
    try:
        logging.info(f"🖼 txt_to_images başladı: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f if ln.strip()]
        
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
            
            os.makedirs(CACHE_DIR, exist_ok=True)
            img_path = os.path.join(CACHE_DIR, f"{tag}_{idx}.png")
            fig.savefig(img_path, bbox_inches="tight")
            plt.close(fig)
            image_paths.append(img_path)
        return image_paths
    except Exception as e:
        logging.error(f"txt_to_images failed: {e}")
        return []

def find_latest_matrix_file(keyword: str) -> str:
    try:
        if not os.path.exists(MATRIX_DIR): return None
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
            for file in os.listdir(latest_folder):
                if keyword.lower() in file.lower():
                    return os.path.join(latest_folder, file)
        return None
    except Exception as e:
        logging.error(f"find_latest_matrix_file failed: {e}")
        return None

# PARÇA 3A/5 — Bölüm A (Optimize Sync + Local Rsync Only, No GitHub Push)

import os
import logging
import subprocess
from flask import Flask, request, jsonify

def sync_to_github():
    """Render içindeki klasörleri lokal repo ile senkronize eder (push işlemleri iptal edildi)."""
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

        # ✅ Senkronize edilecek klasörler (Hisse Analiz ve Mobil tarafı için tam liste)
        target_dirs = [
            "al", "sat", "al_listeleri", "sat_listeleri", "matriks",
            "tavan_listeleri", "txt_dosyalar", "öneri", "performans",
            "ballikaymak", "bisttum", "gorsel_cache",
            "mobil_izinliler", "onaylayanlar", "assets",
            "destek_direnc"
        ]

        for d in target_dirs:
            src = os.path.join(BASE_DIR, d)
            dst = os.path.join(repo_dir, d)
            
            # Kaynak klasör yoksa oluştur (rsync hatasını önlemek için)
            if not os.path.exists(src):
                os.makedirs(src, exist_ok=True)
                logging.info(f"🆕 Eksik klasör oluşturuldu: {d}")
                
            os.makedirs(dst, exist_ok=True)

            # rsync ile dosyaları aynala (Flutter tarafının en güncel veriyi görmesi için)
            subprocess.run(
                ["rsync", "-av", "--delete", src + "/", dst + "/"],
                capture_output=True, text=True, check=True
            )
            logging.info(f"📂 {d.upper()} klasörü lokalde senkronize edildi.")

        logging.info("ℹ️ Lokal senkronizasyon tamamlandı, GitHub push yapılmadı.")

    except Exception as e:
        logging.error(f"❌ Sync failed: {e}")

# PARÇA 3B/5 — Bölüm B (Consent ve Upload Route)
import uuid # ✅ UUID kütüphanesi eksikti, eklendi

@flask_app.route("/check", methods=["GET", "POST"])
def check_consent():
    try:
        if request.method == "GET":
            return jsonify({"status": "ok"}), 200

        data = request.get_json(silent=True) or {}
        device_id = data.get("device_id")

        if not device_id:
            return jsonify({"authorized": "false", "error": "device_id eksik"}), 200

        id_no = find_id_no_by_device(device_id)
        if not id_no:
            return jsonify({"authorized": "false", "error": "ID NO bulunamadı"}), 200

        izin_file = os.path.join(MOBIL_IZINLILER_DIR, f"{id_no}.txt")
        if not os.path.exists(izin_file):
            return jsonify({"authorized": "false", "error": "izin dosyası yok"}), 200

        with open(izin_file, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
            end_date_line = next((l for l in lines if l.startswith("END_DATE:")), None)
            
            if not end_date_line:
                return jsonify({"authorized": "false", "error": "END_DATE satırı yok"}), 200
            
            end_date_str = end_date_line.replace("END_DATE:", "").strip()
            # Tarih formatı esnekliği sağlandı
            try:
                end_date = datetime.datetime.strptime(end_date_str, "%d.%m.%Y %I:%M %p")
            except ValueError:
                end_date = datetime.datetime.strptime(end_date_str, "%d.%m.%Y %H:%M")

        if datetime.datetime.now() > end_date:
            return jsonify({"authorized": "false", "expired": "true", "end_date": end_date_str}), 200
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

            # uuid kütüphanesi yukarıda eklendiği için artık hata vermeyecek
            uuid_val = str(uuid.uuid4())
            id_no = uuid_val[:8]

            start_dt = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
            start_date = start_dt.strftime("%d.%m.%Y %I:%M %p")
            end_dt = start_dt + datetime.timedelta(days=7)
            end_date = end_dt.strftime("%d.%m.%Y %I:%M %p")

            if device_id:
                os.makedirs(MOBIL_IZINLILER_DIR, exist_ok=True)
                izin_file = os.path.join(MOBIL_IZINLILER_DIR, f"{id_no}.txt")
                with open(izin_file, "w", encoding="utf-8") as f:
                    f.write(f"ID NO: {id_no}\n")
                    f.write(f"START_DATE: {start_date}\n")
                    f.write(f"END_DATE: {end_date}\n")

                os.makedirs(ONAYLAYANLAR_DIR, exist_ok=True)
                onay_file = os.path.join(ONAYLAYANLAR_DIR, f"{uuid_val}.txt")
                with open(onay_file, "w", encoding="utf-8") as f:
                    f.write("Bu dosya Açık Rıza Metninin onaylanması ile otomatik oluşturulmuştur.\n\n")
                    f.write(f"ID NO: {id_no}\n")
                    f.write(f"CIHAZ ID: {device_id}\n")
                    f.write(f"UUID: {uuid_val}\n")
                    f.write(f"ONAY TARİHİ VE SAATİ: {start_date}\n\n")
                    f.write("--- AÇIK RIZA METNİ ---\n")
                    
                    consent_path = os.path.join(BASE_DIR, "assets", "AÇIK RIZA METNİ.txt")
                    if os.path.exists(consent_path):
                        with open(consent_path, "r", encoding="utf-8") as cp:
                            f.write(cp.read())
                    else:
                        f.write("Açık rıza metni dosyası sistemde bulunamadı.\n")

                return jsonify({"status": "ok", "id_no": id_no, "end_date": end_date}), 200
            else:
                return jsonify({"status": "error", "error": "device_id eksik"}), 400
        except Exception as e:
            logging.error(f"Upload JSON failed: {e}")
            return jsonify({"status": "error", "error": str(e)}), 500

    # Dosya yükleme (key tabanlı) kısmı
    key = request.form.get("key")
    if key != os.getenv("UPLOAD_KEY"):
        return jsonify({"status": "error", "error": "Unauthorized"}), 403
    
    if "file" not in request.files:
        return jsonify({"status": "error", "error": "No file part"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"status": "error", "error": "No selected file"}), 400

    target = request.form.get("target", "txt_dosyalar")
    save_dir = os.path.join(BASE_DIR, target)
    os.makedirs(save_dir, exist_ok=True)

    save_path = os.path.join(save_dir, file.filename)
    try:
        file.save(save_path)
        return jsonify({"status": "ok", "file": file.filename, "target": target}), 200
    except Exception as e:
        logging.error(f"Upload failed: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

# PARÇA 4/5 — Bölüm 1 (webhook başlangıcı + yeni route’lar)
@flask_app.route("/get_symbol_files", methods=["POST"])
def get_symbol_files():
    try:
        data = request.get_json(silent=True) or {}
        # Flutter'dan gelen klasör ismini temizle ve güvenli hale getir
        folder = data.get("folder", "txt_dosyalar").strip("/")
        dir_path = os.path.join(BASE_DIR, folder)

        if not os.path.exists(dir_path):
            logging.warning(f"⚠️ Klasör bulunamadı: {dir_path}")
            return jsonify([]), 200

        # Dosyaları listele, gizli dosyaları ve .txt olmayanları ele
        files = [f for f in os.listdir(dir_path) if f.lower().endswith(".txt") and not f.startswith(".")]
        # Listeyi alfabetik sırala (Flutter'da daha düzenli görünür)
        files.sort()
        
        return jsonify(files), 200
    except Exception as e:
        logging.error(f"/get_symbol_files hatası: {e}")
        return jsonify([]), 200 # Flutter tarafının çökmemesi için 200 dönüyoruz


@flask_app.route("/get_symbol_file_content", methods=["POST"])
def get_symbol_file_content():
    try:
        data = request.get_json(silent=True) or {}
        folder = data.get("folder", "txt_dosyalar").strip("/")
        symbol = data.get("symbol", "").strip()
        
        if not symbol:
            return jsonify({"error": "❌ Sembol parametresi eksik"}), 200

        # Uzantı kontrolü (Flutter'dan uzantısız gelirse ekle)
        if not symbol.lower().endswith(".txt"):
            symbol = f"{symbol}.txt"

        dir_path = os.path.join(BASE_DIR, folder)
        fp = os.path.join(dir_path, symbol)

        if os.path.exists(fp) and os.path.isfile(fp):
            with open(fp, "r", encoding="utf-8") as f:
                content = f.read()
            return jsonify({"content": content}), 200
            
        return jsonify({"error": f"❌ {symbol} dosyası bulunamadı"}), 200
    except Exception as e:
        logging.error(f"/get_symbol_file_content hatası: {e}")
        return jsonify({"error": f"Sistem Hatası: {str(e)}"}), 200


@flask_app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(silent=True) or {}

        msg = data.get("message", "")
        # Telegram verisi mi yoksa Flutter butonu mu kontrolü
        if isinstance(msg, dict):
            msg_text = msg.get("text", "")
            chat_id = msg.get("chat", {}).get("id", 0)
        else:
            msg_text = msg
            chat_id = data.get("chat_id", 0)

        text_low = str(msg_text).lower().strip()
        mobil_mode = data.get("mobil_mode", False)

        # Türkçe karakterleri normalize et (Hatalı eşleşmeyi önlemek için)
        def normalize_tr(text: str) -> str:
            tr_map = str.maketrans("çğıöşü", "cgiosu")
            return text.translate(tr_map)

        text_norm = normalize_tr(text_low)

        # MATRİKS klasörü bulucu (Hiyerarşik yapı kontrolü)
        def find_latest_matrix_folder():
            try:
                if not os.path.exists(MATRIX_DIR):
                    return None
                folders = []
                for fn in os.listdir(MATRIX_DIR):
                    full_path = os.path.join(MATRIX_DIR, fn)
                    if os.path.isdir(full_path):
                        try:
                            # 09.04.2026 formatını parse et
                            dt = datetime.datetime.strptime(fn, "%d.%m.%Y").date()
                            folders.append((dt, full_path))
                        except Exception:
                            continue
                if folders:
                    folders.sort(reverse=True)
                    return folders[0][1]
                return None
            except Exception as e:
                logging.error(f"find_latest_matrix_folder failed: {e}")
                return None

# PARÇA 4/5 (WEBHOOK ROUTE — Tüm komutlar ve fallback) — DÜZELTİLMİŞ TAM KOD

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

        # --- Komutlar ---
        if any(x in text_low for x in ["öneri", "oneri", "önerı", "onerı"]):
            fp = find_latest_file(ONERI_DIR)
            if fp:
                if mobil_mode:
                    with open(fp, "r", encoding="utf-8") as f: content = f.read()
                    send_message(chat_id, content, mobil_mode)
                    return content, 200
                else:
                    for idx, img in enumerate(txt_to_images(fp, "öneri_listesi"), start=1):
                        send_photo(chat_id, img, caption=f"💡 Günlük ÖNERİ listesi (parça {idx})")
                    return "OK", 200
            send_message(chat_id, "❌ ÖNERİ listesi bulunamadı.", mobil_mode)
            return "❌ ÖNERİ listesi bulunamadı.", 200

        if text_low == "tavan":
            fp = find_latest_file(TAVAN_DIR)
            if fp:
                if mobil_mode:
                    with open(fp, "r", encoding="utf-8") as f: content = f.read()
                    send_message(chat_id, content, mobil_mode)
                    return content, 200
                else:
                    for idx, img in enumerate(txt_to_images(fp, "tavan_listesi"), start=1):
                        send_photo(chat_id, img, caption=f"🚀 Günlük TAVAN listesi (parça {idx})")
                    return "OK", 200
            send_message(chat_id, "❌ TAVAN listesi bulunamadı.", mobil_mode)
            return "❌ TAVAN listesi bulunamadı.", 200

        if text_low == "temel":
            latest_folder = find_latest_matrix_folder()
            if latest_folder:
                fp = os.path.join(latest_folder, "Temp.xlsx")
                if os.path.exists(fp):
                    send_document(chat_id, fp, caption="📊 TEMEL verisi", mobil_mode=mobil_mode)
                    return "OK", 200
            send_message(chat_id, "❌ Temp.xlsx bulunamadı.", mobil_mode)
            return "❌ Temp.xlsx bulunamadı.", 200

        if text_low == "teknik":
            latest_folder = find_latest_matrix_folder()
            if latest_folder:
                fp = os.path.join(latest_folder, "gunluk_veri.xlsx")
                if os.path.exists(fp):
                    send_document(chat_id, fp, caption="📊 TEKNİK veri", mobil_mode=mobil_mode)
                    return "OK", 200
            send_message(chat_id, "❌ gunluk_veri.xlsx bulunamadı.", mobil_mode)
            return "❌ gunluk_veri.xlsx bulunamadı.", 200

        if text_low == "bofa":
            latest_folder = find_latest_matrix_folder()
            if latest_folder:
                fp = os.path.join(latest_folder, "AlinanSatilan.xlsx")
                if os.path.exists(fp):
                    send_document(chat_id, fp, caption="📊 BOFA verisi", mobil_mode=mobil_mode)
                    return "OK", 200
            send_message(chat_id, "❌ AlinanSatilan.xlsx bulunamadı.", mobil_mode)
            return "❌ AlinanSatilan.xlsx bulunamadı.", 200

        # 📌 Destek/Direnç (özel düzeltme)
        if "destek" in text_low or "direnc" in text_low or "destek_direnc" in text_low:
            fp_fixed = os.path.join(DESTEK_DIRENC_DIR, "destek_direnc.txt")
            if os.path.exists(fp_fixed):
                with open(fp_fixed, "r", encoding="utf-8") as f:
                    content = f.read()
                send_message(chat_id, content, mobil_mode)
                return content, 200
            fp = find_latest_file(DESTEK_DIRENC_DIR)
            if fp:
                with open(fp, "r", encoding="utf-8") as f:
                    content = f.read()
                send_message(chat_id, content, mobil_mode)
                return content, 200
            send_message(chat_id, "❌ Destek/Direnç dosyası bulunamadı.", mobil_mode)
            return "❌ Destek/Direnç dosyası bulunamadı.", 200

        # 📌 Sembol bazlı komutlar (case-insensitive ve startswith kontrolü)
        for fn in os.listdir(TXT_DIR):
            if fn.lower().startswith(text_low.lower()):
                fp_symbol = os.path.join(TXT_DIR, fn)
                with open(fp_symbol, "r", encoding="utf-8") as f:
                    content = f.read()
                send_message(chat_id, content, mobil_mode)
                return content, 200

        logging.info(f"Gelen text_low: {text_low}")

        # 📌 Ballı Kaymak
        if ("balli" in text_low or "kaymak" in text_low) or "balli_kaymak" in text_low:
            fp = find_latest_file(BALLI_KAYMAK_DIR)
            if fp:
                if mobil_mode:
                    with open(fp, "r", encoding="utf-8") as f: 
                        content = f.read()
                    send_message(chat_id, content, mobil_mode)
                    return content, 200
                else:
                    for idx, img in enumerate(txt_to_images(fp, "balli_kaymak_listesi"), start=1):
                        send_photo(chat_id, img, caption=f"🍯 Ballı Kaymak listesi (parça {idx})")
                    return "OK", 200
            send_message(chat_id, "❌ Ballı Kaymak listesi bulunamadı.", mobil_mode)
            return "❌ Ballı Kaymak listesi bulunamadı.", 200

        # 📌 Dünkü Performans
        if ("dünkü" in text_low and "performans" in text_low) or text_low == "performans":
            fp = find_latest_file(PERFORMANS_DIR)
            if fp:
                with open(fp, "r", encoding="utf-8") as f: 
                    content = f.read()
                send_message(chat_id, content, mobil_mode)
                return content, 200
            send_message(chat_id, "❌ Performans dosyası bulunamadı.", mobil_mode)
            return "❌ Performans dosyası bulunamadı.", 200

        # 📌 Tüm Hisseler
        if ("tüm" in text_low and "hisse" in text_low) or text_low == "tum_hisseler":
            fp = find_latest_file(BISTTUM_DIR)
            if fp:
                with open(fp, "r", encoding="utf-8") as f: 
                    content = f.read()
                send_message(chat_id, content, mobil_mode)
                return content, 200
            send_message(chat_id, "❌ Tüm hisseler dosyası bulunamadı.", mobil_mode)
            return "❌ Tüm hisseler dosyası bulunamadı.", 200

        # 📌 Mobil: Bugün AL
        if text_low in ["bugün al", "bugunal", "al_mobil"]:
            fp = find_latest_file(AL_MOBIL_DIR)
            if fp:
                with open(fp, "r", encoding="utf-8") as f: 
                    content = f.read()
                send_message(chat_id, content, mobil_mode)
                return content, 200
            send_message(chat_id, "❌ Bugün AL listesi bulunamadı.", mobil_mode)
            return "❌ Bugün AL listesi bulunamadı.", 200

        # 📌 Mobil: Bugün SAT
        if text_low in ["bugün sat", "bugunsat", "sat_mobil"]:
            fp = find_latest_file(SAT_MOBIL_DIR)
            if fp:
                with open(fp, "r", encoding="utf-8") as f: 
                    content = f.read()
                send_message(chat_id, content, mobil_mode)
                return content, 200
            send_message(chat_id, "❌ Bugün SAT listesi bulunamadı.", mobil_mode)
            return "❌ Bugün SAT listesi bulunamadı.", 200

        # 📌 Telegram: AL
        if text_low == "al":
            fp = find_latest_file(AL_DIR)
            if fp:
                if mobil_mode:
                    with open(fp, "r", encoding="utf-8") as f: 
                        content = f.read()
                    send_message(chat_id, content, mobil_mode)
                    return content, 200
                else:
                    for idx, img in enumerate(txt_to_images(fp, "al_listesi"), start=1):
                        send_photo(chat_id, img, caption=f"📈 Günlük AL listesi (parça {idx})")
                    return "OK", 200
            send_message(chat_id, "❌ AL listesi bulunamadı.", mobil_mode)
            return "❌ AL listesi bulunamadı.", 200

        # 📌 Telegram: SAT
        if text_low == "sat":
            fp = find_latest_file(SAT_DIR)
            if fp:
                if mobil_mode:
                    with open(fp, "r", encoding="utf-8") as f: 
                        content = f.read()
                    send_message(chat_id, content, mobil_mode)
                    return content, 200
                else:
                    for idx, img in enumerate(txt_to_images(fp, "sat_listesi"), start=1):
                        send_photo(chat_id, img, caption=f"📉 Günlük SAT listesi (parça {idx})")
                    return "OK", 200
            send_message(chat_id, "❌ SAT listesi bulunamadı.", mobil_mode)
            return "❌ SAT listesi bulunamadı.", 200

        # 📌 Fallback: Diğer mesajlar
        send_message(chat_id, f"Mesajını aldım: {msg_text}", mobil_mode)
        return f"Mesajını aldım: {msg_text}", 200

    except Exception as e:
        logging.error(f"/webhook route hatası: {e}")
        return f"Hata: {e}", 500


# =================================================================
# PARÇA 5a — Görsel Üretim ve Yardımcı Fonksiyonlar
# =================================================================
import os
import datetime
import logging
from PIL import Image, ImageDraw, ImageFont

def get_latest_file_content_as_image(target_dir):
    try:
        dir_path = os.path.join(BASE_DIR, target_dir)
        cache_path = os.path.join(BASE_DIR, "gorsel_cache")
        os.makedirs(cache_path, exist_ok=True)

        if not os.path.exists(dir_path):
            logging.warning(f"❌ Klasör bulunamadı: {dir_path}")
            return None

        files = [f for f in os.listdir(dir_path) if f.lower().endswith(".txt") and not f.startswith(".")]
        if not files:
            logging.warning(f"❌ Klasörde işlenecek .txt dosyası yok: {dir_path}")
            return None

        latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(dir_path, f)))
        latest_path = os.path.join(dir_path, latest_file)

        with open(latest_path, "r", encoding="utf-8") as f:
            content = f.read()

        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "DejaVuSans.ttf", "arial.ttf"
        ]
        
        font = None
        for path in font_paths:
            try:
                font = ImageFont.truetype(path, 15)
                break
            except: continue
        
        if font is None: font = ImageFont.load_default()

        lines = content.splitlines()
        width = 1000
        line_height = 25
        height = line_height * (len(lines) + 4)

        img = Image.new("RGB", (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)

        y = 20
        draw.text((20, y), f"Rapor Tarihi: {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}", font=font, fill=(100, 100, 100))
        y += 40

        for line in lines:
            draw.text((20, y), line, font=font, fill=(0, 0, 0))
            y += line_height

        clean_name = latest_file.replace(".txt", "").replace(" ", "_")
        img_name = f"{target_dir}_{clean_name}.png"
        img_full_path = os.path.join(cache_path, img_name)
        img.save(img_full_path)

        logging.info(f"✅ Görsel üretildi: {img_full_path}")
        return img_full_path
    except Exception as e:
        logging.error(f"❌ Görsel üretim hatası: {e}")
        return None

# =================================================================
# PARÇA 5b — Telegram Bot Mantığı
# =================================================================
import threading
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext

def handle_telegram_message(update: Update, context: CallbackContext):
    try:
        if not update.message or not update.message.text: return
        text_norm = update.message.text.strip().lower().translate(str.maketrans("ışğçöü", "isgcou"))

        if text_norm == "al":
            fp = find_latest_file(AL_DIR)
            if fp:
                images = txt_to_images(fp, "al_listesi")
                for idx, img in enumerate(images or [], start=1):
                    with open(img, "rb") as f:
                        update.message.reply_photo(photo=f, caption=f"📈 Günlük AL listesi ({idx})")
            else: update.message.reply_text("❌ Güncel AL listesi bulunamadı.")

        elif text_norm == "sat":
            fp = find_latest_file(SAT_DIR)
            if fp:
                images = txt_to_images(fp, "sat_listesi")
                for idx, img in enumerate(images or [], start=1):
                    with open(img, "rb") as f:
                        update.message.reply_photo(photo=f, caption=f"📉 Günlük SAT listesi ({idx})")
            else: update.message.reply_text("❌ Güncel SAT listesi bulunamadı.")
        
        else:
            update.message.reply_text("🤖 Komut anlaşılamadı. Örn: AL, SAT, Hisse Kodu")
    except Exception as e:
        logging.error(f"Telegram Hatası: {e}")

def run_telegram_bot():
    token = os.getenv("BOT_TOKEN")
    if not token: return
    try:
        updater = Updater(token, use_context=True)
        dp = updater.dispatcher
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_telegram_message))
        updater.start_polling(drop_pending_updates=True)
    except Exception as e:
        logging.error(f"Bot Başlatma Hatası: {e}")

# =================================================================
# PARÇA 5c — Zamanlanmış Görevler (Scheduler)
# =================================================================
import pytz, requests, shutil, subprocess

def otomatik_mesaj_telegram():
    for chat_id in IZINLI_ID_LIST:
        try:
            send_message(chat_id, "📢 *Sistem Bilgilendirmesi*\nVeriler güncellendi!", mobil_mode=False)
        except: pass

def keep_alive():
    try:
        url = os.getenv("APP_URL", "https://hissecibaba-bot.onrender.com")
        requests.get(url, timeout=10)
    except: pass

# --- SCHEDULER AYARLARI ---
from apscheduler.schedulers.background import BackgroundScheduler
scheduler = BackgroundScheduler(timezone=pytz.timezone("Europe/Istanbul"))
scheduler.add_job(otomatik_mesaj_telegram, "cron", day_of_week="mon-fri", hour=21, minute=0)
scheduler.add_job(keep_alive, "interval", minutes=10)


# =================================================================
# ANA ÇALIŞTIRICI (RENDER & GUNICORN UYUMLU)
# =================================================================

def start_services():
    # Gunicorn'un botu birden fazla kez başlatmasını önlemek için check
    if not any(t.name == "TelegramBotThread" for t in threading.enumerate()):
        t = threading.Thread(target=run_telegram_bot, name="TelegramBotThread", daemon=True)
        t.start()
        logging.info("🚀 Telegram bot thread başlatıldı.")

    if not scheduler.running:
        scheduler.start()
        logging.info("⏰ Scheduler aktif edildi.")

# Gunicorn veya Python doğrudan çalıştırmada servisleri tetikler
start_services()

if __name__ == "__main__":
    # Render Portu
    port = int(os.environ.get("PORT", 10000))
    # Local çalıştırma
    flask_app.run(host="0.0.0.0", port=port, debug=False)
