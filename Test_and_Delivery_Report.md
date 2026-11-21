# FaturaGuard AI — Test ve Teslim Raporu

## Tüm bulgu ailelerine ortak açıklama katmanı

Tek tax-exclusive örneğine özel karşılaştırma koşulu kaldırıldı.
`document_insights.py`, motorun gerçek allowlist/bağımlılık kataloğundan dört
izinli düzeltmenin tamamını açıklar; tutarları uygulanmış tekliften okur.
Bulgu adet farklarıyla tamamen kaybolan, kısmen azalan ve yeni/artan kodları
ayırır. Bilinen bağımlılık ve doğrulama sonucu birlikte desteklemiyorsa neden
uydurmaz; birden fazla değişiklikte tekil nedensellik kurmaz.

Tek bulgu açıklaması bütün katalog kodlarında gerçek mesaj, XML konumu,
doğrulayıcı kuralı, teklif/bağımlılık durumu ve inceleme önerisiyle başlar.
LLM yorumu ayrı gösterilir; kaynak yokken yerel bulgu korunur. Serbest kullanıcı
sorusu ve bu yerel belge ayrıntıları sağlayıcıya eklenmez. Genel LLM promptu,
genel bulgudan daha özel teşhis veya uygulanmış düzeltme sonucu çıkarmamayı ister.

**236 test geçti**, Ruff temiz: 65 katalog kodu + bilinmeyen kod için yerel
bağlam, dört düzeltme, üç bağımlılık ilişkisi, kısmi çözüm, yeni hata, ilgisiz
bulgu ve tarihî kod sorgusu sınandı. Kaynaklı yanıt testi kontrollü sağlayıcı
çıktısı kullanır. Bu çalışma bütün kodlarda canlı LLM/anlamsal doğruluk veya
bütün GİB senaryolarına uygunluk kanıtı değildir.

## Sohbet karşılaştırmasının somutlaştırılması

Önce/sonra yanıtı, sayılara ek olarak yalnızca uygulanmış tekliflerin alanını ve
before/after değerlerini, artık görülmeyen bulgu kodlarını ve güncel kalan
bulguları gösterir. Tek tax-exclusive düzeltmesi, iki uyarı düşüşü ve ilgili
bulguların kaybolması birlikte kayıtlıysa bağımlı vergi dahil kontrolünün de
geçtiğini açıklar. Bekleyen/reddedilen tekliflerden veya eksik kayıttan değişiklik
uydurmaz. Kullanıcının gerçek tax-exclusive kaydıyla salt okunur çıktı kontrolü
yapıldı. İki yeni regresyon testiyle toplam **159 test**; ek API çağrısı yok.

## Güncel sonuç / ilk doğrulama ayrımı

Kullanıcının manuel tax-exclusive senaryosunda tek `15.00 → 15.15` değişikliği,
0 hata/0 uyarılı yeniden doğrulama ve sohbet geçmişinin korunması doğrulandı.
Üstteki eski sayaçların güncel sonuç sanılmasını önlemek için sonuç ekranı ve
geçmiş listesi artık corrected_report varsa onu kullanır. İlk rapor ve agent
planı tarihî kayıt olarak açıkça etiketlenir; sohbetin eski yanıtlarına zaman
bağlamı açıklaması eklendi. İki regresyon kontrolüyle toplam **157 test** geçti.
Gerçek tax-exclusive işlem kaydında tarayıcıyla üstte 0 hata/0 uyarı/1 bilgi
ve geçmiş listesinde düzeltilmiş kopyanın 0 uyarılı sonucu doğrulandı.

## Belge asistanı doğrulaması — 21.11.2026

**Canlı kabul tamamlandı:** Kullanıcının CMD çıktısında `local_mode=overview`,
`finding_code=imza-yok`, `answer_mode=source_backed`, `citation_count=1` ve
`xml_changed=false` görüldü; smoke testi başarılı bitti. Aşağıdaki canlı test
bekleme notu bu sonuçla kapanmıştır. Bu tek bulgunun canlı kabulüdür;
bütün serbest soruların/model yanıtlarının doğruluğu iddia edilmez.

- Sonuç ve rapor ekranında sohbet paneli, hazır sorular, güncel bulgu seçimi,
  bekleme/hata mesajı ve sayfa yenilenmeden düz metin yanıt gösterimi eklendi.
- 16 yeni test: güncel sonuç kullanımı, sorunun/geçmişin sağlayıcıya taşınmaması,
  komutların işlem yapamaması, iş/bulgu izolasyonu, yetersiz kaynak, 600 karakter
  sınırı, 20 tur saklama, HTML escaping, resmî atıf URL kontrolü, audit gizliliği,
  XML hash koruması ve bekleme sırasında yeni kararları ezmeme. Toplam **155 test**;
  Ruff ve pip check temiz.
- Gerçek Uvicorn sunucusunda tarayıcıdan önce/sonra hazır sorusu ve "Bu faturayı
  düzelt" sorusunun salt okunur sınırda tutulduğu doğrulandı.
- Testler API yanıtı için kontrollü test doubles kullanır. Yeni panelin gerçek
  Gemini/Groq üretimi kullanıcı hesabındaki anahtarlarla ayrıca sınanmalıdır:
  `scripts/run_document_chat_smoke_test.py`. Henüz canlı kabul tamamlandı denmez.

## Veri ve sürüm geçmişi kurtarma — 21.11.2026

- Dört işlemdeki sekiz eski mutlak dosya yolu, SQLite backup sonrası tek
  transaction ile proje içi göreceli yollara taşındı. 73 orijinal ve 43 düzeltilmiş
  XML hash'i doğrulandı; eksik yol kalmadı. XML içerikleri değiştirilmedi.
- Private origin'deki main yedekteki `694491a` ile eşleşti; 69 commit'lik geçmiş
  geri bağlandı. 92 çalışma dosyasının işlem öncesi/sonrası SHA-256 değerleri
  eşleşti; yerel kurtarma değişiklikleri korundu. Git fsck temiz.

## Format sonrası native kapanış düzeltmesi — 21.11.2026

### Düzeltme sonrası canlı kabul sonucu

Kullanıcının kendi Windows CMD oturumundan paylaştığı yeni sonuçlar:

| Fixture | Plan sağlayıcısı | Kalan uyarı |
|---|---|---:|
| demo_tax_exclusive_error.xml | gemini_correction_plan | 0 |
| demo_tax_inclusive_error.xml | groq_correction_plan | 0 |
| demo_payable_error.xml | gemini_correction_plan | 0 |

Komuttan hemen sonra `echo %ERRORLEVEL%` sonucu **0** olarak doğrulandı.
Üçlü upload/plan/onay/patch/yeniden doğrulama/rapor kabulü ve normal süreç
kapanışı geçti. Kanıt: `data/evaluation/web_acceptance.json`.
Aşağıdaki düzeltme sürecinde geçen “bekleniyor” notu bu sonuçla kapanmıştır.

- Kullanıcı CMD'sinde Gemini ve Groq kaynaklı açıklama smoke testleri geçti.
  Maskeli düzeltme planı, Gemini ReadTimeout sonrasında Groq ile `propose` üretti.
- Web kabulü kapanışındaki Saxon native StackOverflowError, API olmadan ayrı
  thread'de oluşturulup interpreter kapanışına bırakılan cached Schematron
  motoruyla yeniden üretildi (exit 99). Motoru oluşturulduğu thread'de temizlemek
  aynı denemeyi exit 0 ile tamamladı.
- FastAPI lifespan kapanışına doğrulayıcı temizliği eklendi. Subprocess regresyon
  testi iki TestClient yaşam döngüsünde gerçek XML yüklemesini ve normal süreç
  çıkışını doğruluyor. Güncel sonuç: **139 test başarılı**, Ruff temiz.
- Canlı sağlayıcılarla yeni kodun üçlü web kabulü, kullanıcının CMD'sinde
  normal çıkış 0 ile tamamlandı; sonuçlar yukarıdaki tabloda kaydedildi.

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
- Hata kapsam matrisi eklendi ve gerçek fixture paketi başlatıldı: XML, XSD, kimlik, taraf, iade/senaryo, aritmetik, imza, UUID, tarih, para birimi, ölçü birimi, vergi kodu ve tevkifat ailelerinde 18 gerçek XML senaryosu doğrulandı. Geçerli temel faturadan tek alanı değiştiren fixture testleri, `sch-InvoiceIDCheck-1`, `sch-UUIDCheck-1`, `sch-TarihBicimi-1`, `sch-CurrencyCodeCheck-1`, `sch-GeneralUnitCodeCheck-1`, `sch-TaxTypeCheck-1`, `sch-PartyIdentificationTCKNVKNCheck-2`, `sch-IADEInvioceCheck-1`, `sch-GeneralWithholdingTaxTotalCheck-1`, `sch-XadesSignatureCheckForInvoice-1` ve `hesap-dip-odenecek` kodlarını gerçek doğrulayıcıyla sınar.
- Fixture paketi profil/senaryo ve alt hesap kontrolleriyle genişletildi: `sch-ProfileIDCheck-1`, `hesap-satir`, `hesap-vergi` ve `hesap-dip-vergi-dahil` için tek alanlı mutasyonlar gerçek doğrulayıcıda beklenen kodları üretir. Satır tutarı vakası, doğrulayıcının 0,01 parasal toleransını aşacak 0,02 farkla kuruldu; böylece test yalnızca beklenen davranışı gerçekten tetiklediğinde geçer.
- Kapsam ikinci fixture dalgasıyla 30 gerçek senaryoya ulaştı: kök XML, UBL/özelleştirme sürümü, belge kopya göstergesi, fatura tipi, zorunlu ölçü birimi, VKN/TCKN ve taraf kimlik şeması kuralları gerçek doğrulayıcıyla sınanır. Her mutasyonun yalnızca hedef kuralı tetiklediği test edilerek, XML biçim hatasına yanlışlıkla düşen denemeler düzeltilmiştir.
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
- Doğrulayıcının belgelenmiş 64 hata/bilgi kodunun tamamı kapsam matrisine alındı. Belgelenmiş kodların 61'i gerçek XML, e‑Arşiv veya zarf fixture'ı ile doğrulandı; genel `xsd`, Schematron değerlendirme hatası ve ApplicationResponse imza çıktısı ise kural çıktısını uygulamaya taşıyan çalışma zamanı/SVRL işleyicisi testleriyle doğrulandı. Genel XSD ailesi için buna ek olarak gerçek `xsd-element-content` XML senaryosu bulunur; dolayısıyla matriste 62 gerçek senaryo ve toplam 65 ayrı doğrulama kaydı vardır. Ayrıntı: `resources/evaluation/error_coverage_matrix.json`.
- LangGraph agent orkestrasyonu genişletildi: belge yüklemede agent yerel doğrulama aracını çağırır, yalnızca izinli düzeltme teklifini üretir ve bulgular varsa insan incelemesine yönlendirir. Kullanıcı onay/red kararında ikinci graph güvenli düzeltme, yeniden doğrulama ve raporlama araçlarını koşullu olarak yürütür. Araç çağrıları SQLite audit trail'e kaydedilir; akış sırası ve onaysız düzeltmenin engellendiği otomatik testlerle doğrulandı.
- LLM tabanlı maskeli patch-plan katmanı eklendi. Gemini, başarısızlığında Groq, yalnızca aday kimliği ve `TARGET_FIELD_n`/`CURRENT_VALUE_n`/`RECALCULATED_VALUE_n` tokenlarını içeren yapılandırılmış düzeltme planı üretir. Agent planı yerel adayla ve GİB retrieval atıflarıyla doğrular; değer, XML yolu veya işlem türü icat eden planlar reddedilir. Kullanıcı onay düğmesi yalnızca LLM'in `propose` kararı güvenlik politikasıyla eşleştiğinde etkinleşir.
- Merkezi `PrivacyRedactor` katmanı eklendi. Açıklama ve düzeltme-planı sağlayıcı istekleri tek noktada PII maskesinden geçer; VKN/TCKN, IBAN, e-posta, telefon ve hesap numarası tokenlaştırılır, XML/adres/kişi adı içeren alanlar bastırılır. Negatif testler, iç içe payload'larda da ham tanımlayıcıların taşınmadığını doğrular.
- Agent intake graph'ına `assess_document_risk` kalite kapısı eklendi. Araç; kritik hata varsa belgeyi `blocked`, bulgu varsa `needs_human_review`, temiz teknik doğrulamada ise `ready_for_manual_submission_review` rotasına alır; öncelikli bulguları ve kullanıcıya önerilen sonraki adımları audit trail ile kaydeder.
- Güvenli düzeltme kataloğu `TaxExclusiveAmount`, `TaxInclusiveAmount` ve `PayableAmount` dip toplamlarıyla genişletildi. Her kural gerçek `efatura-kontrol` doğrulayıcısıyla mutasyona uğratılmış fatura üzerinde onaylı patch → yeniden doğrulama testiyle doğrulandı. Alt toplam bulgusu varken bağımlı üst toplam teklifleri özellikle ertelenir.
- 12.11.2026 yerel kalite çalıştırmasında `ruff check .` başarılı oldu; güncel paket 138 otomatik testi geçti. Bu sayı, eski geliştirme aşamasındaki `51/51` notunun yerine geçer.
- HTML ve JSON işlem raporları agentın `blocked` / `needs_human_review` / `ready_for_manual_submission_review` risk rotasını, öncelikli bulgularını ve sonraki adımlarını ham XML taşımadan gösterir.
- Correction-plan sağlayıcı zinciri için anahtar göstermeyen bağımsız smoke testi eklendi. Gemini/Groq hata zinciri planın `provider_trace` alanında ve audit kaydında korunur; yükleme ekranındaki plan çağrıları açıklama çağrılarından ayrı, varsayılan 12 saniyelik süre bütçesiyle sınırlandırılır.
- Groq GPT-OSS correction-plan çağrısı strict JSON Schema moduna alındı. Böylece serbest JSON'un Pydantic `ValidationError`a düşmesi yerine, sağlayıcının `propose` / `human_review` sözleşmesine uygun yanıt üretmesi beklenir.

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

- [x] Kurulum ve çalıştırma adımları README'de doğrulandı.
- [x] Kritik akışlar otomatik testlerle çalışıyor.
- [x] Demo senaryosu baştan sona tekrarlandı; genişletilmiş üç aritmetik düzeltme senaryosu da web katmanında kabul edildi.
- [x] Bilinen sınırlılıklar kaydedildi.

## Teslim kapanış kanıtları — 12.11.2026

### Web kabulü: genişletilmiş düzeltme kataloğu

`scripts/run_web_acceptance.py` gerçek FastAPI upload/approval/report rotalarını kullanarak üç
demo XML'i sınadı. Her senaryoda orijinal fixture SHA-256 değeri korundu, LLM'nin maskeli
planı agent güvenlik kapısından geçti, kullanıcı onayı simüle edildi ve düzeltilmiş çalışma
kopyası yeniden doğrulandığında uyarı sayısı sıfır oldu.

| Fixture | İzinli kural | Plan üreticisi | Sonuç |
|---|---|---|---|
| `demo_tax_exclusive_error.xml` | `recalculate-tax-exclusive-total` | Groq fallback | 0 kalan uyarı |
| `demo_tax_inclusive_error.xml` | `recalculate-tax-inclusive-total` | Gemini | 0 kalan uyarı |
| `demo_payable_error.xml` | `recalculate-payable-total` | Groq fallback | 0 kalan uyarı |

Çalışma çıktısı: `data/evaluation/web_acceptance.json` (bilerek Git dışında tutulur; işlem
kimliği/hash içerir, XML içeriği içermez).

### Sunum preflight ve API ölçümü

`python scripts/run_demo_preflight.py` RAG indeksini hazır buldu; aktif üretim zinciri
Gemini → Groq → deterministik kaynak özeti olarak doğrulandı. Aynı RAG bulgusuyla üçer
tekrarlı canlı ölçüm şu sonucu verdi:

| Sağlayıcı | Model | Başarılı tekrar | Ortalama süre | Not |
|---|---|---:|---:|---|
| Gemini | `gemini-3.5-flash-lite` | 2/3 | 6,703 sn | Bir çağrı HTTP durum hatasıyla güvenli biçimde başarısız oldu. |
| Groq | `openai/gpt-oss-120b` | 3/3 | 5,341 sn | Fallback sağlayıcısı tüm tekrarları üretti. |

Ölçüm betiği `scripts/benchmark_api_providers.py`, ham fatura veya API anahtarı yazmadan
sonucu `data/evaluation/api_provider_benchmark.json` altında saklar. Değerler ağ/sağlayıcı
yüküne bağlıdır; sunumda preflight yeniden çalıştırılmalıdır.

### Uzak CI kanıtı

Private GitHub reposu `Muhammed-Cosgun/FaturaGuard-AI` oluşturuldu ve uzak Ubuntu runner
üzerindeki GitHub Actions CI, `d093577` commit'i için başarıyla tamamlandı. İlk iki koşu,
Linux runner'da `scripts` import yolunu açıkça tanımlamayan CI yapılandırmasının yakaladığı
gerçek bir taşınabilirlik sorununu gösterdi; `scripts/__init__.py` ve CI `PYTHONPATH`
tanımıyla düzeltildi. Başarılı üçüncü koşu lint ve 138 testi tamamladı.

### Kod kalitesi ve temiz ortam denemesi

- `ruff check .`: başarılı.
- `pytest --basetemp .pytest-work-delivery-final`: **138 passed**.
- Sıfırdan venv yaratma denemesinde Python'un geçici dizini bu yürütme ortamında yazma izni
  vermedi. `TEMP`/`TMP` proje içindeki `.build-temp` dizinine yönlendirilince venv ve pip
  kuruldu; ancak bu otomasyon ortamının 30 saniyelik işlem limiti tüm bağımlılık kurulumunu
  bitirmeye izin vermedi. Bu, uygulama hatası değil, teslimden önce normal yerel CMD'de
  tekrar edilmesi gereken ortam-kısıtlı kanıttır.

### n8n doğrulaması ve sınırlılık

`n8n/faturaguard-webhook-workflow.json` JSON olarak doğrulandı: pasif (varsayılan güvenli)
iki düğümlü webhook akışı mevcuttur ve yalnızca işlem özeti taşır. Docker CLI bulunmasına
rağmen bu ortamda Docker daemon çalışmadığı, `npx n8n` paket kurulumu da yürütme süresi
sınırını aştığı için gerçek n8n sunucusunda import/aktif webhook çağrısı burada tamamlanamadı.
Bu V1 için isteğe bağlı otomasyondur; teslimde "yerel n8n canlı çalıştırması" olarak açık
bir sınırlılık şeklinde sunulmalıdır.

## Doğrulama ortamı notu

Bu geliştirme ortamı yerel TCP dinleme ve Windows `asyncio` olay döngüsünün kullandığı yerel soketleri engellediğinden, tarayıcı üzerinden manuel `localhost` kontrolü burada gerçekleştirilemedi. Bu ürün sınırlaması değildir. Manuel web kontrolü, normal yerel CMD ortamında `uvicorn faturaguard.main:app --reload` komutuyla ve `DEMO_SCENARIO.md` içindeki adımlarla teslim öncesi yapılacaktır.
