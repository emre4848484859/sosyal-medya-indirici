# Sosyal Medya İndirici Botu

Telegram üzerinden TikTok (ve gelecekte diğer platformlar) içeriklerini indirebilen, gruplarda ve özel sohbetlerde kullanılmaya hazır, genişletilebilir bir bot.

## Özellikler
- `/tiktok_video <link>` ile filigransız video indirme ve gönderme
- `/tiktok_story <link>` ile hikâye/vaka indirme
- `/tiktok_photos <link>` ile fotoğraf/albüm gönderimi (10'lu gruplar halinde)
- Hem özel sohbetlerde hem de gruplarda güvenli kullanım
- TikTok dışındaki platformlar için modüler servis mimarisi

## Gereksinimler
- Python 3.11+
- Telegram bot token ([@BotFather](https://t.me/BotFather) üzerinden alınır)

## Kurulum
```bash
# bağımlılıkları kur
pip install -e .

# ortam değişkenlerini hazırla
cp .env.example .env
# .env dosyasındaki BOT_TOKEN, BOT_MODE vb. alanları doldurun

# botu çalıştır
python -m bot.main
```

> Varsayılan olarak TikTok medyaları `https://tikwm.com/api/` servisi üzerinden çekilir. Farklı bir servis kullanmak isterseniz `.env` içindeki `TIKWM_API_URL` değerini güncelleyin.

### Çalıştırma Modları
- `BOT_MODE=polling`: Lokal geliştirme için idealdir, Telegram API’sine long-polling ile bağlanır.
- `BOT_MODE=webhook`: Railway gibi kalıcı olarak yayımlanan servislerde önerilir. `WEBHOOK_BASE_URL` ve isteğe bağlı `WEBHOOK_SECRET` değerlerini tanımlayın.

## Komutlar
- `/start` – Botu başlatır, kısa bilgilendirme yapar.
- `/help` – Komutlar ve ipuçlarını gösterir.
- `/tiktok_video <link>` – Videoyu indirir ve yollar.
- `/tiktok_story <link>` – Hikâyeyi indirir (video olarak gönderilir).
- `/tiktok_photos <link>` – Fotoğraf/albümü Telegram sınırları nedeniyle otomatik olarak 10 adetlik paketlere ayırarak gönderir.

## Mimari
```
src/bot
├── config.py        # .env tabanlı ayarlar
├── logging.py       # standart logging konfigurasyonu
├── main.py          # aiogram Dispatcher ve router kurulumu
├── handlers/
│   ├── base.py      # /start, /help vb.
│   └── tiktok.py    # TikTok komutları ve iş mantığı
├── services/
│   └── tiktok.py    # tikwm tabanlı indirme servisi
└── utils/
    └── chunk.py     # medya gruplarını bölme yardımcıları
```

Yeni bir platform eklemek için `services/` altında yeni bir istemci ve `handlers/` altında ilgili komutları tanımlamanız yeterli. Router mimarisi her servisi modüler tutar.

## Railway Üzerine Dağıtım
1. Railway hesabınızda yeni bir “Service” oluşturun ve bu repo’yu bağlayın (veya `railway up` komutuyla push edin). Proje, kökteki Dockerfile ile otomatik container olarak derlenir.
2. Ortam değişkenlerini ayarlayın:
   - `BOT_TOKEN`: BotFather’dan aldığınız token.
   - `BOT_MODE=webhook`
   - `WEBHOOK_BASE_URL=https://<projeniz>.up.railway.app`
   - `WEBHOOK_PATH=/webhook/<rastgele>` (Telegram token’ınızı ifşa etmeyen bir yol seçin)
   - `WEBHOOK_SECRET` (opsiyonel fakat güvenlik için önerilir)
3. Railway `PORT` değişkenini otomatik sağlar; bot sunucusu `0.0.0.0:PORT` üzerinde webhook dinleyicisini ayağa kaldırır.
4. Deploy tamamlandığında Telegram tarafında webhook kendiliğinden ayarlanır; botunuz hazır olur.

## Yol Haritası
- Instagram Reels/Stories indirme
- YouTube kısa & uzun video desteği
- Reddit ve X (Twitter) içerikleri
- Kuyruk sistemi (Redis) ile yüksek hacimli istek yönetimi
