# GitHub teslim denetimi

Tarih: 22.11.2026. Amaç: başka bilgisayarda Git klonundan kurulabilir,
anlaşılır ve sır içermeyen yerel bootcamp teslimi.

## Yapılan düzeltmeler

- README öğretmenin izleyebileceği temiz-klon kurulumuna göre yeniden yazıldı;
  bağımlı olunan kişisel yedek varsayımı kaldırıldı.
- `prepare_demo.py` eklendi: örnekler, resmî HTTPS/hash doğrulamalı indirme,
  sabit embedding revizyonu ve Chroma hazırlığı. Mevcut kullanıcı işleri silinmez.
- `efatura-kontrol` test edilen 0.1.0'a sabitlendi; doğrudan kullanılan Hub ve
  Windows zaman dilimi bağımlılıkları açıkça belirtildi.
- `pytest` güvenlik bildirimi için 9.0.3'e yükseltildi. Embedding'de uzaktan
  kod çalıştırma açıkça kapatıldı; Chroma sunucu bildirimleri SECURITY.md'de açıklandı.
- Büyük kurtarma günlükleri Git tesliminden çıkarıldı; asıl dosyalar ve
  `data/delivery-archive` yerel yedeği korundu. AGENTS.md kısa proje kurallarına dönüştürüldü.
- Kullanılmayan eski n8n göndericisi kaldırıldı. Yeni kalıcı outbox akışının
  kapsamlı testleri korunuyor; eski basit göndericiye ait iki test çıkarıldı.
- Demo betiklerinde native doğrulayıcı temizliği güvenceye alındı.
- Git/Markdown/sır kontrol betiği ve temiz kurulum güvenlik testleri eklendi.
- GitHub Actions'a bağımlılık, belge/sır, JS, yerel kalite ve paket kontrolü eklendi.
  CI gerçek API anahtarı, n8n veya kişisel çalışma verisi istemez.

## Yerel kontroller ve kapsam

Güncel sayısal sonuçlar aşağıdaki kapanış tablosunda kaydedildi. Önceki 518
prototip testi ile yeni teslim testleri farklı kapılardır; test sayısı tek başına
güvenilirlik ölçümü değildir. Yeni LLM veya dış e-posta çağrısı yapılmadı.

| Kontrol | Durum |
|---|---|
| Windows 3.14 kilit listesinden ayrı venv kurulumu | Başarılı |
| Temiz Git teslim dosyalarıyla ayrı dizin | Çalışma verisi/cache taşınmadan oluşturuldu |
| Temiz dizinde pytest | pytest 9.0.3 ile 526 test geçti; ana çalışma kopyasında da 526 geçti |
| Resmî kaynakları temiz dizine indirme | Dört dosya indirildi ve SHA-256 doğrulandı |
| Açık embedding modelini temiz dizine indirme | Sabit revizyon indirildi; 330/330 Chroma hazır |
| Anahtar/Git geçmişi taraması | Tanınan sır imzaları bulunmadı; final betik raporu data/evaluation/submission_hygiene.json |
| Ruff / JS / pip check / 24 kalite vakası | Geçti |
| JSON/YAML/TOML ve gerçek Jinja ortamı | 7 JSON, 2 YAML, 1 TOML, 7 şablon geçti |
| Temiz kurulum web kontrolü | health, ana sayfa, PDF reddi, bozuk XML ve gerçek baseline geçti |
| CLI düzeltme ve native kapanış | 0/2 uyarıdan 0/0 sonucuna, orijinal hash korundu, çıkış 0 |
| Wheel paketleme | Kod/şablon/statik dosyalar mevcut; sır ve runtime verileri yok |
| pip-audit | pytest düzeltildi; Chroma için belgelenmiş dört sunucu bildirimi sürüyor |

Temiz dizin Git teslim dosyalarından yerel olarak oluşturulmuştur; buna
“uzaktan klonlandı” denmez. Kullanıcının push işlemi sonrasında GitHub,
oturum açık tarayıcıdan ayrıca incelendi: **7d591e5** commit'i için
[CI #19](https://github.com/Muhammed-Cosgun/FaturaGuard-AI/actions/runs/45040863009)
**Success** sonucuyla tamamlandı (toplam 2 dakika 40 saniye). Kalite işi ve
bütün adımları başarılıdır. README başlıkları, komut blokları, belge bağlantıları
ve Mermaid mimari diyagramı GitHub üzerinde görüntülendi.

Tek CI uyarısı: `actions/checkout@v4` ve `actions/setup-python@v5` Node.js 20
hedefliyor; GitHub bunları Node.js 24 üzerinde çalıştırmış. Bu, başarısız test
veya uygulama hatası değildir; Action sürümlerinin sonraki bakımda güncellenmesi
önerilir. Bu rapor güncellemesi uygulama/CI kodunu değiştirmez ve `[skip ci]`
ile kaydedilir; yukarıdaki başarı özellikle 7d591e5 commit'ine aittir.

## GitHub üzerinde teslimden önce

1. Son düzeltmeleri `git push origin main` ile gönderin.
2. `git fetch origin` ardından `git status --short --branch`: çalışma ağacı temiz,
   ahead/behind olmamalı. Son commit GitHub'da görünmeli.
3. Actions → son CI çalışması yeşil olmalı. Çıkabilecek Linux/sürüm sorunları
   görülmeden “uzak CI geçti” denmez; hata varsa çıktıyla ayrıca düzeltilecektir.
4. Repo private: hocanın GitHub hesabına erişim verin, daveti kabul ettiğini
   kontrol edin. Public yapma zorunluluğu yoktur. Erişim daveti otomatik gönderilmedi.
5. README ve göreli belge bağlantılarını GitHub'da açın.
6. API anahtarı, local.env, data/model/SQLite veya kişisel faturaları yüklemeyin.

GitHub'a yalnızca repo dosyaları teslim edilir. Büyük RAG/model varlıkları
hazırlık komutuyla edinilir. Kişisel n8n credential'ları taşınmaz; kurulum rehberi
ve import edilebilir workflow verilir. Açık kaynak lisansı kullanıcı adına
otomatik seçilmedi. Üçüncü taraf kaynaklar THIRD_PARTY_NOTICES.md içinde.

## Sonuç

**Yerel bootcamp teslim kapısı başarılı; bilinen Chroma riski belgeli.**
Temiz kurulumdaki API anahtarsız testte Ollama çalışmadığı için LLM ısıtması
bağlantı uyarısı verdi; temel site/doğrulayıcı başarılı açıldı. Uzak LLM çağrısı
yapılmadı. Yeni Chroma/SMTP canlı kabulü bu tur tekrar edilmedi; Mailpit
manifest digest ile sabitlendi, Compose YAML doğrulandı; daemon sandbox
hesabından yönetilemedi. RAG ölçümü temiz dizinde aynı sonucu verdi.
Uygulama commit'inin GitHub push/CI kontrolü tamamlandı. Öğretmen erişimi
ve bu rapor güncellemesinin push işlemi son adım olarak kalır. Üretim güvenliği veya bütün
GİB/LLM senaryolarının kusursuzluğu iddia edilmez. [Güvenlik sınırları](SECURITY.md).

Makine tarafından okunabilir, sır içermeyen teslim özeti:
[submission_results.json](resources/evaluation/submission_results.json).
