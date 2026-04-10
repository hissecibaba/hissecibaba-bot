# PARÇA 1: Importlar, Ortam Değişkenleri ve Temel Yardımcı Fonksiyonlar
# -- coding: utf-8 --
import os, re, logging, requests, datetime, uuid, pytz, shutil, subprocess
import matplotlib.pyplot as plt
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from PIL import Image, ImageDraw, ImageFont

# Log ayarları
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Ortam Değişkenleri
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

def find_id_no_by_device(device_id: str):
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

def find_latest_file(folder_path: str) -> str:
    try:
        if not os.path.exists(folder_path): return None
        files = []
        for fn in os.listdir(folder_path):
            if fn.lower().endswith(".txt"):
                full_path = os.path.join(folder_path, fn)
                date_str = fn.replace(".txt", "")
                try:
                    try:
                        dt = datetime.datetime.strptime(date_str, "%d.%m.%Y")
                    except ValueError:
                        dt = datetime.datetime.strptime(date_str, "%d.%m.%Y_%H%M")
                    files.append((dt, full_path))
                except Exception:
                    continue
        files.sort(reverse=True, key=lambda x: x[0])
        return files[0][1] if files else None
    except Exception as e:
        logging.error(f"find_latest_file failed: {e}")
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
            if not os.path.exists(CACHE_DIR): os.makedirs(CACHE_DIR)
            img_path = os.path.join(CACHE_DIR, f"{tag}_{idx}.png")
            fig.savefig(img_path, bbox_inches="tight")
            plt.close(fig)
            image_paths.append(img_path)
        return image_paths
    except Exception as e:
        logging.error(f"txt_to_images failed: {e}")
        return []

def send_document(chat_id: int, file_path: str, caption: str = None, mobil_mode: bool = False):
    try:
        if not os.path.exists(file_path):
            return (jsonify({"error": "❌ Dosya bulunamadı."}), 200) if mobil_mode else ("❌ Dosya bulunamadı.", 200)
        with open(file_path, "rb") as f:
            files = {"document": f}
            data = {"chat_id": chat_id, "disable_notification": mobil_mode}
            if caption: data["caption"] = caption
            requests.post(f"{TELEGRAM_API}/sendDocument", data=data, files=files, timeout=30)
        return (jsonify({"content": "📄 Gönderildi"}), 200) if mobil_mode else ("OK", 200)
    except Exception as e:
        logging.error(f"send_document failed: {e}")
        return (jsonify({"error": "Hata"}), 500) if mobil_mode else ("Hata", 500)

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
                except: continue
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

# PARÇA 2: Yetkilendirme (Consent) Kontrolü ve Matriks Klasör Yönetimi
# --- 1-B Fonksiyonlar (Devam) ---

def find_latest_matrix_folder():
    try:
        if not os.path.exists(MATRIX_DIR):
            return None
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

# --- 1-C Route'lar (API & Webhook Başlangıcı) ---

@flask_app.route("/check", methods=["GET", "POST"])
def check_consent():
    """Mobil uygulamanın giriş yetkisini kontrol eder."""
    try:
        if request.method == "GET":
            return jsonify({"status": "ok", "info": "Hissecibaba Consent API"}), 200

        data = request.get_json(silent=True) or {}
        device_id = data.get("device_id")
        if not device_id:
            return jsonify({"authorized": "false", "reason": "no_device_id"}), 400

        id_no = find_id_no_by_device(device_id)
        if not id_no:
            return jsonify({"authorized": "false", "reason": "device_not_registered"}), 200

        izin_file = os.path.join(MOBIL_IZINLILER_DIR, f"{id_no}.txt")
        if not os.path.exists(izin_file):
            return jsonify({"authorized": "false", "reason": "no_permission_file"}), 200

        with open(izin_file, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
            end_line = next((l for l in lines if l.startswith("END_DATE:")), None)
            if not end_line:
                return jsonify({"authorized": "false", "reason": "invalid_file_format"}), 200
            
            end_date_str = end_line.replace("END_DATE:", "").strip()
            # Örn format: 24.06.2025 12:00 PM
            end_date = datetime.datetime.strptime(end_date_str, "%d.%m.%Y %I:%M %p")

        if datetime.datetime.now() > end_date:
            return jsonify({"authorized": "false", "expired": "true", "end_date": end_date_str}), 200

        return jsonify({"authorized": "true", "end_date": end_date_str}), 200
    except Exception as e:
        logging.error(f"/check hatası: {e}")
        return jsonify({"error": str(e)}), 500

def normalize_tr(text: str) -> str:
    """Türkçe karakterleri normalize eder."""
    tr_map = str.maketrans("çğıöşü", "cgiosu")
    return text.lower().translate(tr_map).strip()

# PARÇA 3: Webhook Girişi ve Dosya Bazlı Komutlar (Öneri, Tavan, Temel, Teknik, Bofa)

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    """Telegram'dan gelen mesajları karşılar ve yanıtlar."""
    try:
        data = request.get_json(silent=True) or {}
        
        # Mobil veya Telegram ayrımı
        mobil_mode = data.get("mobil_mode", False)
        
        if mobil_mode:
            msg_text = data.get("message", "")
            chat_id = data.get("chat_id", 0)
        else:
            if "message" not in data:
                return "OK", 200
            msg = data["message"]
            chat_id = msg.get("chat", {}).get("id", 0)
            msg_text = msg.get("text", "")

        if not msg_text:
            return "OK", 200

        text_norm = normalize_tr(msg_text)

        # 🔹 1. YETKİ KONTROLÜ (Telegram için)
        if not mobil_mode and chat_id not in IZINLI_ID_LIST:
            send_message(chat_id, "❌ Bu botu kullanma yetkiniz yok.")
            return "OK", 200

        # 🔹 2. KOMUTLAR (Hata veren try bloğu burada başlıyor)
        try:
            # --- ÖNERİ ---
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

            # --- TAVAN ---
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

            # --- TEMEL ---
            if text_norm == "temel":
                latest_folder = find_latest_matrix_folder()
                if latest_folder:
                    fp = os.path.join(latest_folder, "Temp.xlsx")
                    if os.path.exists(fp):
                        if mobil_mode:
                            return jsonify({"content": "Excel dosyası mobil modda metin olarak okunamaz, dosya olarak gönderilmelidir."}), 200
                        else:
                            send_document(chat_id, fp, caption="📊 TEMEL verisi", mobil_mode=mobil_mode)
                            return "OK", 200
                return jsonify({"error": "❌ Temp.xlsx bulunamadı."}), 200 if mobil_mode else ("❌ Temp.xlsx bulunamadı.", 200)

            # --- TEKNİK ---
            if text_norm == "teknik":
                latest_folder = find_latest_matrix_folder()
                if latest_folder:
                    fp = os.path.join(latest_folder, "gunluk_veri.xlsx")
                    if os.path.exists(fp):
                        if mobil_mode:
                            return jsonify({"content": "Excel dosyası mobil modda metin olarak okunamaz."}), 200
                        else:
                            send_document(chat_id, fp, caption="📊 TEKNİK veri", mobil_mode=mobil_mode)
                            return "OK", 200
                return jsonify({"error": "❌ gunluk_veri.xlsx bulunamadı."}), 200 if mobil_mode else ("❌ gunluk_veri.xlsx bulunamadı.", 200)

            # --- BOFA ---
            if text_norm == "bofa":
                latest_folder = find_latest_matrix_folder()
                if latest_folder:
                    fp = os.path.join(latest_folder, "AlinanSatilan.xlsx")
                    if os.path.exists(fp):
                        if mobil_mode:
                            return jsonify({"content": "Excel dosyası mobil modda metin olarak okunamaz."}), 200
                        else:
                            send_document(chat_id, fp, caption="📊 BOFA verisi", mobil_mode=mobil_mode)
                            return "OK", 200
                return jsonify({"error": "❌ AlinanSatilan.xlsx bulunamadı."}), 200 if mobil_mode else ("❌ AlinanSatilan.xlsx bulunamadı.", 200)

# PARÇA 4: Özel Listeler (Ballı Kaymak, Destek, Bist Tüm) ve AL/SAT Komutları

            # --- BALLI KAYMAK ---
            if text_norm == "balli kaymak":
                fp = find_latest_file(BALLI_KAYMAK_DIR)
                if fp:
                    with open(fp, "r", encoding="utf-8") as f: content = f.read()
                    if mobil_mode: return jsonify({"content": content}), 200
                    for img in txt_to_images(fp, "ballikaymak"): send_photo(chat_id, img)
                    return "OK", 200
                return jsonify({"error": "❌ Ballı Kaymak listesi bulunamadı."}), 200 if mobil_mode else ("❌ Liste bulunamadı.", 200)

            # --- DESTEK / DIRENC ---
            if text_norm in ["destek", "direnc"]:
                fp = find_latest_file(DESTEK_DIRENC_DIR)
                if fp:
                    with open(fp, "r", encoding="utf-8") as f: content = f.read()
                    if mobil_mode: return jsonify({"content": content}), 200
                    for img in txt_to_images(fp, "destek_direnc"): send_photo(chat_id, img)
                    return "OK", 200
                return jsonify({"error": "❌ Destek/Direnç listesi bulunamadı."}), 200 if mobil_mode else ("❌ Liste bulunamadı.", 200)

            # --- BIST TUM ---
            if text_norm == "bist tum":
                fp = find_latest_file(BISTTUM_DIR)
                if fp:
                    with open(fp, "r", encoding="utf-8") as f: content = f.read()
                    if mobil_mode: return jsonify({"content": content}), 200
                    for img in txt_to_images(fp, "bisttum"): send_photo(chat_id, img)
                    return "OK", 200
                return jsonify({"error": "❌ BIST TUM listesi bulunamadı."}), 200 if mobil_mode else ("❌ Liste bulunamadı.", 200)

            # --- PERFORMANS ---
            if text_norm == "performans":
                fp = find_latest_file(PERFORMANS_DIR)
                if fp:
                    with open(fp, "r", encoding="utf-8") as f: content = f.read()
                    if mobil_mode: return jsonify({"content": content}), 200
                    for img in txt_to_images(fp, "performans"): send_photo(chat_id, img)
                    return "OK", 200
                return jsonify({"error": "❌ Performans listesi bulunamadı."}), 200 if mobil_mode else ("❌ Liste bulunamadı.", 200)

            # --- AL KOMUTLARI ---
            if text_norm == "al":
                # Mobil ve Telegram için farklı klasörlerden son dosyayı çekiyoruz
                target_dir = AL_MOBIL_DIR if mobil_mode else AL_DIR
                fp = find_latest_file(target_dir)
                if fp:
                    with open(fp, "r", encoding="utf-8") as f: content = f.read()
                    if mobil_mode: return jsonify({"content": content}), 200
                    for img in txt_to_images(fp, "al_listesi"): send_photo(chat_id, img)
                    return "OK", 200
                return jsonify({"error": "❌ AL listesi bulunamadı."}), 200 if mobil_mode else ("❌ Liste bulunamadı.", 200)

            # --- SAT KOMUTLARI ---
            if text_norm == "sat":
                target_dir = SAT_MOBIL_DIR if mobil_mode else SAT_DIR
                fp = find_latest_file(target_dir)
                if fp:
                    with open(fp, "r", encoding="utf-8") as f: content = f.read()
                    if mobil_mode: return jsonify({"content": content}), 200
                    for img in txt_to_images(fp, "sat_listesi"): send_photo(chat_id, img)
                    return "OK", 200
                return jsonify({"error": "❌ SAT listesi bulunamadı."}), 200 if mobil_mode else ("❌ Liste bulunamadı.", 200)

# PARÇA 5: Sembol Araması, Webhook Kapanışı ve Sunucu Başlatma

            # --- SEMBOL / HİSSE ARAMASI ---
            # Eğer yukarıdaki komutlardan hiçbiri değilse, metni bir hisse sembolü olarak ara
            symbol_file = os.path.join(TXT_DIR, f"{text_norm}.txt")
            if os.path.exists(symbol_file):
                with open(symbol_file, "r", encoding="utf-8") as f:
                    content = f.read()
                if mobil_mode:
                    return jsonify({"content": content}), 200
                else:
                    send_message(chat_id, content)
                    return "OK", 200

            # --- FALLBACK (HİÇBİRİ DEĞİLSE) ---
            if not mobil_mode:
                # Telegram kullanıcılarına bilinmeyen komut uyarısı (isteğe bağlı)
                # send_message(chat_id, "❓ Komut anlaşılamadı. Lütfen geçerli bir komut veya hisse kodu giriniz.")
                pass
            
            # Fonksiyonun sonuna ulaşıldığında başarı dön
            if mobil_mode:
                return jsonify({"content": "Komut işlendi."}), 200
            return "OK", 200

        except Exception as e:
            # İŞTE BURASI: 464. satır civarındaki hatayı tamir eden iç except bloğu
            logging.error(f"İç Webhook Hatası: {e}")
            if mobil_mode:
                return jsonify({"error": f"İşlem hatası: {str(e)}"}), 500
            else:
                send_message(chat_id, f"⚠️ Bir hata oluştu: {str(e)}")
                return "OK", 200

    except Exception as e:
        # Dış Webhook Hatası (JSON ayrıştırma vb.)
        logging.error(f"Dış Webhook Hatası: {e}")
        return "OK", 200

# --- 1-D Sunucu Kontrolleri & Zamanlanmış Görevler ---

def keep_alive():
    """Render servisinin uyumasını engeller."""
    try:
        url = "https://hissecibaba-bot.onrender.com/check"
        requests.get(url, timeout=10)
    except:
        pass

def sync_to_github():
    """GitHub senkronizasyonu (Özel deploy mantığınız)."""
    try:
        repo_url = os.getenv("GITHUB_REPO")
        token = os.getenv("GITHUB_TOKEN")
        if not repo_url or not token:
            logging.warning("GitHub bilgileri eksik, sync atlanıyor.")
            return
        
        repo_dir = "/tmp/hissecibaba_sync"
        if os.path.exists(repo_dir):
            shutil.rmtree(repo_dir)
        
        auth_url = repo_url.replace("https://", f"https://{token}@")
        subprocess.run(["git", "clone", auth_url, repo_dir], check=True)
        subprocess.run(["rsync", "-a", "--delete", f"{BASE_DIR}/", repo_dir], check=True)
        subprocess.run(["git", "-C", repo_dir, "add", "."], check=True)
        subprocess.run(["git", "-C", repo_dir, "commit", "-m", "Auto Sync"], check=True)
        subprocess.run(["git", "-C", repo_dir, "push"], check=True)
        logging.info("✅ GitHub senkronizasyonu tamamlandı.")
    except Exception as e:
        logging.error(f"Sync failed: {e}")

# 🔹 Scheduler Ayarları
scheduler = BackgroundScheduler()
istanbul_tz = pytz.timezone("Europe/Istanbul")

# Her 5 dakikada bir ping
scheduler.add_job(keep_alive, "interval", minutes=5, id="ping_job")
# Her akşam 20:45'te senkronizasyon
scheduler.add_job(sync_to_github, "cron", hour=20, minute=45, timezone=istanbul_tz, id="sync_job")

scheduler.start()

# --- SUNUCUYU BAŞLAT ---
if __name__ == "__main__":
    # Render'ın atadığı PORT'u al, yoksa 8020 kullan
    port = int(os.getenv("PORT", 8020))
    flask_app.run(host="0.0.0.0", port=port)
