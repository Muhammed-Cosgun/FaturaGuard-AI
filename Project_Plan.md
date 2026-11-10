# FaturaGuard AI — Proje Planı

## 1. Proje özeti

FaturaGuard AI, e-Fatura XML belgelerini doğrulayan; sorunları önceliklendiren; yalnızca resmî GİB kaynaklarıyla açıklayan ve kullanıcı onayıyla güvenli, sınırlı düzeltmeler uygulayan bir web uygulamasıdır.

**Teslim hedefi:** çalıştırılabilir FastAPI + Jinja2/HTMX V1 uygulaması, otomatik testler ve tekrar edilebilir demo senaryosu.

## 2. Çalışma yaklaşımı

Proje tek geliştirici tarafından yürütülür. İşler küçük, doğrulanabilir paketlere ayrılır. Bir paket ancak kodu, testi ve belge güncellemesi birlikte tamamlandığında kapatılır. Kapsam değişikliği yalnızca V1 kabul kriterlerini bozmayacaksa yapılır.

## 3. İş paketleri ve çıktılar

| No | İş paketi | Ana çıktı | Bağımlılık |
|---|---|---|---|
| 1 | Temel kurulum | Depo yapısı, FastAPI iskeleti, ayarlar, CI başlangıcı | — |
| 2 | Doğrulama entegrasyonu | `efatura-kontrol` adaptörü ve tek bulgu modeli | 1 |
| 3 | Dosya yaşam döngüsü | Orijinal koruma, çalışma kopyası, işlem kimliği ve hash | 1 |
| 4 | Bulguların sunumu | Önceliklendirme, anlaşılır hata kartları | 2 |
| 5 | GİB hibrit RAG | Kaynak envanteri, chunks, embeddings, Chroma, lexical arama, retrieval/rerank ve kaynaklı yanıt | 4 |
| 6 | Güvenli agent ve düzeltme | LangGraph state/edge yapısı, araç allowlist'i, retry, izinli düzeltme kataloğu, onay/red | 2, 3, 5 |
| 7 | Sonuç kanıtları ve otomasyon | Yeniden doğrulama, XML diff, rapor ve n8n webhook örneği | 6 |
| 8 | Değerlendirme ve uçtan uca ürün | RAG golden seti, retrieval/rerank metriği, web akışı, demo ve teslim | 1–7 |

## 4. Kilometre taşları

| Kilometre taşı | Başarı kanıtı |
|---|---|
| M1 — Doğrulama çalışıyor | Geçerli, bozuk ve aritmetik hatalı XML örnekleri doğru sonuç verir. |
| M2 — Kaynaklı RAG çalışıyor | Chroma ve lexical retrieval, golden sorgularda beklenen GİB kaynağını getirir; rerank sonucu kaynak bilgisi taşır. |
| M3 — Güvenli öneri akışı | LangGraph agent yalnızca tanımlı araçları çağırır; onaysız değişiklik yapılamaz. |
| M4 — Düzeltme kanıtlanıyor | Çalışma kopyası değişir, orijinalin hash'i sabit kalır, diff gösterilir. |
| M5 — Sunuma hazır V1 | Uçtan uca demo, otomatik testler, RAG metrikleri ve teslim raporu hazırdır. |

## 5. Öncelik ve kapsam yönetimi

### Zorunlu V1

- XML yükleme, XSD/Schematron/aritmetik kontroller
- Hata önceliklendirme ve GİB kaynaklı açıklama
- Chroma tabanlı embedding, lexical retrieval ve rerank içeren GİB kaynaklı RAG
- LangGraph üzerinde tek agent, çok adımlı iş akışı ve allowlist araçlar
- Kullanıcı onaylı, sınırlı düzeltme
- Yeniden doğrulama, diff, orijinal koruma ve rapor
- RAG değerlendirme seti ve isteğe bağlı n8n webhook örneği

### Yalnızca zaman kalırsa

- Kullanıcı hesabı ve kalıcı belge geçmişi
- Çoklu belge toplu işleme
- Gelişmiş görsel analitikler
- Çoklu dil desteği

## 6. Başlıca riskler ve azaltma yöntemi

| Risk | Etki | Azaltma |
|---|---|---|
| Doğrulama kütüphanesi beklenmedik çıktı üretir | Yüksek | Adaptör katmanı ve mevcut dört entegrasyon testi korunur. |
| GİB kaynağı yetersiz veya güncel değildir | Orta | Kaynak tarihi/bağlantısı gösterilir; kaynak yoksa kesin öneri verilmez. |
| Embedding/rerank modeli cihazı zorlar | Orta | Yerel kalıcı Chroma, küçük çok dilli model ve yapılandırılabilir model adaptörü kullanılır; golden setle kalite ölçülür. |
| Prompt injection veya kaynaksız LLM cevabı | Yüksek | Güvenilmeyen veri ayrımı, araç allowlist'i, yapılandırılmış çıktı ve zorunlu citation doğrulaması uygulanır. |
| Otomatik düzeltme belge anlamını değiştirir | Yüksek | İzin listesi, kullanıcı onayı, çalışma kopyası ve yeniden doğrulama zorunludur. |
| Süre daralır | Yüksek | Önce zorunlu V1 iş paketleri tamamlanır; isteğe bağlı işler ertelenir. |
| Demo ortamı farklı davranır | Orta | Temiz kurulum ve uçtan uca demo senaryosu teslim öncesi tekrarlanır. |

## 7. Teslim tanımı

V1; temiz ortamda çalıştırılabildiğinde, zorunlu akışı tamamladığında, kritik testleri geçtiğinde ve kullanıcıya orijinal/düzeltilmiş XML ile doğrulama kanıtını sunabildiğinde teslim edilmiş kabul edilir.
