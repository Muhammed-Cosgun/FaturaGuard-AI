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
- Golden sorgu seti ile semantic, BM25 ve hibrit retrieve→rerank akışları gerçek Chroma indeksi üzerinde ölçüldü. İlk baz ölçümde üç strateji de `Recall@3 = 0.67`, `MRR@3 = 0.67`, resmî GİB atıf kapsaması `1.00` verdi; eşitlik, daha geniş değerlendirme seti ve ağırlık kalibrasyonu için açık iyileştirme maddesi olarak kaydedildi.
- n8n webhook bildiriminin yalnızca işlem metadatası gönderdiği; XML içeriği ve yerel saklama yolunu taşımadığı otomatik testle doğrulandı.
- Kaynaklı açıklama öncesi kanıt uygunluk eşiği eklendi: versiyon geçmişi gibi düşük bilgi içeren parçalar elenir; yalnızca yeterli lexical/terim sinyali taşıyan GİB kanıtında üretim yapılır. Zayıf kanıtla agent'ın `insufficient_official_evidence` durumunda durduğu otomatik testle doğrulandı.
- Uygulama kodu biçim/lint denetiminden geçti; tüm otomatik testler çalıştırıldı: 28/28 test başarılı.
- Gerçek `test_hesap_hata.xml` ile komut satırı uçtan uca demo çalıştırıldı. Onaysız akışta teklif oluşturulup giriş XML'i değiştirilmedi; onaylı akışta izinli dip toplam düzeltmesi çalışma kopyasına uygulandı, uyarı sayısı `2`'den `0`'a indi ve giriş dosyasının SHA-256 özeti değişmeden kaldı.
- Gerçek `test_duzeltilmis.xml` ile geçerli belge kabul senaryosu çalıştırıldı: 0 hata, 0 uyarı, 0 düzeltme teklifi ve değişmeyen SHA-256 özeti doğrulandı.
- Demo sonrası JSON rapor ayrıca incelendi: yeniden doğrulama özeti ile diff metadatası bulunuyor; orijinal yol, XML içeriği ve tam XML diff'i bulunmuyor.
- Tarayıcıda yapılan gerçek demo, kaynaklı AI açıklamasının resmî GİB URL/sayfa atfı ve `awaiting_human_review` durumuyla çalıştığını doğruladı. `qwen2.5:7b` ile yanıt süresi yaklaşık üç dakika ölçüldüğünden, varsayılan model CPU dostu `qwen2.5:3b-instruct` olarak güncellendi; sunum öncesi bu modelle hız/kalite kabul testi tekrarlanacak.
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
