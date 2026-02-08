# ReportBot - Windows Kurulum Rehberi

Bu rehber, ReportBot'u Windows bilgisayarında çalıştırılabilir hale getirmek için adım adım talimatlar içerir.

---

## 📋 Gereksinimler

- Windows 10 veya 11
- İnternet bağlantısı
- ~500 MB boş disk alanı

---

## 🚀 Kurulum Adımları

### Adım 1: Python Kur

1. https://www.python.org/downloads/ adresine git
2. **"Download Python 3.12.x"** butonuna tıkla
3. İndirilen dosyayı çalıştır
4. ⚠️ **ÖNEMLİ:** Kurulum ekranında **"Add Python to PATH"** kutucuğunu işaretle!
5. "Install Now" tıkla

### Adım 2: Projeyi İndir

1. Projenin ZIP dosyasını indir (sana gönderilen dosya)
2. ZIP'i bir klasöre çıkart (örn: `C:\ReportBot`)

### Adım 3: Komut İstemi Aç

1. Windows tuşuna bas
2. "cmd" yaz
3. "Komut İstemi" veya "Command Prompt" aç

### Adım 4: Proje Klasörüne Git

```cmd
cd C:\ReportBot
```
(Klasör yolunu kendi çıkarttığın yere göre değiştir)

### Adım 5: Virtual Environment Oluştur

```cmd
python -m venv venv
venv\Scripts\activate
```

### Adım 6: Bağımlılıkları Kur

```cmd
pip install -r requirements.txt
```

### Adım 7: Playwright Browser'ları Kur

```cmd
playwright install chromium
```

### Adım 8: Executable Oluştur

```cmd
python build_windows.py
```

---

## ✅ Kurulum Tamamlandı!

Executable dosyan şurada oluşacak:
```
C:\ReportBot\dist\ReportBot.exe
```

---

## 💡 Kullanım

### Komut İstemi ile:

```cmd
# Tek URL ile çalıştır:
ReportBot.exe --url "https://maps.app.goo.gl/xxx"

# Excel dosyası ile çalıştır:
ReportBot.exe --csv urls.xlsx

# Yardım:
ReportBot.exe --help
```

### Veya doğrudan Python ile (executable olmadan):

```cmd
cd C:\ReportBot
venv\Scripts\activate
python run.py --url "https://maps.app.goo.gl/xxx"
```

---

## ⚠️ Sorun Giderme

### "Python bulunamadı" hatası
- Python'u yeniden kur ve "Add Python to PATH" seçeneğini işaretlediğinden emin ol

### "playwright" komutu çalışmıyor
- Virtual environment aktif mi kontrol et: `venv\Scripts\activate`

### Antivirus uyarısı
- Windows Defender bazen PyInstaller ile oluşturulan dosyaları yanlışlıkla tehlikeli olarak işaretleyebilir
- Güvenli olduğunu biliyorsan, "İzin ver" veya "Exclude" seçeneğini kullan

---

## 📞 Destek

Sorun yaşarsan bana ulaş!
