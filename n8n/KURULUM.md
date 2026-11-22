# Yerel n8n otomasyonu

Akış: kullanıcı onayı → ayrı kopyada düzeltme → yeniden doğrulama → kalıcı
SQLite teslim kuyruğu → n8n → tekil inceleme kaydı → yerel demo e-postası →
tamamlanma cevabı. Belge yükleme, reddetme veya yalnızca sohbet bu olayı üretmez.
Doğrulamada hata kalması bildirimi engellemez; mesaj gerçek hata/uyarı/bilgi
adetlerini gösterir, gönderim onayı vermez.

22.11.2026 canlı sentetik kabul geçti: Docker servisleri, n8n import/yayın,
Header Auth, inceleme kaydı ve tek Mailpit mesajı doğrulandı; aynı olay yeniden
gönderildiğinde duplicate cevabı alındı. Bu test LLM çağırmaz ve dışarı e-posta
göndermez. Gerçek XML düzeltmeli canlı kabul ayrıca yapılmalıdır.

## 1. Docker Desktop

[Resmî Windows kurulumu](https://docs.docker.com/desktop/setup/install/windows-install/)
üzerinden Docker Desktop kurun, WSL 2 / Linux containers ile açın. Gerekirse
Windows'u yeniden başlatın. Yeni CMD'de `docker version` ve `docker compose version`
çalışmalı; ilk komutta hem Client hem Server görünmeli.

## 2. Proje kökünde hazırlık

```cmd
.venv-clean\Scripts\python.exe scripts\setup_local_automation.py
docker compose -f n8n\compose.yaml up -d
```

Portlar: n8n `http://localhost:5678`, demo posta kutusu `http://localhost:8025`.
n8n ve posta verileri kalıcı Docker volume'larındadır. SMTP dışarı açılmaz;
posta internete gönderilmez. `down -v` verileri siler; normal durdurmada kullanmayın.
n8n sürümü sabittir; Mailpit demo imajı `latest` kullanır.

`data/automation/local.env` rastgele otomasyon tokenını tutar; yeniden hazırlık
mevcut dosyayı ezmez. Bu dosya Git dışında kalır. Tokenı sohbete göndermeyin.
`BASLAT.cmd` bu yerel ayarı yüklemez; otomasyonda aşağıdaki başlatıcıları kullanın.

## 3. n8n hesabı ve workflow

1. n8n'i açın ve yerel sahip hesabını oluşturun.
2. `faturaguard-webhook-workflow.json` dosyasını **Import from File** ile alın.
3. **Header Auth** credential oluşturun. Adı `FaturaGuard Local Token`, header
   adı `X-FaturaGuard-Token`, değeri `local.env` içindeki
   `FATURAGUARD_AUTOMATION_TOKEN=` satırının sağ tarafıdır.
4. Bu credential'ı **Webhook**, **Claim Review**, **Complete Review** düğümlerinde
   seçin. Dosyadaki credential kimlikleri yer tutucudur; importtan sonra seçim gerekir.
5. **SMTP** credential oluşturun: host `mailpit`, port `1025`, SSL/TLS kapalı,
   Disable STARTTLS açık; kullanıcı adı ve şifre boş. **Send Demo Email** düğümüne
   bağlayın. Gönderici/alıcı `.local` adresleri yalnızca demo içindir.
6. Eski site sunucusunu Ctrl+C ile kapatın. İki ayrı CMD'de proje kökünden
   `OTOMASYON_CALLBACK.cmd` ve `OTOMASYON_SITE.cmd` çalıştırın.
7. Callback yalnızca otomasyon rotalarını 8012 portunda açar ve token ister.
   Docker'dan `host.docker.internal:8012` ile erişilir; Windows Firewall sorarsa
   yalnızca gerekli yerel/Docker ağ erişimini verin. Ana site 127.0.0.1:8011'de kalır.
8. Workflow'u **Publish/Activate** edin. Üretim URL'si `/webhook/` kullanılır;
   `/webhook-test/` kalıcı kuyruk için kullanılmaz.

Workflow HTTP cevabını bildirim tamamlandıktan sonra verir. Başlangıçta dönen
genel `200 Workflow started` cevabı FaturaGuard tarafından teslim sayılmaz.
SMTP düğümünde otomatik retry açmayın; tekrarları kalıcı kuyruk yönetir.

## 4. Canlı kabul

```cmd
.venv-clean\Scripts\python.exe scripts\run_automation_acceptance.py
```

Bu komut açıkça sentetik bir test kaydı oluşturur; gerçek XML doğrulamaz.
Gerçek n8n webhook'unu çağırır, inceleme kaydı ve Mailpit'te tek e-posta oluştuğunu
kontrol eder, aynı olayı tekrar göndererek `duplicate` cevabını denetler.
Kanıt `data/evaluation/automation_acceptance.json` olur. Gerçek dış e-posta göndermez.
Kabul sırasında eski kuyruk varsa önce onları da işleyebilir; durum komutuyla inceleyin.

Ardından sitede `demo_tax_exclusive_error.xml` yükleyin, teklifi onaylayın,
yeniden doğrulamayı ve Mailpit mesajını karşılaştırın. Reddetme yeni olay üretmemeli.
Canlı gerçek fatura kabulü ile sentetik otomasyon kabulü ayrı kanıtlardır.

## 5. Hata ve tekrar deneme

```cmd
.venv-clean\Scripts\python.exe scripts\automation_status.py
.venv-clean\Scripts\python.exe scripts\automation_status.py --retry OLAY_KIMLIGI
docker compose -f n8n\compose.yaml logs --tail 40 n8n
```

Kuyruk durumları: pending/sending/retry/delivered/failed. Her olay için en fazla
6 deneme; aralar 30, 60, 120, 240, 480 saniye. Sunucu yeniden açılınca kalıcı kuyruk
devam eder; token veya webhook yokken deneme sayısı tüketilmez. 400/401/403/404/410/422
yapılandırma hatası olarak durur; düzeltip açıkça `--retry` gerekir. Diğer HTTP,
ağ ve tamamlanma cevabı hataları tekrar denenir. Teslim edilmiş olay `--retry`
ile yeniden gönderilemez. Ham cevap/URL/token hata metnine kaydedilmez.

İnceleme kaydı event_id ile tekildir; aynı anda tek işlem sahipliği vardır.
Bildirim tamamlandıktan sonra HTTP cevabı kaybolursa tekrar gelen olay e-posta
göndermez. Ancak SMTP gönderiminden hemen sonra, tamamlandı kaydı yazılmadan
çökme olursa e-posta yinelenebilir. Harici SMTP ile kesin exactly-once garantisi
verilmez. Teslimat at-least-once, inceleme kaydı tekildir. Böyle belirsiz durumlarda
otomatik tekrar da yinelenme riski taşır; gerçek kurulumda idempotency destekli
bildirim servisi seçilebilir.

Eski geçmiş olaylar geriye dönük kuyruğa eklenmez; yeni onaylanan düzeltmeler
kuyruğa girer. İnceleme kaydı, kaynak olayın anlık görüntüsüdür; daha sonraki
düzeltmeler ayrı event_id üretir. Dosya adı, XML, taraf bilgileri, tutarlar ve
sohbet gönderilmez. İnceleme verisi uygulamanın SQLite'ında, n8n hesap/credential
verisi Docker volume'unda saklanır. n8n execution içerik kaydı workflow'da kapalıdır.

## Gerçek alıcıya geçiş

Kullanıcı alıcıyı ve gönderici hesabını seçtikten sonra SMTP credential'ı n8n
arayüzünde tanımlanır; **Send Demo Email** alıcı/gönderici alanları güncellenir.
Şifre projeye veya sohbete yazılmaz. Bu aşama henüz yapılmadı; mevcut kurulum
yalnızca yerel posta kutusuna gönderir.

## Kaynaklar

- [n8n Docker kurulumu](https://docs.n8n.io/hosting/installation/docker/)
- [n8n webhook ve test/üretim URL'leri](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/)
- [n8n SMTP credential](https://docs.n8n.io/integrations/builtin/credentials/sendemail/)
- [Mailpit API](https://mailpit.axllent.org/docs/api-v1/)
