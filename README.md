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
# .env dosyasındaki BOT_TOKEN alanını doldurun

# botu çalıştır
python -m bot.main
```

> Varsayılan olarak TikTok medyaları `https://tikwm.com/api/` servisi üzerinden çekilir. Farklı bir servis kullanmak isterseniz `.env` içindeki `TIKWM_API_URL` değerini güncelleyin.

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

## Yol Haritası
- Instagram Reels/Stories indirme
- YouTube kısa & uzun video desteği
- Reddit ve X (Twitter) içerikleri
- Kuyruk sistemi (Redis) ile yüksek hacimli istek yönetimi
