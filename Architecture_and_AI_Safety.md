# FaturaGuard AI — Mimari ve Yapay Zekâ Güvenliği

## Mimari

```text
Jinja2 + HTML/CSS + normal form POST web arayüzü
        ↓
FastAPI uygulaması
 ├─ XML saklama / hash / SQLite denetim izi
 ├─ efatura-kontrol adaptörü
 ├─ Hibrit GİB RAG
 │   ├─ doğrulanmış GİB belgeleri → chunks + metadata
 │   ├─ çok dilli embeddings → kalıcı Chroma koleksiyonu
 │   ├─ lexical arama (BM25 / tam teknik terimler)
 │   └─ hybrid retrieval + rerank
 ├─ LangGraph agent iş akışı
 │   └─ allowlist araçlar, koşullu yönlendirme ve insan onayı
 ├─ güvenli düzeltme motoru / diff / yeniden doğrulama
 └─ raporlama ve isteğe bağlı n8n webhook'u
```

## Bileşen sorumlulukları

- Doğrulama adaptörü: `efatura-kontrol` sonuçlarını tek bulgu modeline dönüştürür. Harici kütüphanenin veri tipleri arayüz veya diğer iş kurallarına doğrudan sızmaz.
- Önceliklendirme: hata kodu, seviye ve kaynakla çalışan deterministik iş kuralları kullanır; önceliği bir dil modeli belirlemez.
- RAG: yalnızca doğrulanmış resmî GİB kaynaklarından açıklama getirir. e-Fatura PDF'lerinin yanında SHA-256 ile doğrulanan UBL-TR kılavuz arşivindeki Fatura ve Ortak Elemanlar dokümanları da indekslenir. Chunk'larda kaynak kimliği, başlık, URL, sayfa ve metin; kaynak envanterinde tarih, sürüm ve ham dosya hash'i saklanır.
- Chroma: doğrulanmış GİB chunks'larının kalıcı vektör koleksiyonudur; içerik ve metadata filtreleri buradan getirilir.
- Hibrit retrieval/rerank: `intfloat/multilingual-e5-small` semantic araması ile BM25 araması ayrı üretilir. İlk 12'şer aday birleştirilir; 0.55 semantic + 0.30 normalize BM25 + 0.15 terim eşleşmesi puanıyla sıralanır. Ayrı bir neural reranker kullanılmaz.
- Agent: LangGraph üzerinde tanımlı araçlar dışında işlem yapamaz. Belge kabul grafiği yerel `validate_document` → `propose_safe_corrections` → `assess_document_risk` → `await_human_review` / `report_ready` düğümlerini çalıştırır. Risk aracı, belgeyi `blocked`, `needs_human_review` veya `ready_for_manual_submission_review` rotasına alır; öncelikli bulguları, RAG ile incelenmesi gereken adımları ve onaya hazır düşük riskli düzeltme sayısını üretir. Karar grafiği ise kullanıcı onayı sonrasında `apply_safe_correction` → `revalidate_corrected_copy` → `report_correction_result` sırasını yürütür; red kararı yalnızca kaydedilir. Kaynaklı açıklama için alt akış: getir → rerank → kaynaklı açıkla → insan incelemesi. Bu araçların her çağrısı SQLite audit trail'e yazılır.
- Kaynaklı açıklama: Ollama yerel API'sine JSON şeması gönderilir. LLM çıktısındaki her atıf, retrieval ile dönen GİB kanıtlarıyla bire bir eşleşmek zorundadır; eşleşmeyen atıf reddedilir.
- LLM tabanlı düzeltme planı: Agent, yereldeki güvenli düzeltme motorunun hesapladığı adayları LLM'e maskeli tokenlarla (`TARGET_FIELD_1`, `CURRENT_VALUE_1`, `RECALCULATED_VALUE_1`) sunar. LLM yalnızca mevcut adaylardan birini seçen yapılandırılmış patch planı üretir; VKN/TCKN, isim, adres, IBAN, dosya adı, hash, ham XML ve gerçek tutarlar uzak sağlayıcıya aktarılmaz. Agent planı yereldeki adayla bire bir eşleştiremezse veya kaynak kanıtı yetersizse düzeltme engellenir ve insan incelemesine yönlenir.
- Model sağlayıcısı: yerel LLM veya API sağlayıcısı değiştirilebilir adaptörlerle bağlanır. Güncel demoda anahtarlar tanımlıyken Gemini birincil, Groq yedektir. Yerel açıklama seçeneği `gemma3:4b`, eski benchmark'ta 4/4 şemalı çıktı üretmiştir; bu anlamsal doğruluk garantisi değildir. Model çevresel ayarla değiştirilebilir.
- Hızlı API modu: `GEMINI_API_KEY` tanımlandığında düşük gecikmeli Gemini Flash-Lite, en güçlü iki GİB kanıt parçası ve 12 saniyelik istek bütçesiyle birincil üretici olur. Süre aşımı veya API hatasında yapılandırılmış çıktıyı Groq GPT-OSS 120B ikinci sağlayıcısı dener; o da başarısızsa uzun yerel LLM beklenmeden doğrulanmış atıflarla deterministik kaynak özeti gösterilir. Anahtar yoksa uygulama tamamen yerel Ollama moduna döner. API sınırından yalnızca statik doğrulama kuralı ve retrieval/rerank ile seçilmiş GİB kanıt parçaları geçer; XML, dosya adı, SHA-256, taraf/tutar bilgileri ve yerel yol geçmez. API anahtarı kaynak kodda, raporda veya audit kaydında tutulmaz.
- Bağımsız ücretsiz yedek: `GROQ_API_KEY` tanımlı olduğunda Gemini başarısızlığı sonrası Groq Chat Completions API denenir. Groq çıktısı strict JSON Schema, Pydantic doğrulaması ve retrieval kanıtlarıyla bire bir citation kontrolünden geçer. İki sağlayıcı da başarısızsa deterministik GİB kaynak özeti gösterilir; ücretsiz kota hataları veya servis kesintileri kullanıcıyı uzun yerel LLM beklemesine sokmaz.
- MCP: agent araçları için aynı sözleşmeyi dış sistemlere açabilecek standart adaptör sınırıdır; ilk sürümde uygulama içi araçlar esas alınır.
- Düzeltme motoru: sadece izin listesinde bulunan, düşük riskli aritmetik dip toplam değişikliklerini çalışma kopyasına uygular. Katalog `LineExtensionAmount`, `TaxExclusiveAmount`, `TaxInclusiveAmount` ve `PayableAmount` alanlarıyla sınırlıdır; bir alanın bağımlılığı olan alt toplamda bulgu varsa üst alan için teklif oluşturmaz.
- İşlem geçmişi: iş özeti, doğrulama sonucu ve audit olayları yerel SQLite veritabanında saklanır. Tam XML diff'i veritabanı dışında, işlem kimliğiyle ilişkili ayrı bir dosyada tutulur.

## Güvenlik kuralları

- Uygulama orijinal dosyaya tekrar yazmaz; SHA-256 kaydını saklar. Dosya sistemi düzeyinde değiştirilemezlik veya şifreleme uygulanmaz.
- Kullanıcı onayı olmadan XML değiştirilemez.
- Agent, kullanıcıdan açık `approve` kararı gelmeden düzeltme aracını çağıramaz; LLM metni hiçbir zaman XML değişikliği komutu değildir.
- Kullanıcı onayı yalnızca `decision=propose` olan, maskeli patch tokenları güvenlik politikasıyla tam eşleşen LLM planlarında sunulur. Agent gerçek XML değerlerini yerel aday eşlemesiyle çözer; yeni değer veya XML yolu icat eden planlar reddedilir.
- E-imza, taraf bilgileri, vergi kimlik bilgileri, fatura numarası, tarih, satır tutarları ve vergi oranları otomatik düzeltilmez. İzinli dip toplamlar yalnızca mevcut satır/vergi/indirim/artırım değerlerinden tekrar hesaplanır.
- Her işlem, dosya bütünlük özeti ve karar kaydıyla ilişkilendirilir.
- Kaynak bulunmadığında agent kesin bir yönlendirme yapmaz.
- Agent, yalnızca yeterli rerank ve teknik-terim eşleşmesi olan kanıtta açıklama üretir; versiyon geçmişi gibi düşük bilgi değerli parçalar kaynak olarak elenir.
- RAG kaynak envanteri `resources/gib/official_sources.json` dosyasında tutulur; kaynak dışı içerik indekslenmez.
- Her yerel kaynak kopyası RAG'a alınmadan önce envanterdeki SHA-256 değeriyle doğrulanır.
- İlk RAG sürümü GİB PDF sayfalarını parçalara bölüp yerel ve açıklanabilir arama yapar; her sonuçta belge, URL ve sayfa numarası zorunludur.
- XML, GİB kaynağı, kullanıcı girdisi ve RAG metni güvenilmeyen veri kabul edilir; hiçbiri agent sistem talimatını, araç allowlist'ini veya kullanıcı onayı gereğini değiştiremez.
- Agent'ın RAG sorgusu ham XML hata metninden üretilmez. Desteklenen bulgu kodları, ilgili UBL-TR teknik terimlerini içeren sabit bir güvenilir sözlüğe eşlenir; tanınmayan kodlarda yalnızca kısa kimlik alanları kullanılır.
- Güvenilir sözlük; XML/XSD, kimlik, tarih-saat, senaryo, para birimi-birim, taraf, vergi-istisna, tevkifat, iade, ödeme, XAdES ve aritmetik hata ailelerini kapsar. Hata ailesi eşlenemediğinde sistem genel bir resmî kaynak araması yapar; kanıt eşiği geçilmezse açıklama üretmeden insan incelemesinde durur.
- LLM sağlayıcılarına ham bulgu mesajı, XML parçası, satır numarası veya dosya metadatası gönderilmez. İstek yalnızca bulgu kodu/seviyesi, doğrulama kuralı, önerilen kullanıcı adımı ve retrieval ile seçilmiş resmî GİB kanıtlarını taşır. Bu izinli bağlam, sağlayıcı çağrısından hemen önce merkezi `PrivacyRedactor` katmanından geçer; VKN/TCKN, IBAN, e-posta, telefon ve hesap numarası düzenli ifadeyle maskelenir, XML/adres/kişi adı gibi hassas alan anahtarları ise tamamen bastırılır.
- Agent'ın LLM çıktısı Pydantic şema ile doğrulanır. Şema dışı çıktı veya yeterli kaynak yoksa işlem "insan incelemesi gerekli" durumuna yönlenir.
- Yerel LLM geçici olarak yanıt veremezse kaynaklı işlem hata sayfasına düşmez; `generation_unavailable` durumuyla insan incelemesine yönlenir ve retrieval ile bulunan resmî kanıtlar kullanıcıya gösterilir.
- Ollama çıktısı JSON sözleşmesini doğrulayamazsa, sistem LLM metnini kullanmaz. Aynı doğrulanmış bulgu ve retrieval kanıtlarıyla `deterministic_fallback` kaynak özeti oluşturur; bu özet her zaman insan incelemesi gerektirir.
- Chroma koleksiyonuna yalnızca envanter + SHA-256 denetiminden geçen GİB kaynakları yazılabilir.

## RAG kalite ölçümü

- Golden sorgu setinde `Recall@k` ve `MRR` kaydedilir.
- Semantic, lexical ve hibrit+rereank sonuçları karşılaştırılır.
- Kaynak kapsamı (citation coverage), sonuç URL'lerinin GİB adresi olmasını ölçer. Kaynaksız kesin cevap oranı için ayrı otomatik metrik yoktur; atıf eşleme ve kanıt eşiği güvenlik kontrolleri uygulanır.

## Çalıştırma ve rapor sınırları

- Yanıt üreticisi: ConversationModel.last_provider yalnızca şeması geçerli
  sonuç döndüren sağlayıcıyla güncellenir. Final cevabın kontrolü geçerse
  generated_by alanına yazılır; yerel yedekte local olur. providers sadece
  deneme izidir. Eski kayıtta gerçek sağlayıcı bilinmiyorsa unknown korunur.
- Dayanaklar: yürütülen araçların gerçekten okuduğu kodlar ve sabit Türkçe kayıt
  türleri yerelde kaydedilir; modelin bu alanları beyan etmesi istenmez. Yerel
  yedek için dayanaklar yerel yanıt türünden türetilir, başarısız model araçları
  yerel yanıtın dayanağı gibi sunulmaz. producer_label hesaplanan bir UI alanıdır.
- chat_quality bilinen teknik anahtarları ve belirli doğrudan durum/seviye/evre
  çelişkilerini red koduyla mevcut tek onarım akışına yönlendirir. 24 olumlu/
  olumsuz vaka, doğru metnin yanlış reddedilmesini de kontrol eder. Genel doğal
  dil doğruluğu veya mevzuat destek ilişkisi bu sınırlı kurallarla kanıtlanmaz.
- Kaynak kartındaki excerpt, yalnızca getirilen resmî chunk'ın modele verilen
  ilk 1800 karakterinden seçilir; güvenilir kod sözlüğünün teknik terimi çevresinde
  kısa bir pencere alınır. Boş/eksik metin yerine alıntı uydurulmaz. HTML autoescape,
  JS textContent ve HTTPS resmî alan doğrulaması korunur. Alıntı, atfın anlamsal
  olarak bütün iddiaları desteklediğinin otomatik ispatı değildir.

- Sohbet görünümü: sonuç/rapor şablonları document-content ve document_chat
  aside'ını CSS Grid ile ayırır. document-chat.css masaüstünde sticky panel ve
  bağımsız mesaj scroll'u sağlar. JS ilk yüklemede paneli kapalı tutar; içerik
  1040 px ortalanır. Açılınca grid ikinci sütuna yer açar ve ana içerik sola
  kayar; kapanınca eski ölçüler geri gelir. Geçiş reduced-motion'a uyar;
  ilk yüklemede animasyon yoktur. Açık/kapalı tercih boyut değişiminde korunur;
  kapatma sohbet DOM'unu veya devam eden isteği silmez. 1100 px altında modal açılır;
  rol/aria-modal, arka plan inert ve odak döngüsü/geri dönüşü yönetilir. Destekleyen
  tarayıcıda visualViewport ile mobil görünen alana uyum sağlanır; fiziksel
  telefon klavyesi ayrı cihaz testinde ölçülmedi. JS yokken aside normal akışta
  ve standart POST formu erişilebilir kalır. HTML soru/yanıtları escape eder,
  JS metinleri textContent ile ekler. Pending balonu gerçek model streaming'i değildir.

- Belge asistanı: `ConversationalDocumentChat` LangGraph'ta `interpret_question`
  → `read_document_tools` → `compose_answer` çalıştırır. İlk LLM çağrısı şemalı
  plan üretir; uygulama en fazla dört izinli salt okunur aracı çalıştırır; ikinci
  LLM çağrısı araç verilerinden yanıt üretir. Bu, tek geçişli şemalı araç
  orkestrasyonudur; sınırsız döngü veya sağlayıcıya devredilmiş araç çalıştırma yoktur.
- Kullanıcının 21.11.2026 talebiyle eski “soru/geçmiş sağlayıcıya gitmez” sohbet
  sınırı değişti. Soru, son 6 turun maskeli metinleri ve gerekli bulgu bağlamı
  Gemini/Groq'a gider. `ConversationMask` bilinen XML yaprak metinlerini, PII,
  anahtar, URL/yol ve sayıları filtreler. Teklif tutarları doğrulanan yerel
  `[VALUE_n]` tokenlarıyla açılır. Karşılaştırma raporunun doğrulanmış adetleri
  `[COUNT_n]` tokenlarıyla açılır; genel maskelerden sayı tahmin edilmez.
  Tutar tokenları noktalama sonlarında da bağlanır ve PII regex'inden önce
  korunur; gerçek parasal değer sağlayıcıya verilmez. Ham XML/dosya metadatası payload'a konmaz;
  orijinal belge okunamazsa sağlayıcı çağrılmaz. Serbest özel isimlerin tamamını
  maskelediği garanti edilmez; arayüz kişisel bilgi yazılmamasını belirtir.
- Araç adları: current_findings, correction_proposals, validation_comparison,
  official_sources. Başka iş kimliği, dosya yolu, URL veya yazma argümanı kabul
  edilmez. RAG eski güvenilir kod sözlüğü ve kanıt eşiğini kullanır. Atıflar
  yalnızca gerçekten getirilen kanıt ID'lerinden kurulur; bilinmeyen atıf/değer
  tokenı, çözülemeyen sayı/PII maskesi ve modelin yazdığı URL reddedilir.
  Güncel teklif durumundan approval_available üretilir; hazır teklif yoksa
  model yeni onay adımı önermemelidir. Bilinen doğrudan onay yönlendirme
  ifadeleri ayrıca reddedilir; bu kontrol genel anlamsal doğruluğu kanıtlamaz.
  Yetki bağlamı sonuç ekranında düzeltme onayı bulunduğunu ve sohbetin onay
  veremediğini ayrı alanlarla belirtir; imza ve gönderim uygulama kapsamı dışındadır.
  chat_facts, teklifin already_applied/plan_not_ready/red/bekleyen durumlarını
  ayırır. Karşılaştırma aracı severity_changes ile net adet değişimini, ayrıca
  finding_changes ile kod+seviye bazında ilk/güncel/giderilen/yeni adetleri verir.
  Net adedin aynı kalması farklı kodların giderilmediğini göstermez. Talimat
  sıfır kalan hata adedini giderilmiş saymamayı ve Bilgi seviyesini korumayı ister;
  bu bağlam/talimat iyileştirmesi bütün serbest ifadelerin doğruluk ispatı değildir.
  Karşılaştırma yanıtı reddedilirse yerel yedek genel router yerine doğrudan
  gerçek önce/sonra kaydını açıklar. Gemini store=false; sunucu tarafında
  konuşma ID'si tutulmaz. Bu ayar bütün sağlayıcı veri saklama politikasını
  ortadan kaldırdığı anlamına gelmez.
- Normal iki üretim aşamasında Gemini → Groq yedeği vardır. Şeması geçerli ama
  atıf/token/onay kontrolü reddedilen final yanıt, aynı maskeli araç sonuçları
  ve yalnızca sabit red koduyla bir kez yeniden üretilir; Groq varsa öncelenir.
  Reddedilen metin bu onarım isteğine eklenmez, araçlar yeniden çalıştırılmaz.
  Normalde en çok dört, onarım dahil en çok altı HTTP denemesi vardır.
  Şema/servis hatasında sağlayıcı zinciri kendi yedeğini dener; bu tek seferlik
  onarım final yanıtın içerik sözleşmesi içindir. Sonuç yine geçersizse
  `DocumentChat` uzak model çağırmadan yerel
  kayıt yedeği üretir, panel bunu ayrı etiketler. Cevabın anlamsal doğruluğu
  hâlâ canlı insan değerlendirmesi gerektirir; araç güvenliği sıfır halüsinasyon değildir.
- Tanı kaydı yalnızca sabit failure_code/validation_issues, repair_attempted,
  sağlayıcı ve araç adlarını içerir. Reddedilen model metni, anahtar veya ham HTTP
  gövdesi audit'e yazılmaz. Olumsuz “onay sürecine geçmeniz gerekmiyor” ifadesi
  olumlu onay önerisi sayılmaz; bu dil kontrolü genel anlam doğrulayıcı değildir.
- `POST /jobs/{job_id}/chat` yalnızca sohbet kaydı ve audit olayı ekler; düzeltme
  motoruna veya karar grafiğine erişmez. Sohbet ekleme, SQLite transaction'ında
  güncel payload'ın yalnızca chat_history alanını değiştirir; uzun model çağrısında
  yapılmış yeni düzeltme kararları eski iş kopyasıyla ezilmez.
- Soru en çok 600 karakterdir. İşler arası bulgu seçimi reddedilir, güncel
  corrected_report varsa o kullanılır. Son 20 tur saklanır. Yanıt/soru düz metin
  olarak escape edilir; tarayıcı JS'i innerHTML kullanmaz. Atıflar HTTPS GİB URL'si olmalıdır.

- Güncel demo zinciri Gemini → Groq → deterministik kaynak özetidir. Yerel Gemma
  yalnızca anahtarsız/açık yerel açıklama seçeneğidir; Ollama düzeltme-planı adaptörü yoktur.
- Web istekleri model yanıtını bekler. Gerçek arka plan iş kuyruğu, polling,
  streaming veya HTMX entegrasyonu uygulanmış değildir.
- Citation eşleşmesi atfın retrieval sonuçlarında bulunduğunu doğrular; iddianın
  kanıttan mantıksal olarak çıktığını veya sıfır halüsinasyonu kanıtlamaz.
- HTML rapor tam XML diff'i gösterebilir; JSON rapor ham XML/tam diff'i dışlar,
  fakat dosya adı, bulgu metni ve teklif tutarları içerebilir. Rapor anonim değildir.
- FastAPI lifespan kapanışı cached Schematron motorunu event loop thread'i
  bitmeden temizler; native kapanış regresyonu ayrı süreçte test edilir.
