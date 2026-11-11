# FaturaGuard AI — Test ve Teslim Raporu

Bu belge geliştirme boyunca test sonuçları ve teslim kanıtlarıyla güncellenecektir.

## Başlangıç doğrulama kanıtları

- Python API entegrasyon testi tamamlandı.
- Bozuk XML biçim hatası testi tamamlandı.
- SHA-256 dosya bütünlüğü testi tamamlandı.
- Yapılandırılmış JSON hata çıktısı testi tamamlandı.

## Uygulama altyapısı durumu

- FastAPI uygulama fabrikası ve sağlık denetimi eklendi.
- Ana sayfanın erişilebilirliği otomatik testle doğrulanıyor.
- GitHub Actions CI hattı lint ve test kontrollerini çalıştıracak şekilde eklendi.
- `efatura-kontrol` için uygulama içi adaptör sözleşmesi ve bu sözleşmenin eşleme testi eklendi.
- XML yükleme politikasını, orijinal dosya saklamayı ve SHA-256 bütünlük kaydını kapsayan saklama servisi eklendi.
- Saklama servisinin uzantı, boyut, yol geçişi ve hash davranışlarını sınayan testler eklendi.
- RAG için resmî GİB kaynak envanteri oluşturuldu; UBL-TR paketi/kılavuzları ile e-Fatura test ve entegrasyon kılavuzları resmî GİB adreslerinden indirildi ve SHA-256 değerleri kaydedildi.
- Kaynak kataloğu servisinin GİB dışı alan adlarını reddetmesi ve yerel dosyanın SHA-256 bütünlüğünü doğrulaması için testler eklendi.
- Hata, hesap/şematron uyarısı, imza eksikliği ve bilgilendirme bulguları için deterministik önceliklendirme testleri eklendi.
- SHA-256 doğrulamasından geçen iki resmî GİB PDF'sinden 100 kaynak parçası üretilip yerel RAG aramasıyla doğrulandı; arama sonucu kaynak kimliği ve sayfa numarası döndürüyor.
- Chroma semantic retrieval, BM25 lexical retrieval ve hibrit rerank altyapısı eklendi. Rerank birimi, teknik terim eşleşmesinin doğru GİB kanıtını öne çıkardığını sınar.
- Resmî GİB UBL-TR 1.2.1 Kılavuzları arşivinden Fatura ve Ortak Elemanlar PDF'leri de SHA-256 doğrulanmış arşiv üzerinden indekslendi. Kaynak parçası sayısı 100'den 330'a çıktı; `LegalMonetaryTotal` ve `InvoiceLine` alanları için doğrudan UBL-TR kanıtı getirildi.
- Gerçek GİB chunk'ları üzerinde BM25 lexical araması çalıştırıldı; `UBL-TR şema schematron kontrolü` sorgusunda e-Fatura Test Planı'nın ilgili sayfası ilk sonuç oldu.
- Embedding modeli önbelleği kullanıcı profili yerine proje içindeki `data/models/` klasörüne yönlendirildi; model ve indeks varlıkları proje ortamında tutulur.
- Gerçek Chroma koleksiyonu üretildi: doğrulanmış 100 GİB chunk'ı kalıcı vektör koleksiyonuna yazıldı. Semantic + BM25 + hybrid rerank sorgusu, e-Fatura Test Planı'nın 7. sayfasını kaynak URL'siyle ilk kanıt olarak döndürdü.
- LangGraph agent için kaynak bulunduğunda insan incelemesine giden, kaynak bulunmadığında kesin öneri vermeden duran iki koşullu rota testi eklendi.
- LangGraph agent, hybrid rerank ve resmî kaynak kataloğu testleri proje içi geçici dizinle çalıştırıldı: 5/5 test geçti.
- Yerel LLM smoke testi, varsayılan `qwen2.5:7b` modeliyle gerçek RAG kanıtı ve yapılandırılmış kaynak-atıf sözleşmesini doğrulamak için eklendi.
- Gerçek yerel LLM smoke testi başarıyla tamamlandı: `qwen2.5:7b`, e-Fatura Test Planı v1.3, sayfa 7 kaynağıyla geçerli yapılandırılmış açıklama üretti; LangGraph akışı `awaiting_human_review` durumunda güvenle durdu.
- İnsan onaylı düzeltme akışı eklendi: `hesap-dip-satir` için yalnızca mevcut satır tutarlarından `LineExtensionAmount` dip toplamını hesaplayan izinli kural, çalışma kopyası, diff ve yeniden doğrulama alt yapısı oluşturuldu.
- İş kaydı ve audit trail, JSON dosyaları yerine SQLite'a taşındı. `job_created`, kullanıcı onayı/reddi, düzeltme uygulama, kaynak açıklaması ve otomasyon bildirimi olayları işlem kimliğiyle kaydedilir; tam XML diff'i SQLite dışında tutulur.
- İşlem geçmişi ekranı eklendi: son 20 işlem, hash kısaltması, doğrulama özeti ve rapor bağlantısıyla XML içeriği açığa çıkarılmadan listelenir. HTML/JSON raporlarına SQLite audit olayları eklendi.
- Kullanıcı arayüzündeki audit zamanları UTC olarak saklanan kayıtlardan Türkiye yerel saatine dönüştürülerek okunabilir biçimde gösterilir.
- Hata ekranında isteğe bağlı kaynaklı AI açıklaması eklendi. Her açıklama LangGraph işlem izi ve doğrulanmış GİB URL/sayfa atfıyla işlem kaydında saklanır.
- Golden sorgu seti; XSD/Schematron, uygulama yanıtı, parasal toplamlar, InvoiceLine, TaxExclusiveAmount, XAdES/ExtensionContent ve vergi/kimlik alanlarını kapsayacak şekilde 11 sorguya genişletildi. Güncel gerçek Chroma ölçümünde semantic `Recall@3 = 0.82`, `MRR@3 = 0.76`; BM25 ve hybrid rerank `Recall@3 = 0.91`, `MRR@3 = 0.71`; tüm stratejilerde resmî GİB atıf kapsamı `1.00` bulundu. Ölçüm ayrıntıları `data/evaluation/retrieval_metrics.json` dosyasındadır.
- Aritmetik bulgu için gerçek agent retrieval denetimi yapıldı: UBL-TR Ortak Elemanlar Kılavuzu sayfa 47 ile UBL-TR Fatura Kılavuzu sayfa 35 yeterli teknik-terim ve rerank sinyaliyle bulundu; agent açıklama üretme eşiğini geçti. Zayıf versiyon geçmişi kaynakları filtrelenmeye devam eder.
- Yerel LLM üretim hatası için güvenli geri dönüş eklendi. Model açıklama üretemezse işlem hata sayfasına düşmez; resmî kanıtlar korunur, durum `generation_unavailable` olarak kaydedilir ve insan incelemesi istenir. Küçük yerel modelin açıklama alanlarında cümle tekrarı yapması için ek azaltma denetimi eklendi.
- Yerel modelin JSON sözleşmesini bozduğu durum için deterministik kaynak özeti fallback'i eklendi. Bu yol, doğrulanmış bulgu ve retrieval citation'larını kullanır; modelin geçersiz metnini hiç göstermez. Geçersiz JSON dönen model yanıtını taklit eden test bu akışı doğrular.
- `generation_unavailable` durumunda audit trail artık hata sınıfını da saklar. Bu sayede timeout, HTTP erişimi veya yapılandırılmış çıktı doğrulama sorunu ayrıştırılabilir; kullanıcı ekranı teknik ayrıntı göstermez.
- Yerel LLM seçimini ölçüme dayandırmak için dört gerçek bulgu vakasında süre, şemaya uygun LLM yanıt oranı, fallback oranı ve kaynaklı yanıt oranını ölçen benchmark altyapısı eklendi. Karşılaştırılacak modeller: `qwen2.5:3b-instruct`, `qwen3:4b-instruct`, `gemma3:4b`.
- n8n webhook bildiriminin yalnızca işlem metadatası gönderdiği; XML içeriği ve yerel saklama yolunu taşımadığı otomatik testle doğrulandı.
- Kaynaklı açıklama öncesi kanıt uygunluk eşiği eklendi: versiyon geçmişi gibi düşük bilgi içeren parçalar elenir; yalnızca yeterli lexical/terim sinyali taşıyan GİB kanıtında üretim yapılır. Zayıf kanıtla agent'ın `insufficient_official_evidence` durumunda durduğu otomatik testle doğrulandı.
- Güvenlik negatif testleri genişletildi: onaysız ve izin listesi dışındaki düzeltme kuralı reddedilir; retrieval ile dönmeyen citation reddedilir; Gemini başarısızlığında ikinci API sağlayıcısının sonucu korunur.
- Prompt-injection'a karşı veri sınırı sertleştirildi: ham XML/kütüphane hata metni artık agent retrieval sorgusuna veya LLM isteğine aktarılmaz. Bulgu kodundan üretilen güvenilir teknik sözlük kullanılır; saldırı cümlesi içeren bulgu mesajının sorgu ve sağlayıcı payload'ından dışlandığı otomatik testlerle doğrulandı.
- Hata kapsam matrisi eklendi ve gerçek fixture paketi başlatıldı: XML, XSD, kimlik, taraf, iade/senaryo, aritmetik, imza, UUID, tarih, para birimi, ölçü birimi ve vergi kodu ailelerinde 16 gerçek XML senaryosu doğrulandı. Geçerli temel faturadan tek alanı değiştiren fixture testleri, `sch-InvoiceIDCheck-1`, `sch-UUIDCheck-1`, `sch-TarihBicimi-1`, `sch-CurrencyCodeCheck-1`, `sch-GeneralUnitCodeCheck-1`, `sch-TaxTypeCheck-1`, `sch-PartyIdentificationTCKNVKNCheck-2`, `sch-IADEInvioceCheck-1` ve `hesap-dip-odenecek` kodlarını gerçek doğrulayıcıyla sınar. Tevkifat ve imzalı XAdES yapısı için ayrı fixture üretimi planlıdır.
- Sağlayıcı seçimi birim testine ayrıldı: `auto` modunun Gemini → Groq → deterministik kaynak özeti zinciri, Cohere'in yalnızca açık deneysel seçimde kullanılması ve `local` modunun API sağlayıcısı kurmaması doğrulanır.
- Sunum öncesi preflight komutu eklendi: RAG indeksinin varlığını ve anahtar değerlerini göstermeden aktif üretim/fallback zincirini denetler.
- Sunum arayüzü kurumsal uygulama kabuğuna yükseltildi: tüm ekranlarda tutarlı üst gezinme/alt bilgi, çalışma alanı bağlamı, durum rozetleri, hata/uyarı/bilgi sayaçları, işlem adımı göstergeleri, karar odaklı düzeltme kartları ve önce/sonra rapor özeti bulunur. Ham JSON gösterilmez; tüm Jinja şablonları derleme testiyle doğrulanır.
- Uygulama kodu biçim/lint denetiminden geçti; güncel otomatik test paketi 51/51 başarılıdır.
- Gerçek `test_hesap_hata.xml` ile komut satırı uçtan uca demo çalıştırıldı. Onaysız akışta teklif oluşturulup giriş XML'i değiştirilmedi; onaylı akışta izinli dip toplam düzeltmesi çalışma kopyasına uygulandı, uyarı sayısı `2`'den `0`'a indi ve giriş dosyasının SHA-256 özeti değişmeden kaldı.
- Gerçek `test_duzeltilmis.xml` ile geçerli belge kabul senaryosu çalıştırıldı: 0 hata, 0 uyarı, 0 düzeltme teklifi ve değişmeyen SHA-256 özeti doğrulandı.
- Güncel sürümde üçlü uçtan uca kabul paketi tekrarlandı: `test_bozuk_xml.xml` 1 hata ve 0 teklif ile reddedildi; `test_hesap_hata.xml` kullanıcı onayıyla 2 uyarıdan 0 uyarıya indi, orijinal SHA-256 korundu ve diff yalnızca `25.15 → 15.15` satırını içerdi; `test_duzeltilmis.xml` 0 hata/0 uyarı ve 0 teklif ile kabul edildi.
- Demo sonrası JSON rapor ayrıca incelendi: yeniden doğrulama özeti ile diff metadatası bulunuyor; orijinal yol, XML içeriği ve tam XML diff'i bulunmuyor.
- Yerel model benchmark'ı tamamlandı: `qwen2.5:3b-instruct` ortalama 20,95 sn'de dört vakanın tamamında deterministik fallback'e düştü (%0 geçerli LLM çıktısı); `qwen3:4b-instruct` ortalama 51,16 sn ve %50 geçerli LLM çıktısı verdi; `gemma3:4b` ortalama 43,42 sn ve dört vakanın tamamında geçerli yapılandırılmış LLM çıktısı verdi (%100). Bu nedenle varsayılan model `gemma3:4b` olarak değiştirildi.
- Sunum için ilk AI açıklamasındaki 40 saniyelik yerel gecikmeyi azaltmak amacıyla isteğe bağlı Gemini API adaptörü eklendi. Adaptör, aynı Pydantic JSON şemasını ve retrieval ile dönen atıfların bire bir doğrulanmasını kullanır; API başarısız olursa uzun yerel üretimi beklemeden deterministik GİB kaynak özetine döner. API anahtarı tanımlanmadan uygulama yerel Gemma modunda çalışır.
- RAG/embedding soğuk başlangıcını ilk kullanıcı tıklamasından çıkarmak için FastAPI lifespan başlangıcında küçük bir semantic retrieval ısıtması eklendi. Isıtma başarısız olsa bile uygulama açılır; durum loglanır ve normal güvenli akış korunur.
- Yerel model karşılaştırmasının adil olması için yerel Ollama üreticisine başlangıç ısıtması eklendi. `LLM_PROVIDER=local` modunda sunucu hazır olmadan önce Gemma'ya bir tokenlık kısa çağrı yapılır; API birincil modunda uzak modele deneme isteği gönderilmez.
- Gemini Flash Lite, canlı arayüz testinde kaynaklı açıklamaları yaklaşık 3–5 saniyede üreten birincil sağlayıcı olarak seçildi. Gemini başarısız olursa Groq Chat Completions tabanlı `openai/gpt-oss-120b` ikinci sağlayıcı olarak denenir; iki API de başarısızsa sistem doğrulanmış GİB atıflarıyla deterministik kaynak özeti üretir.
- Groq GPT-OSS 120B, gerçek hesap ve imza bulgularında akıcı Türkçe, strict JSON Schema ve doğrulanmış GİB atıflarıyla kalite kabulünü geçti. Qwen 3.8 27B ve Cohere Command A+ ise gerçek arayüz testinde dil/bağlam kalitesi kabulünü geçmediği için otomatik zincire alınmadı; Cohere yalnızca deneysel karşılaştırma modunda tutulur.
- Tarayıcıdaki son kabul testinde `qwen2.5:3b-instruct`, hesap bulgusunda 10–15 saniye içinde `insufficient_official_evidence` ile güvenli biçimde durdu; imza bulgusunda 13 saniyede Entegrasyon Kılavuzu v1.10, sayfa 17 atfıyla kaynaklı açıklama üretti. Onaylı dip toplam düzeltmesi sonrası uyarılar 2'den 0'a indi ve minimal diff doğrulandı.
- Gerçek demo sırasında fark edilen geniş XML yeniden-serileştirme diff'i düzeltildi. Düzeltme motoru artık yalnızca onaylanan dip toplam metnini byte düzeyinde değiştiriyor; aynı XML ile yeni uçtan uca çalıştırmada diff yalnızca `25.15 → 15.15` satırını içerdi ve yeniden doğrulama 0 uyarı verdi.
- Kullanıcıya HTML/JSON işlem raporu ve XML içeriği taşımayan isteğe bağlı n8n webhook bildirim altyapısı eklendi.

## Planlanan test senaryoları

- Geçerli XML doğrulaması
- Bozuk XML reddi
- XSD ve Schematron bulguları
- Aritmetik tutarsızlık tespiti
- Onaysız düzeltmenin engellenmesi
- Onaylı düzeltme sonrası yeniden doğrulama
- Önce/sonra XML diff üretimi
- Orijinal dosyanın değişmediğinin doğrulanması
- RAG kaynak gösterimi
- Chunk metadata'sının kaynak, URL, sayfa ve hash ile korunması
- Chroma metadata filtreleme ve semantic retrieval
- Lexical / semantic / hibrit+rereank retrieval karşılaştırması
- Golden sorgu seti ile Recall@k ve MRR ölçümü
- Agent'ın kaynak yokken düzeltme önermemesi
- Agent'ın izin verilmeyen aracı çağıramaması
- Prompt injection içeren XML veya RAG metninin güvenlik kurallarını değiştirememesi

## Teslim kontrol listesi

- [ ] Kurulum ve çalıştırma adımları README'de doğrulandı.
- [x] Kritik akışlar otomatik testlerle çalışıyor.
- [x] Demo senaryosu baştan sona tekrarlandı.
- [x] Bilinen sınırlılıklar kaydedildi.

## Doğrulama ortamı notu

Bu geliştirme ortamı yerel TCP dinleme ve Windows `asyncio` olay döngüsünün kullandığı yerel soketleri engellediğinden, tarayıcı üzerinden manuel `localhost` kontrolü burada gerçekleştirilemedi. Bu ürün sınırlaması değildir. Manuel web kontrolü, normal yerel CMD ortamında `uvicorn faturaguard.main:app --reload` komutuyla ve `DEMO_SCENARIO.md` içindeki adımlarla teslim öncesi yapılacaktır.
