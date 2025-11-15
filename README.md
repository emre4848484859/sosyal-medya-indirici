# Sosyal Medya İndirici Botu

Telegram üzerinden TikTok ve X (Twitter) içeriklerini indirebilen, gruplarda ve özel sohbetlerde kullanılmaya hazır, genişletilebilir bir bot.

## Özellikler
- Sohbete bırakılan TikTok ve X (Twitter) linklerini otomatik olarak algılama
- Telegram mesaj linklerinden (public veya özel kanal/grup) medya çekme ve kullanıcıya geri gönderme
- TikTok videoları, story'leri ve fotoğraf albümlerini tek istekle ayırt edip gönderme
- VXTwitter API üzerinden X (Twitter) fotoğrafları, GIF'leri ve videolarını indirme
- Albümlerde Telegram sınırlarını aşmamak için 10'lu medya grupları ve artan görselleri tekil mesajlarla tamamlama
- Hem özel sohbetlerde hem de gruplarda güvenli kullanım
- TikTok dışındaki platformlar için modüler servis mimarisi

## Gereksinimler
- Python 3.11+
- Telegram bot token ([@BotFather](https://t.me/BotFather) üzerinden alınır)
- Telegram API kimlik bilgileri (`TELETHON_API_ID`, `TELETHON_API_HASH`, `TELETHON_SESSION_STRING`) – Telegram linklerinden medya çekmek için zorunludur

## Kurulum
```bash
# bağımlılıkları kur
pip install -e .

# ortam değişkenlerini hazırla
cp .env.example .env
# .env dosyasındaki BOT_TOKEN, BOT_MODE vb. alanları doldurun
# Telegram link özelliği için TELETHON_API_ID, TELETHON_API_HASH
# ve TELETHON_SESSION_STRING değerlerini girin

# botu çalıştır
python -m bot.main
```

> Varsayılan API uçları:
> - TikTok: `TIKWM_API_URL=https://tikwm.com/api/`
> - X (Twitter): `TWITTER_API_BASE_URL=https://api.vxtwitter.com`
>
> İhtiyacınıza göre bu değerleri `.env` dosyasında güncelleyebilirsiniz.

### Çalıştırma Modları
- `BOT_MODE=polling`: Lokal geliştirme için idealdir, Telegram API’sine long-polling ile bağlanır.
- `BOT_MODE=webhook`: Railway gibi kalıcı olarak yayımlanan servislerde önerilir. `WEBHOOK_BASE_URL` ve isteğe bağlı `WEBHOOK_SECRET` değerlerini tanımlayın.

## Komutlar
- `/start` – Botu başlatır, kısa bilgilendirme yapar.
- `/help` – Nasıl kullanacağınızı ve ipuçlarını gösterir.

## Mimari
```
src/bot
├── config.py        # .env tabanlı ayarlar
├── logging.py       # standart logging konfigurasyonu
├── main.py          # aiogram Dispatcher ve router kurulumu
├── handlers/
│   ├── base.py      # /start, /help vb.
│   ├── tiktok.py    # TikTok komutları ve iş mantığı
│   ├── twitter.py   # X (Twitter) linklerini işler
│   └── telegram.py  # Telegram linklerinden medya çeker
├── services/
│   ├── tiktok.py            # tikwm tabanlı indirme servisi
│   ├── twitter.py           # VXTwitter istemcisi
│   └── telegram_fetcher.py  # Telethon tabanlı Telegram mesaj yardımcıları
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
- Snapchat / Facebook içerikleri
- Kuyruk sistemi (Redis) ile yüksek hacimli istek yönetimi
