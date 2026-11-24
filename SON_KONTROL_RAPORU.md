# FaturaGuard AI son kontrol raporu

Tarih: 22.11.2026. İncelenen uygulama: main / 050ed05.

## Karar

**Bootcamp prototipi ve gözetimli demo için başarılı.**
Üretim ortamına çıkış veya bütün GİB senaryolarının karşılandığı onayı değildir.
Bu kapanış turunda uygulamanın iş mantığı değiştirilmedi.

## Bu tur yeniden çalıştırılan kontroller

| Kontrol | Sonuç |
|---|---|
| pytest, bütün testler | 518 geçti, başarısız yok |
| Ruff | Geçti |
| document-chat.js, Node sözdizimi | Geçti |
| pip check | Bozuk bağımlılık yok |
| Yerel demo preflight | RAG dosyaları hazır; Gemini/Groq ayarları tanımlı |
| Yanıt kalite sözleşmesi | 24/24 vaka geçti |
| Resmî ham kaynak SHA-256 | Yerel dosyası ve kayıtlı hash'i olan 4/4 kaynak eşleşti |
| RAG veri kümesi | 330 kaynak parçası |
| Yerel RAG değerlendirmesi | 11 golden sorgu yeniden çalıştırıldı |
| Tanınan anahtar imzası taraması | Git'teki güncel metin dosyalarında Gemini/Groq anahtarı veya özel anahtar başlığı bulunmadı |
| Ortam dosyaları | Takip edilen .env yok; yerel otomasyon ayarı Git dışında |
| Önceden kabul edilmiş XML dosyaları | Orijinal ve düzeltilmiş dosya hash'leri kayıtlarla yeniden eşleşti |

Anahtar taraması sınırlı desen kontrolüdür; tam bir gizli bilgi veya Git geçmişi
denetimi değildir. Preflight hazır olması sağlayıcının o anda yanıt verdiğini kanıtlamaz.
Bu tur yeni LLM/API isteği yapılmadı, ücretli servis veya abonelik açılmadı.

## RAG ölçümü

| Yöntem | Recall@3 | MRR@3 | URL kaynak kapsaması |
|---|---:|---:|---:|
| Semantic | 0,8182 | 0,7576 | 1,00 |
| BM25 | 0,9091 | 0,7121 | 1,00 |
| Hibrit rerank | 0,9091 | 0,7121 | 1,00 |

Hibrit yöntem daha fazla beklenen kaynağı ilk üçte buluyor, ancak MRR daha düşük.
Her ölçütte üstünlük iddiası yok. 11 sorguluk retrieval ölçümü ve 24 kalite vakası,
LLM'in her yanıtının doğru olduğunu veya halüsinasyonun sıfırlandığını göstermez.
Kanıt: `data/evaluation/retrieval_metrics.json`, `chat_answer_quality.json`.

## Önceki canlı kabullerin bu tur incelenen kanıtları

- Üç web senaryosu: vergi hariç, vergi dahil ve ödenecek toplam. Kayıtlı sonuçlar
  sıfır kalan uyarı ve HTTP 200 rapor içeriyor (`web_acceptance.json`).
- Sohbet: üç tur LLM/araç/atıf ve XML hash koruma kaydı
  (`document_conversation_acceptance.json`). Bu dosya geçmiş kabul kanıtıdır.
- Sentetik n8n: teslim, tek yerel mesaj ve tekrar olayda duplicate cevabı
  (`automation_acceptance.json`).
- Gerçek XML + n8n: `demo_tax_exclusive_error.xml`, işlem
  `108a817bf3544418ba55debf594e037e`; düzeltme applied, 0 hata/0 uyarı/1 bilgi;
  outbox delivered, review notified. Kullanıcının paylaştığı Mailpit mesajıyla
  yerel kayıtlar eşleştirilmişti (`automation_xml_acceptance.json`).
- Bu tur kabul işlemindeki orijinal ve çalışma kopyası dosyalarının hash'leri
  tekrar doğrulandı. Kayıtlı canlı kabuller bu tur yeniden üretilmedi.

## Mimari inceleme

FastAPI/Jinja2 ve küçük JavaScript arayüzü; efatura-kontrol adaptörü; yerel
Chroma/E5 + BM25 RAG; LangGraph durum/koşul/araç akışları; Gemini/Groq açıklama
ve maskeli plan; lxml/Decimal ile dört izinli aritmetik düzeltme; SQLite audit,
job ve outbox; n8n ve Mailpit katmanlarının sorumlulukları ayrılmış durumda.
Kullanıcı onayı, ayrı kopya, yeniden doğrulama ve salt okunur sohbet korunuyor.
Kuyruk tekrar denemesi, iş sahipliği, tamamlanma cevabı ve tokenlı callback
testleri mevcut. n8n akışında LLM kullanılmıyor.

## Demo öncesi kalan operasyon adımları

Kontrol anında site, n8n ve Mailpit HTTP servisleri erişilebilir değildi.
Önceki talebe göre kapatılmış olmaları beklenen durum; canlı sağlık testi bu
tur geçildi olarak işaretlenmedi. Demo günü:

1. Docker Desktop'ı açın; `docker compose -f n8n\compose.yaml start` çalıştırın.
2. `OTOMASYON_CALLBACK.cmd` ve `OTOMASYON_SITE.cmd` ayrı pencerelerde açık kalsın.
3. `run_demo_preflight.py` ve health kontrolünü yapın; n8n yayın durumunu kontrol edin.
4. Örnek XML, sonuç raporu ve Mailpit sekmelerini önceden hazırlayın.
5. Kota/ağ sorunu çıkarsa yerel kabul edilmiş kayıtları gösterin; canlı olmayan
   gösterimi açıkça belirtin. Yeni LLM sonucu yerine yerel özet kullanıldığını gizlemeyin.

## Bilinen sınırlar

Elektronik imza oluşturma ve GİB gönderimi yok. MCP uygulanmadı. Bütün hata
kodları otomatik düzeltilemez; düzeltme kataloğu dört dip toplam alanıyla sınırlı.
Maskeleme bütün özel verileri yakalayamayabilir. Kaynak kimliği doğrulaması her
cümlede anlamsal doğruluğu kanıtlamaz. SMTP gönderimi sonrası çökmede yinelenen
e-posta mümkün. Çok kullanıcılı kimlik/yetki yönetimi, kurumsal veri erişimi,
merkezi izleme ve geniş insan puanlamalı cevap değerlendirmesi üretim öncesi
ayrı iş paketleridir. Docker volume/credential yedeği kullanıcı operasyonudur;
bu tur yedek oluşturulduğu iddia edilmiyor.
