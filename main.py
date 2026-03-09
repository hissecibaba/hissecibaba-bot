# PARÇA 1/5 — Importlar, Ortam Değişkenleri ve Temel Fonksiyonlar

# -- coding: utf-8 --
import os, re, logging, requests, datetime
import matplotlib.pyplot as plt
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BOT_TOKEN = os.getenv("BOT_TOKEN")
izinli_raw = os.getenv("IZINLI_ID_LIST", "")
IZINLI_ID_LIST = [int(id.strip()) for id in izinli_raw.split(",") if id.strip().isdigit()]
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

TXT_DIR = "/home/hissecibaba/txt_dosyalar"
AL_DIR = "/home/hissecibaba/al_listeleri"
SAT_DIR = "/home/hissecibaba/sat_listeleri"
TAVAN_DIR = "/home/hissecibaba/tavan_listeleri"
ONERI_DIR = "/home/hissecibaba/öneri"
MATRIX_DIR = "/home/hissecibaba/matriks"
AL_NEW_DIR = "/home/hissecibaba/al"
SAT_NEW_DIR = "/home/hissecibaba/sat"
BALLI_KAYMAK_DIR = "/home/hissecibaba/ballikaymak"
BISTTUM_DIR = "/home/hissecibaba/bisttum"
PERFORMANS_DIR = "/home/hissecibaba/performans"
CACHE_DIR = "/home/hissecibaba/gorsel_cache"

# 🔹 Onaylayanlar klasörü sabiti
ONAYLAYANLAR_DIR = "/home/hissecibaba/onaylayanlar"

# 🔹 Mobil izinliler klasörü sabiti (abonelik kontrolü için)
MOBIL_IZINLILER_DIR = "/home/hissecibaba/mobil_izinliler"

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
        send_message(chat_id, "❌ Dosya gönderimi başarısız.", mobil_mode)

def find_latest_file(folder_path: str) -> str:
    try:
        files = []
        for fn in os.listdir(folder_path):
            if fn.lower().endswith(".txt"):
                full_path = os.path.join(folder_path, fn)
                try:
                    # 🔹 Dosya adında IDNO_TARIHSAAT formatı varsa (ör: 5e196e7e_20260213_0354.txt)
                    parts = fn[:-4].split("_")
                    if len(parts) >= 3:
                        dt = datetime.datetime.strptime(parts[-2] + parts[-1], "%Y%m%d%H%M")
                        files.append((dt, full_path))
                    else:
                        files.append((datetime.datetime.min, full_path))
                except Exception:
                    files.append((datetime.datetime.min, full_path))
        files.sort(reverse=True)
        return files[0][1] if files else None
    except Exception:
        return None

def txt_to_images(file_path, tag, chunk_size=40):
    try:
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
            if not os.path.exists(CACHE_DIR):
                os.makedirs(CACHE_DIR)
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
    except Exception:
        return None

# PARÇA 3/5 — Upload Route ve Webhook Başlangıcı (Telegram + Flutter JSON Desteği + Loglama)

@flask_app.route("/upload", methods=["POST"])
def upload_file():
    key = request.form.get("key")
    if key != os.getenv("UPLOAD_KEY"):
        return "Unauthorized", 403
    if "file" not in request.files:
        return "No file part", 400
    file = request.files["file"]
    if file.filename == "":
        return "No selected file", 400
    target = request.form.get("target", "txt_dosyalar")
    base_dir = "/home/hissecibaba"
    save_dir = os.path.join(base_dir, target)
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    save_path = os.path.join(save_dir, file.filename)
    file.save(save_path)
    return f"✅ File uploaded to {target}", 200


@flask_app.route("/webhook", methods=["POST"])
def telegram_webhook():
    try:
        update = request.get_json(silent=True) or {}
        logging.info(f"Gelen JSON: {update}")

        if not update:
            logging.warning("Boş JSON geldi, işlem yapılmadı.")
            return "Empty JSON", 200

        message = update.get("message")
        keyword = update.get("keyword", "").lower()

        if keyword == "" and "consent_data" in update:
            keyword = "acik_riza"

        if not message and not keyword:
            return "No message", 200

        chat_id = None
        text_low = ""
        mobil_mode = False
        user_id = None

        if message:
            chat_id = message.get("chat", {}).get("id")
            text = (message.get("text") or "").strip()
            if text.startswith("MOBIL:"):
                text = text.replace("MOBIL:", "").strip()
                text_low = text.lower()
                mobil_mode = True
                user_id = str(chat_id)
                # 🔹 Abonelik kontrolü
                if not check_subscription(user_id):
                    send_message(chat_id, "⛔ Abonelik süreniz doldu.", mobil_mode)
                    return "⛔ Abonelik süreniz doldu.", 200
            else:
                text_low = text.lower()
                mobil_mode = False
                if chat_id not in IZINLI_ID_LIST:
                    send_message(chat_id, "⛔ Bu botu kullanma izniniz yok.")
                    return "Unauthorized", 200
        else:
            chat_id = update.get("consent_data", {}).get("user_id", 0)
            text_low = keyword
            mobil_mode = False

        # ✅ Açık Rıza komutu entegrasyonu
        if text_low.strip() == "acik_riza":
            try:
                data = update.get("consent_data", {})
                user_id = data.get("user_id")
                if not user_id or str(user_id).strip() == "":
                    user_id = chat_id

                consent_text = data.get("consent_text", "")
                consent_time = data.get("consent_time")
                device_id = data.get("device_id", "unknown_device")
                uuid = data.get("uuid", "unknown_uuid")

                timestamp = consent_time or (datetime.datetime.utcnow() + datetime.timedelta(hours=3)).strftime("%d.%m.%Y %H:%M")

                if not os.path.exists(ONAYLAYANLAR_DIR):
                    os.makedirs(ONAYLAYANLAR_DIR)
                if not os.path.exists(MOBIL_IZINLILER_DIR):
                    os.makedirs(MOBIL_IZINLILER_DIR)

                safe_time = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M")

                # 🔹 Onaylayanlar dosyası
                filename_onay = f"{user_id}_{safe_time}_onay.txt"
                filepath_onay = os.path.join(ONAYLAYANLAR_DIR, filename_onay)
                content_onay = (
                    "Bu dosya Açık Rıza Metninin onaylanması ile otomatik oluşturulmuştur.\n\n"
                    f"ID NO: {user_id}\n"
                    f"CIHAZ ID: {device_id}\n"
                    f"UUID: {uuid}\n"
                    f"ONAY TARİHİ VE SAATİ: {timestamp}\n\n"
                    "--- AÇIK RIZA METNİ ---\n"
                    f"{consent_text}\n"
                )
                with open(filepath_onay, "w", encoding="utf-8") as f:
                    f.write(content_onay)

                # 🔹 Mobil izinliler dosyası (subscription_data desteği)
                subscription_data = update.get("subscription_data", {})
                logging.info(f"Subscription data: {subscription_data}")  # 🔹 log ekledik

                id_no = subscription_data.get("id_no", user_id)
                start_date = subscription_data.get("start_date", timestamp)
                end_date = subscription_data.get("end_date") or (datetime.datetime.utcnow() + datetime.timedelta(days=7)).strftime("%d.%m.%Y %H:%M")

                filename_izin = f"{id_no}_{safe_time}_izin.txt"
                filepath_izin = os.path.join(MOBIL_IZINLILER_DIR, filename_izin)
                content_izin = (
                    f"ID NO: {id_no}\n"
                    f"START_DATE: {start_date}\n"
                    f"END_DATE: {end_date}\n"
                )
                with open(filepath_izin, "w", encoding="utf-8") as f:
                    f.write(content_izin)

                logging.info("✅ Onay ve mobil izin dosyaları başarıyla yazıldı.")
                send_message(chat_id, "✅ Açık Rıza ve abonelik kaydedildi.", mobil_mode)
                return "Açık Rıza ve abonelik kaydedildi", 200
            except Exception as e:
                logging.error(f"Açık Rıza kaydı hatası: {e}")
                return "Açık Rıza kaydı hatası", 500

        # AL komutu
        if text_low == "al":
            fp = find_latest_file(AL_NEW_DIR if mobil_mode else AL_DIR)
            if fp:
                if mobil_mode:
                    with open(fp, "r", encoding="utf-8") as f:
                        content = f.read()
                    send_message(chat_id, content, mobil_mode)
                    return content, 200
                else:
                    images = txt_to_images(fp, "al_listesi")
                    for idx, img in enumerate(images, start=1):
                        send_photo(chat_id, img, caption=f"📈 Günlük AL listesi (parça {idx})")
                    return "OK", 200
            else:
                send_message(chat_id, "❌ AL listesi bulunamadı.")
                return "❌ AL listesi bulunamadı.", 200

        # SAT komutu
        if text_low == "sat":
            fp = find_latest_file(SAT_NEW_DIR if mobil_mode else SAT_DIR)
            if fp:
                if mobil_mode:
                    with open(fp, "r", encoding="utf-8") as f:
                        content = f.read()
                    send_message(chat_id, content, mobil_mode)
                    return content, 200
                else:
                    images = txt_to_images(fp, "sat_listesi")
                    for idx, img in enumerate(images, start=1):
                        send_photo(chat_id, img, caption=f"📉 Günlük SAT listesi (parça {idx})")
                    return "OK", 200
            else:
                send_message(chat_id, "❌ SAT listesi bulunamadı.")
                return "❌ SAT listesi bulunamadı.", 200

# PARÇA 4/5 — Diğer Komutlar (ÖNERİ, TAVAN, TEMEL, TEKNİK, BOFA, BALLI KAYMAK, PERFORMANS, TÜM HİSSELER)
        # En güncel matriks klasörünü bul
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
            except Exception:
                return None

        # ÖNERİ komutu
        if any(x in text_low for x in ["öneri", "oneri", "önerı", "onerı"]):
            fp = find_latest_file(ONERI_DIR)
            if fp:
                if mobil_mode:
                    with open(fp, "r", encoding="utf-8") as f:
                        content = f.read()
                    send_message(chat_id, content, mobil_mode)
                    return content, 200
                else:
                    images = txt_to_images(fp, "öneri_listesi")
                    for idx, img in enumerate(images, start=1):
                        send_photo(chat_id, img, caption=f"💡 Günlük ÖNERİ listesi (parça {idx})")
                    return "OK", 200
            else:
                send_message(chat_id, "❌ ÖNERİ listesi bulunamadı.", mobil_mode)
                return "❌ ÖNERİ listesi bulunamadı.", 200

        # TAVAN komutu
        if text_low == "tavan":
            fp = find_latest_file(TAVAN_DIR)
            if fp:
                if mobil_mode:
                    with open(fp, "r", encoding="utf-8") as f:
                        content = f.read()
                    send_message(chat_id, content, mobil_mode)
                    return content, 200
                else:
                    images = txt_to_images(fp, "tavan_listesi")
                    for idx, img in enumerate(images, start=1):
                        send_photo(chat_id, img, caption=f"🚀 Günlük TAVAN listesi (parça {idx})")
                    return "OK", 200
            else:
                send_message(chat_id, "❌ TAVAN listesi bulunamadı.", mobil_mode)
                return "❌ TAVAN listesi bulunamadı.", 200

        # TEMEL komutu → Temp.xlsx
        if text_low == "temel":
            latest_folder = find_latest_matrix_folder()
            if latest_folder:
                fp = os.path.join(latest_folder, "Temp.xlsx")
                if os.path.exists(fp):
                    send_document(chat_id, fp, caption="📊 TEMEL verisi", mobil_mode=mobil_mode)
                    return "OK", 200
            send_message(chat_id, "❌ Temp.xlsx bulunamadı.", mobil_mode)
            return "❌ Temp.xlsx bulunamadı.", 200

        # TEKNİK komutu → gunluk_veri.xlsx
        if text_low == "teknik":
            latest_folder = find_latest_matrix_folder()
            if latest_folder:
                fp = os.path.join(latest_folder, "gunluk_veri.xlsx")
                if os.path.exists(fp):
                    send_document(chat_id, fp, caption="📊 TEKNİK veri", mobil_mode=mobil_mode)
                    return "OK", 200
            send_message(chat_id, "❌ gunluk_veri.xlsx bulunamadı.", mobil_mode)
            return "❌ gunluk_veri.xlsx bulunamadı.", 200

        # BOFA komutu → AlinanSatilan.xlsx
        if text_low == "bofa":
            latest_folder = find_latest_matrix_folder()
            if latest_folder:
                fp = os.path.join(latest_folder, "AlinanSatilan.xlsx")
                if os.path.exists(fp):
                    send_document(chat_id, fp, caption="📊 BOFA verisi", mobil_mode=mobil_mode)
                    return "OK", 200
            send_message(chat_id, "❌ AlinanSatilan.xlsx bulunamadı.", mobil_mode)
            return "❌ AlinanSatilan.xlsx bulunamadı.", 200

        # BALLI KAYMAK komutu
        if text_low in ["balli_kaymak", "ballıkaymak", "balli", "kaymak"]:
            fp = find_latest_file(BALLI_KAYMAK_DIR)
            if fp:
                if mobil_mode:
                    with open(fp, "r", encoding="utf-8") as f:
                        content = f.read()
                    send_message(chat_id, content, mobil_mode)
                    return content, 200
                else:
                    images = txt_to_images(fp, "balli_kaymak_listesi")
                    for idx, img in enumerate(images, start=1):
                        send_photo(chat_id, img, caption=f"🍯 Ballı Kaymak listesi (parça {idx})")
                    return "OK", 200
            else:
                send_message(chat_id, "❌ Ballı Kaymak listesi bulunamadı.", mobil_mode)
                return "❌ Ballı Kaymak listesi bulunamadı.", 200

        # DÜNKÜ PERFORMANS komutu
        if text_low in ["performans", "dünküperformans", "dunku", "dünkü"]:
            fp = find_latest_file(PERFORMANS_DIR)
            if fp:
                with open(fp, "r", encoding="utf-8") as f:
                    content = f.read()
                send_message(chat_id, content, mobil_mode)
                return content, 200
            else:
                send_message(chat_id, "❌ Performans dosyası bulunamadı.", mobil_mode)
                return "❌ Performans dosyası bulunamadı.", 200

        # TÜM HİSSELER komutu
        if text_low in ["tum_hisseler", "tümhisseler", "tum", "tüm"]:
            fp = find_latest_file(BISTTUM_DIR)
            if fp:
                with open(fp, "r", encoding="utf-8") as f:
                    content = f.read()
                send_message(chat_id, content, mobil_mode)
                return content, 200
            else:
                send_message(chat_id, "❌ Tüm hisseler dosyası bulunamadı.", mobil_mode)
                return "❌ Tüm hisseler dosyası bulunamadı.", 200

        # 🔹 Yeni ekleme: Sembol isimleri ile dosya gönderme (fallback)
        symbol_file = os.path.join(TXT_DIR, f"{text_low.upper()}.txt")
        if os.path.exists(symbol_file):
            with open(symbol_file, "r", encoding="utf-8") as f:
                content = f.read()
            send_message(chat_id, content, mobil_mode)
            return content, 200

        # Eğer hiçbir komuta uymadıysa, serbest mesajı yakala
        send_message(chat_id, f"Mesajını aldım: {text_low}", mobil_mode)
        return "Unhandled message", 200

    except Exception as e:
        logging.error(f"/webhook failed: {e}")
        return "Sunucu hatası", 500

# PARÇA 5/5 — Otomatik Mesaj, Scheduler ve Uygulama Çalıştırma

def otomatik_mesaj_telegram():
    for chat_id in IZINLI_ID_LIST:
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
        files = [fn for fn in os.listdir(MOBIL_IZINLILER_DIR) if fn.startswith(user_id)]
        if not files:
            return False
        files.sort(reverse=True)
        filepath = os.path.join(MOBIL_IZINLILER_DIR, files[0])
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        end_line = [ln for ln in lines if ln.startswith("END_DATE")]
        if not end_line:
            return False
        end_date_str = end_line[0].split(":", 1)[1].strip()
        end_date = datetime.datetime.strptime(end_date_str, "%d.%m.%Y %H:%M")
        now = datetime.datetime.utcnow() + datetime.timedelta(hours=3)
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
    flask_app.run(host="0.0.0.0", port=8020)

