# Sosyal Medya İndirici Botu

TikTok ve X (Twitter) linklerini anında yakalayıp Telegram sohbetlerinde indirilebilir medyaya çeviren, modüler ve kolay konfigüre edilebilen bir bot. Gruplarda, kanallarda ve özel sohbetlerde sorunsuz çalışır.

## Öne Çıkan Özellikler
- Sohbete bırakılan TikTok ya da X linklerini otomatik tanıma
- Telegram mesaj linklerinden (public/özel) medya alma ve kullanıcıya geri gönderme
- TikTok video, story ve albüm içeriklerini tek adımda ayırt etme
- VXTwitter API ile fotoğraf, GIF ve videoları indirme
- Büyük albümlerde Telegram limitlerini aşmadan akıllı parçalara bölme
- Servis bazlı mimari sayesinde yeni platformları dakikalar içinde ekleyebilme

## Gereksinimler
- Python 3.11+
- Telegram bot token ([@BotFather](https://t.me/BotFather))
- Telegram API bilgileri (`TELETHON_API_ID`, `TELETHON_API_HASH`, `TELETHON_SESSION_STRING`) – Telegram linklerinden medya çekmek için zorunludur

## Hızlı Kurulum
```bash
pip install -e .
cp .env.example .env
# .env dosyasındaki BOT_TOKEN, BOT_MODE ve Telethon bilgilerini doldurun

python -m bot.main
```

### Temel Ortam Değişkenleri
| Değişken | Açıklama |
| --- | --- |
| `BOT_TOKEN` | BotFather’dan alınan token |
| `BOT_MODE` | `polling` (lokal) veya `webhook` (production) |
| `WEBHOOK_BASE_URL`, `WEBHOOK_SECRET` | Webhook modunu seçtiğinizde zorunlu/isteğe bağlı alanlar |
| `TIKWM_API_URL` | Varsayılan: `https://tikwm.com/api/` |
| `TWITTER_API_BASE_URL` | Varsayılan: `https://api.vxtwitter.com` |

> İhtiyaç halinde tüm değerleri `.env` dosyasında güncelleyebilirsiniz.

## Kullanıcı Dostu Loglama
- Konsol çıktısı okunaklı seviyeler, kısaltılmış logger adı ve kısa ipuçları içerir.
- `logs/bot.log` dosyası döner (5 MB, 2 yedek) ve DEBUG seviyesinden itibaren tüm detayları saklar.
- `LOG_LEVEL` ortam değişkeni veya `setup_logging(level=...)` argümanı ile varsayılan INFO seviyesini değiştirebilirsiniz.

## Komutlar
- `/start` – Botu tanıtır ve hazır olduğuna dair mesaj verir.
- `/help` – Desteklenen platformlar ve kullanım ipuçlarını listeler.

## Mimari Özeti
```
src/bot
├── config.py        # .env tabanlı ayarlar
├── logging.py       # kullanıcı dostu log konfigurasyonu
├── main.py          # bot giriş noktası
├── handlers/        # Telegram komutları ve link yakalayıcılar
├── services/        # TikTok / Twitter istemcileri + Telegram fetcher
└── utils/           # yardımcı fonksiyonlar (chunk, medya vb.)
```

Yeni bir platform eklemek için ilgili servisi `services/` altında, komutları ise `handlers/` içinde tanımlamanız yeterlidir.

## Railway Üzerine Dağıtım
1. Railway’de yeni bir Service açın ve bu repo’yu bağlayın (Dockerfile otomatik kullanılır).
2. Ortam değişkenlerini girin:
   - `BOT_TOKEN`
   - `BOT_MODE=webhook`
   - `WEBHOOK_BASE_URL=https://<projeniz>.up.railway.app`
   - `WEBHOOK_PATH=/webhook/<benzersiz>` ve opsiyonel `WEBHOOK_SECRET`
3. Railway `PORT` değişkenini sağlar; uygulama `0.0.0.0:PORT` üzerinde webhook dinler.
4. Deploy tamamlandığında Telegram webhook’u otomatik ayarlanır.

## Yol Haritası
- Instagram Reels/Stories indirme
- YouTube (shorts + klasik) desteği
- Snapchat / Facebook içerikleri
- Redis tabanlı kuyruk ile yüksek hacimli istek yönetimi
