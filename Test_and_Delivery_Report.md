# Test ve teslim özeti

## Güncel belgeler

- [GitHub teslim kontrolü](TESLIM_KONTROLU.md): temiz-klon, paket, belge,
  güvenlik ve güncel test kapısı.
- [Prototip kapanış raporu](SON_KONTROL_RAPORU.md): 22.11.2026 tarihli 518 test,
  RAG ölçümü ve kayıtlı canlı kabulün kapsamı.
- [Sunum ve demo](SUNUM_HAZIRLIK.md).

## Kanıtların anlamı

Otomatik testler yazılım sözleşmelerini, güvenlik sınırlarını, hata yollarını,
gerçek XML bulgularını ve taklit sağlayıcılarla agent davranışını denetler.
24 yerel yanıt kalite vakası, geniş bir insan puanlamalı model değerlendirmesi
veya yüzde yüz cevap doğruluğu değildir.

Üç aritmetik web senaryosu ve Gemini/Groq sohbeti geçmiş canlı kabullerde
çalıştırıldı. n8n için hem sentetik duplicate testi hem gerçek XML + yerel
posta kabulü geçti. Yeni teslim turunda bunların yeniden üretilip
üretilmediği TESLIM_KONTROLU.md içinde açıkça belirtilir.

Çalışma zamanı data/evaluation dosyaları gerçek işlem/ağ ortamına bağlıdır,
GitHub klonunda hazır oldukları varsayılmaz. Komutlar README.md içinde.
Eski format/kurtarma günlüğü güncel teslim kılavuzuyla karışmaması için
Git tesliminden çıkarıldı; kullanıcının yerel yedekleri korunur.
