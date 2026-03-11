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
AL_DIR = os.path.join(BASE_DIR, "al_listeleri")
SAT_DIR = os.path.join(BASE_DIR, "sat_listeleri")
TAVAN_DIR = os.path.join(BASE_DIR, "tavan_listeleri")
ONERI_DIR = os.path.join(BASE_DIR, "öneri")
MATRIX_DIR = os.path.join(BASE_DIR, "matriks")
AL_NEW_DIR = os.path.join(BASE_DIR, "al")
SAT_NEW_DIR = os.path.join(BASE_DIR, "sat")
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
        
# PARÇA 3/5 — Upload Route ve Webhook Başlangıcı (Telegram + Flutter JSON Desteği + Loglama)

import os
import logging
import datetime
import uuid   # 🔹 eksik olan satır eklendi

from flask import Flask, request, jsonify

@flask_app.route("/check", methods=["POST"])
def check_consent():
    try:
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
            user_name = subscription.get("user_name", "UNKNOWN")

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
                    # Açık rıza metnini assets klasöründen oku
                    try:
                        with open(r"C:\hb_mobile\hb_mobile_project\assets\AÇIK RIZA METNİ.txt", "r", encoding="utf-8") as consent_file:
                            f.write(consent_file.read())
                    except Exception as e:
                        f.write("Açık rıza metni yüklenemedi.\n")
                        logging.error(f"Açık rıza metni okunamadı: {e}")

                logging.info(f"✅ JSON abonelik kaydı oluşturuldu: {izin_file}")
                logging.info(f"✅ Onay dosyası oluşturuldu: {onay_file}")
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
        return f"✅ File uploaded to {target}", 200
    except Exception as e:
        logging.error(f"Upload failed: {e}")
        return f"Hata: {e}", 500

# PARÇA 4/5 — Diğer Komutlar (ÖNERİ, TAVAN, TEMEL, TEKNİK, BOFA, BALLI KAYMAK, PERFORMANS, TÜM HİSSELER)

        # En güncel matriks klasörünü bul
        def find_latest_matrix_folder():
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
                    logging.info(f"✅ Seçilen MATRİKS klasörü: {folders[0][1]}")
                else:
                    logging.warning("❌ MATRİKS klasörü bulunamadı.")
                return folders[0][1] if folders else None
            except Exception as e:
                logging.error(f"find_latest_matrix_folder failed: {e}")
                return None

        # ÖNERİ komutu
        if any(x in text_low for x in ["öneri", "oneri", "önerı", "onerı"]):
            logging.info(f"📂 ÖNERİ klasörü içeriği: {os.listdir(ONERI_DIR)}")
            fp = find_latest_file(ONERI_DIR)
            if fp:
                logging.info(f"✅ ÖNERİ dosyası bulundu: {fp}")
                if mobil_mode:
                    with open(fp, "r", encoding="utf-8") as f:
                        content = f.read()
                    send_message(chat_id, content, mobil_mode)
                    return content, 200
                else:
                    images = txt_to_images(fp, "öneri_listesi")
                    logging.info(f"🖼 ÖNERİ listesi görsellere dönüştürüldü, {len(images)} parça")
                    for idx, img in enumerate(images, start=1):
                        send_photo(chat_id, img, caption=f"💡 Günlük ÖNERİ listesi (parça {idx})")
                    return "OK", 200
            else:
                logging.warning("❌ ÖNERİ listesi bulunamadı.")
                send_message(chat_id, "❌ ÖNERİ listesi bulunamadı.", mobil_mode)
                return "❌ ÖNERİ listesi bulunamadı.", 200

        # TAVAN komutu
        if text_low == "tavan":
            logging.info(f"📂 TAVAN klasörü içeriği: {os.listdir(TAVAN_DIR)}")
            fp = find_latest_file(TAVAN_DIR)
            if fp:
                logging.info(f"✅ TAVAN dosyası bulundu: {fp}")
                if mobil_mode:
                    with open(fp, "r", encoding="utf-8") as f:
                        content = f.read()
                    send_message(chat_id, content, mobil_mode)
                    return content, 200
                else:
                    images = txt_to_images(fp, "tavan_listesi")
                    logging.info(f"🖼 TAVAN listesi görsellere dönüştürüldü, {len(images)} parça")
                    for idx, img in enumerate(images, start=1):
                        send_photo(chat_id, img, caption=f"🚀 Günlük TAVAN listesi (parça {idx})")
                    return "OK", 200
            else:
                logging.warning("❌ TAVAN listesi bulunamadı.")
                send_message(chat_id, "❌ TAVAN listesi bulunamadı.", mobil_mode)
                return "❌ TAVAN listesi bulunamadı.", 200

        # TEMEL komutu → Temp.xlsx
        if text_low == "temel":
            latest_folder = find_latest_matrix_folder()
            if latest_folder:
                logging.info(f"📂 TEMEL klasörü içeriği: {os.listdir(latest_folder)}")
                fp = os.path.join(latest_folder, "Temp.xlsx")
                if os.path.exists(fp):
                    logging.info(f"✅ TEMEL dosyası bulundu: {fp}")
                    send_document(chat_id, fp, caption="📊 TEMEL verisi", mobil_mode=mobil_mode)
                    return "OK", 200
            logging.warning("❌ Temp.xlsx bulunamadı.")
            send_message(chat_id, "❌ Temp.xlsx bulunamadı.", mobil_mode)
            return "❌ Temp.xlsx bulunamadı.", 200
        # TEKNİK komutu → gunluk_veri.xlsx
        if text_low == "teknik":
            latest_folder = find_latest_matrix_folder()
            if latest_folder:
                logging.info(f"📂 TEKNİK klasörü içeriği: {os.listdir(latest_folder)}")
                fp = os.path.join(latest_folder, "gunluk_veri.xlsx")
                if os.path.exists(fp):
                    logging.info(f"✅ TEKNİK dosyası bulundu: {fp}")
                    send_document(chat_id, fp, caption="📊 TEKNİK veri", mobil_mode=mobil_mode)
                    return "OK", 200
            logging.warning("❌ gunluk_veri.xlsx bulunamadı.")
            send_message(chat_id, "❌ gunluk_veri.xlsx bulunamadı.", mobil_mode)
            return "❌ gunluk_veri.xlsx bulunamadı.", 200

        # BOFA komutu → AlinanSatilan.xlsx
        if text_low == "bofa":
            latest_folder = find_latest_matrix_folder()
            if latest_folder:
                logging.info(f"📂 BOFA klasörü içeriği: {os.listdir(latest_folder)}")
                fp = os.path.join(latest_folder, "AlinanSatilan.xlsx")
                if os.path.exists(fp):
                    logging.info(f"✅ BOFA dosyası bulundu: {fp}")
                    send_document(chat_id, fp, caption="📊 BOFA verisi", mobil_mode=mobil_mode)
                    return "OK", 200
            logging.warning("❌ AlinanSatilan.xlsx bulunamadı.")
            send_message(chat_id, "❌ AlinanSatilan.xlsx bulunamadı.", mobil_mode)
            return "❌ AlinanSatilan.xlsx bulunamadı.", 200

        # BALLI KAYMAK komutu
        if text_low in ["balli_kaymak", "ballıkaymak", "balli", "kaymak"]:
            logging.info(f"📂 BALLI KAYMAK klasörü içeriği: {os.listdir(BALLI_KAYMAK_DIR)}")
            fp = find_latest_file(BALLI_KAYMAK_DIR)
            if fp:
                logging.info(f"✅ BALLI KAYMAK dosyası bulundu: {fp}")
                if mobil_mode:
                    with open(fp, "r", encoding="utf-8") as f:
                        content = f.read()
                    send_message(chat_id, content, mobil_mode)
                    return content, 200
                else:
                    images = txt_to_images(fp, "balli_kaymak_listesi")
                    logging.info(f"🖼 BALLI KAYMAK listesi görsellere dönüştürüldü, {len(images)} parça")
                    for idx, img in enumerate(images, start=1):
                        send_photo(chat_id, img, caption=f"🍯 Ballı Kaymak listesi (parça {idx})")
                    return "OK", 200
            else:
                logging.warning("❌ Ballı Kaymak listesi bulunamadı.")
                send_message(chat_id, "❌ Ballı Kaymak listesi bulunamadı.", mobil_mode)
                return "❌ Ballı Kaymak listesi bulunamadı.", 200

        # DÜNKÜ PERFORMANS komutu
        if text_low in ["performans", "dünküperformans", "dunku", "dünkü"]:
            logging.info(f"📂 PERFORMANS klasörü içeriği: {os.listdir(PERFORMANS_DIR)}")
            fp = find_latest_file(PERFORMANS_DIR)
            if fp:
                logging.info(f"✅ PERFORMANS dosyası bulundu: {fp}")
                with open(fp, "r", encoding="utf-8") as f:
                    content = f.read()
                send_message(chat_id, content, mobil_mode)
                return content, 200
            else:
                logging.warning("❌ Performans dosyası bulunamadı.")
                send_message(chat_id, "❌ Performans dosyası bulunamadı.", mobil_mode)
                return "❌ Performans dosyası bulunamadı.", 200

        # TÜM HİSSELER komutu
        if text_low in ["tum_hisseler", "tümhisseler", "tum", "tüm"]:
            logging.info(f"📂 BISTTUM klasörü içeriği: {os.listdir(BISTTUM_DIR)}")
            fp = find_latest_file(BISTTUM_DIR)
            if fp:
                logging.info(f"✅ TÜM HİSSELER dosyası bulundu: {fp}")
                with open(fp, "r", encoding="utf-8") as f:
                    content = f.read()
                send_message(chat_id, content, mobil_mode)
                return content, 200
            else:
                logging.warning("❌ Tüm hisseler dosyası bulunamadı.")
                send_message(chat_id, "❌ Tüm hisseler dosyası bulunamadı.", mobil_mode)
                return "❌ Tüm hisseler dosyası bulunamadı.", 200

        # 🔹 Yeni ekleme: Sembol isimleri ile dosya gönderme (fallback)
        symbol_file = os.path.join(TXT_DIR, f"{text_low.upper()}.txt")
        if os.path.exists(symbol_file):
            logging.info(f"✅ Sembol dosyası bulundu: {symbol_file}")
            with open(symbol_file, "r", encoding="utf-8") as f:
                content = f.read()
            send_message(chat_id, content, mobil_mode)
            return content, 200

        # Eğer hiçbir komuta uymadıysa, serbest mesajı yakala
        logging.info(f"⚠️ Hiçbir komuta uymadı, serbest mesaj: {text_low}")
        send_message(chat_id, f"Mesajını aldım: {text_low}", mobil_mode)
        return "Unhandled message", 200

    except Exception as e:
        logging.error(f"/webhook failed: {e}")
        return "Sunucu hatası", 500

# PARÇA 5/5 — Otomatik Mesaj, Scheduler ve Uygulama Çalıştırma

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


scheduler = BackgroundScheduler()
scheduler.add_job(
    otomatik_mesaj_telegram,
    "cron",
    day_of_week="mon-fri",
    hour=17,
    minute=30,
    id="otomatik_mesaj",
    replace_existing=True
)
scheduler.start()

# 🔹 Flask uygulaması çalıştırma
if __name__ == "__main__":
    logging.info("🚀 Flask uygulaması başlatılıyor...")
    flask_app.run(host="0.0.0.0", port=8020)
