# ReportBot 🤖

Google Maps'te bir işletmenin en düşük puanlı yorumunu bulup, Google Report Content formunu otomatik dolduran bir otomasyon aracı.

## Özellikler

- 🔍 Google Maps'te işletme arama
- ⭐ Review'ları çekip en düşük puanlı olanı bulma
- 📝 reportcontent.google.com formunu otomatik doldurma
- ⏸️ CAPTCHA adımında durup manuel tamamlama imkanı

## Kurulum

```bash
# Virtual environment oluştur
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Dependency'leri yükle
pip install -r requirements.txt

# Playwright browser'larını yükle
playwright install chromium
```

## Kullanım

```bash
# Basit kullanım
python run.py "İşletme Adı"

# Örnek
python run.py "Starbucks Taksim"

# Ek seçenekler
python run.py "Restaurant XYZ" --reason "Harassment" --info "Ek bilgi"

# Headless modda (Maps taraması için, form her zaman görünür)
python run.py "Cafe ABC" --headless

# Daha fazla review çek
python run.py "Hotel DEF" --max-reviews 100
```

## CLI Parametreleri

| Parametre | Kısa | Açıklama | Varsayılan |
|-----------|------|----------|------------|
| `business` | - | İşletme adı (zorunlu) | - |
| `--reason` | `-r` | Raporlama nedeni | "Spam or fake content" |
| `--info` | `-i` | Ek bilgi | "" |
| `--headless` | - | Headless mod | False |
| `--max-reviews` | `-m` | Maksimum review sayısı | 50 |

## Nasıl Çalışır

1. **İşletme Arama**: Verilen isimle Google Maps'te arama yapar
2. **Review Toplama**: İşletmenin yorumlarını toplar
3. **En Düşük Puan**: En düşük puanlı yorumu bulur
4. **Form Doldurma**: reportcontent.google.com formunu açar ve doldurur
5. **CAPTCHA Bekleme**: CAPTCHA'yı manuel tamamlamanız için bekler

## Testleri Çalıştırma

```bash
pytest tests/ -v
```

## Proje Yapısı

```
reportbot/
├── src/
│   ├── __init__.py
│   ├── main.py           # Ana CLI
│   ├── models.py         # Veri modelleri
│   ├── maps_scraper.py   # Google Maps scraper
│   ├── report_filler.py  # Form doldurma
│   └── review_finder.py  # Review bulma logic'i
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   └── test_review_finder.py
├── requirements.txt
├── pytest.ini
├── run.py
└── README.md
```

## Notlar

⚠️ **Önemli**: Bu araç eğitim amaçlıdır. Google'ın hizmet şartlarına uygun kullanın.

- CAPTCHA otomatik çözülmez, manuel tamamlamanız gerekir
- Bot tespit edilmemesi için headless mod kullanılması önerilmez
- Rate limiting'e dikkat edin
