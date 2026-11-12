# FaturaGuard AI — Mimari ve Yapay Zekâ Güvenliği

## Mimari

```text
Jinja2 + HTMX web arayüzü
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
- RAG: yalnızca doğrulanmış resmî GİB kaynaklarından açıklama getirir. e-Fatura PDF'lerinin yanında SHA-256 ile doğrulanan UBL-TR kılavuz arşivindeki Fatura ve Ortak Elemanlar dokümanları da indekslenir. Parçalar kaynak kimliği, başlık, resmî URL, sayfa numarası, sürüm ve hash ile saklanır.
- Chroma: doğrulanmış GİB chunks'larının kalıcı vektör koleksiyonudur; içerik ve metadata filtreleri buradan getirilir.
- Hibrit retrieval/rerank: semantic arama ile lexical arama ayrı üretilir; adaylar birleştirilir ve teknik-terim eşleşmesi, benzerlik ve belge bağlamıyla tekrar sıralanır.
- Agent: LangGraph üzerinde tanımlı araçlar dışında işlem yapamaz. Belge kabul grafiği yerel `validate_document` → `propose_safe_corrections` → `assess_document_risk` → `await_human_review` / `report_ready` düğümlerini çalıştırır. Risk aracı, belgeyi `blocked`, `needs_human_review` veya `ready_for_manual_submission_review` rotasına alır; öncelikli bulguları, RAG ile incelenmesi gereken adımları ve onaya hazır düşük riskli düzeltme sayısını üretir. Karar grafiği ise kullanıcı onayı sonrasında `apply_safe_correction` → `revalidate_corrected_copy` → `report_correction_result` sırasını yürütür; red kararı yalnızca kaydedilir. Kaynaklı açıklama için alt akış: getir → rerank → kaynaklı açıkla → insan incelemesi. Bu araçların her çağrısı SQLite audit trail'e yazılır.
- Kaynaklı açıklama: Ollama yerel API'sine JSON şeması gönderilir. LLM çıktısındaki her atıf, retrieval ile dönen GİB kanıtlarıyla bire bir eşleşmek zorundadır; eşleşmeyen atıf reddedilir.
- LLM tabanlı düzeltme planı: Agent, yereldeki güvenli düzeltme motorunun hesapladığı adayları LLM'e maskeli tokenlarla (`TARGET_FIELD_1`, `CURRENT_VALUE_1`, `RECALCULATED_VALUE_1`) sunar. LLM yalnızca mevcut adaylardan birini seçen yapılandırılmış patch planı üretir; VKN/TCKN, isim, adres, IBAN, dosya adı, hash, ham XML ve gerçek tutarlar uzak sağlayıcıya aktarılmaz. Agent planı yereldeki adayla bire bir eşleştiremezse veya kaynak kanıtı yetersizse düzeltme engellenir ve insan incelemesine yönlenir.
- Model sağlayıcısı: yerel LLM veya API sağlayıcısı, aynı yapılandırılmış çıktı sözleşmesini uygulayan değiştirilebilir bir adaptör üzerinden bağlanır. Varsayılan demo sağlayıcısı yerel Ollama `gemma3:4b` modelidir; dört gerçek bulgu vakasındaki %100 geçerli yapılandırılmış çıktı sonucu nedeniyle seçilmiştir. Model çevresel ayarla değiştirilebilir.
- Hızlı API modu: `GEMINI_API_KEY` tanımlandığında düşük gecikmeli Gemini Flash-Lite, en güçlü iki GİB kanıt parçası ve 12 saniyelik istek bütçesiyle birincil üretici olur. Süre aşımı veya API hatasında yapılandırılmış çıktıyı Groq GPT-OSS 120B ikinci sağlayıcısı dener; o da başarısızsa uzun yerel LLM beklenmeden doğrulanmış atıflarla deterministik kaynak özeti gösterilir. Anahtar yoksa uygulama tamamen yerel Ollama moduna döner. API sınırından yalnızca statik doğrulama kuralı ve retrieval/rerank ile seçilmiş GİB kanıt parçaları geçer; XML, dosya adı, SHA-256, taraf/tutar bilgileri ve yerel yol geçmez. API anahtarı kaynak kodda, raporda veya audit kaydında tutulmaz.
- Bağımsız ücretsiz yedek: `GROQ_API_KEY` tanımlı olduğunda Gemini başarısızlığı sonrası Groq Chat Completions API denenir. Groq çıktısı strict JSON Schema, Pydantic doğrulaması ve retrieval kanıtlarıyla bire bir citation kontrolünden geçer. İki sağlayıcı da başarısızsa deterministik GİB kaynak özeti gösterilir; ücretsiz kota hataları veya servis kesintileri kullanıcıyı uzun yerel LLM beklemesine sokmaz.
- MCP: agent araçları için aynı sözleşmeyi dış sistemlere açabilecek standart adaptör sınırıdır; ilk sürümde uygulama içi araçlar esas alınır.
- Düzeltme motoru: sadece izin listesinde bulunan, düşük riskli değişiklikleri çalışma kopyasına uygular.
- İşlem geçmişi: iş özeti, doğrulama sonucu ve audit olayları yerel SQLite veritabanında saklanır. Tam XML diff'i veritabanı dışında, işlem kimliğiyle ilişkili ayrı bir dosyada tutulur.

## Güvenlik kuralları

- Orijinal dosya salt okunur korunur.
- Kullanıcı onayı olmadan XML değiştirilemez.
- Agent, kullanıcıdan açık `approve` kararı gelmeden düzeltme aracını çağıramaz; LLM metni hiçbir zaman XML değişikliği komutu değildir.
- Kullanıcı onayı yalnızca `decision=propose` olan, maskeli patch tokenları güvenlik politikasıyla tam eşleşen LLM planlarında sunulur. Agent gerçek XML değerlerini yerel aday eşlemesiyle çözer; yeni değer veya XML yolu icat eden planlar reddedilir.
- E-imza, taraf bilgileri, vergi kimlik bilgileri, fatura numarası, tarih ve ticari tutarı değiştiren alanlar otomatik düzeltilmez.
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
- Her cevapta kaynak kapsamı (citation coverage) ve kaynaksız kesin cevap oranı ölçülür.
