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

## 8. Güncel ilerleme takibi (12.11.2026)

| İş paketi | Durum | Tamamlanan kanıt | Açık takip maddesi |
|---|---|---|---|
| 1 — Temel kurulum | Büyük ölçüde tamamlandı | FastAPI uygulaması, bağımlılık tanımı, lint/test komutları ve GitHub Actions CI tanımı mevcut. | Temiz bir Windows ortamında yeniden kurulum ve uzaktaki CI çalışmasının kanıtı alınacak. |
| 2 — Doğrulama entegrasyonu | Tamamlandı | `efatura-kontrol` adaptörü, önceliklendirme ve 64 belgelenmiş kod için 65 doğrulama kaydı/test kapsamı mevcut. | Yeni kütüphane sürümünde regresyon çalıştırılacak. |
| 3 — Dosya yaşam döngüsü | Tamamlandı | Orijinal saklama, SHA-256, işlem kimliği, ayrı çalışma kopyası ve minimal XML diff uygulanıyor. | Demo öncesi depolama klasörleri temizlenip saklama notu doğrulanacak. |
| 4 — Bulguların sunumu | Tamamlandı | Öncelikli bulgu kartları, işlem geçmişi, HTML/JSON raporları ve denetim izi mevcut. | Agent risk/işlem planının HTML işlem raporunda da görünmesi iyileştirilecek. |
| 5 — GİB hibrit RAG | Tamamlandı | Resmî GİB envanteri + SHA-256, chunking, embedding, Chroma, BM25, hybrid rerank, golden set ve metrikler mevcut. | 64 doğrulama kodunun tamamı için değil, temsilî hata aileleri için RAG kalite ölçümü var; golden set kapsamı genişletilebilir. |
| 6 — Güvenli agent ve düzeltme | Tamamlandı, katalog genişletmesi sürüyor | LangGraph intake/decision graph, tool allowlist, insan onayı, maskeli LLM patch planı, privacy redactor ve dört izinli aritmetik dip toplam düzeltmesi mevcut. | Yeni düzeltme kuralları ancak gerçek fixture + bağımlılık analizi + yeniden doğrulama kanıtıyla eklenmeli. |
| 7 — Sonuç kanıtları ve otomasyon | Tamamlandı | Yeniden doğrulama, hash, diff, SQLite audit trail, rapor ve n8n webhook örneği/testi mevcut. | n8n webhook'u gerçek bir yerel n8n örneğinde isteğe bağlı demo olarak çalıştırılabilir. |
| 8 — Değerlendirme ve uçtan uca ürün | Büyük ölçüde tamamlandı | Otomatik test paketi, RAG metrikleri, model smoke/benchmark araçları, preflight ve ana demo senaryosu mevcut. | Genişletilmiş düzeltme kataloğu için tarayıcıdan manuel kabul testleri, API gecikme ölçümü ve temiz kurulum testi tamamlanacak. |

### Teslim öncesi öncelikli takip listesi

- [ ] **P0 — Genişletilmiş düzeltme kataloğu manuel kabulü:** `TaxExclusiveAmount`, `TaxInclusiveAmount` ve `PayableAmount` tekil hata senaryolarını web arayüzünde yükle; LLM patch planı, kullanıcı onayı, minimal diff ve yeniden doğrulamayı kaydet.
- [ ] **P0 — Temiz kurulum kanıtı:** Yeni sanal ortamda bağımlılık kurulumu, RAG indeks kontrolü, `pytest`, `ruff check .` ve uygulama açılışını tekrar doğrula.
- [ ] **P0 — Sunum yapılandırması:** `run_demo_preflight.py` ile Gemini → Groq → deterministik fallback zincirini kontrol et; anahtarları ekrana veya Git'e yazma.
- [ ] **P0 — Teslim raporu güncellemesi:** Güncel 136 otomatik testlik paket sonucunu, manuel kabul tarihlerini ve bilinen sınırlılıkları `Test_and_Delivery_Report.md` içine son kez işle.
- [ ] **P1 — Hız/kalite kanıtı:** Birincil ve fallback sağlayıcı için üçer kaynak açıklaması ölç; süre, sağlayıcı ve başarı/fallback sonucunu teslim raporuna ekle.
- [x] **P1 — Rapor bütünlüğü:** HTML rapora agent risk/işlem planı özeti eklendi; JSON raporundaki agent triage alanıyla tutarlılığı test edildi.
- [ ] **P1 — Gizlilik denetimi:** Redactor'ın açıklama ve patch-plan payload'larında maskelenen alan sayısını değerleri saklamadan audit olayına yazmayı değerlendir.
- [ ] **P2 — RAG değerlendirmesi:** Golden sorgu setini, az temsil edilen hata aileleri (iade, tevkifat, ödeme, e-Arşiv/zarf) için genişlet ve metrikleri yeniden üret.
- [ ] **P2 — İsteğe bağlı otomasyon:** n8n webhook örneğini gerçek yerel n8n akışında test et; yapılmazsa bunu bilinen sınırlılık olarak raporla.
- [ ] **P2 — Depo hijyeni:** Geçici `.pytest-work-*` klasörlerini sil veya `.gitignore` içinde dışla; teslimde yalnızca izlenebilir kaynak, test ve belge dosyaları kalsın.

### Bilinçli kapsam dışı maddeler

E-imza/mali mühür üretimi, GİB'e gerçek gönderim, kullanıcı hesabı/çok kiracılı yapı, toplu belge işleme ve serbest biçimli XML düzeltmesi V1'in eksikleri değildir; proje kapsamında özellikle dışarıda bırakılmıştır.
