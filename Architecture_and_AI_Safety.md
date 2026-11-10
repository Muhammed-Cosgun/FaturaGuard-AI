# FaturaGuard AI — Mimari ve Yapay Zekâ Güvenliği

## Mimari

```text
Jinja2 + HTMX web arayüzü
        ↓
FastAPI uygulaması
 ├─ XML saklama / hash / denetim izi
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
- RAG: yalnızca doğrulanmış resmî GİB kaynaklarından açıklama getirir. Parçalar kaynak kimliği, başlık, resmî URL, sayfa numarası, sürüm ve hash ile saklanır.
- Chroma: doğrulanmış GİB chunks'larının kalıcı vektör koleksiyonudur; içerik ve metadata filtreleri buradan getirilir.
- Hibrit retrieval/rerank: semantic arama ile lexical arama ayrı üretilir; adaylar birleştirilir ve teknik-terim eşleşmesi, benzerlik ve belge bağlamıyla tekrar sıralanır.
- Agent: LangGraph üzerinde tanımlı araçlar dışında işlem yapamaz. Akış: doğrula → önceliklendir → getir → rerank → kaynaklı açıkla → güvenlik denetimi → onay bekle → uygula → yeniden doğrula → raporla.
- Kaynaklı açıklama: Ollama yerel API'sine JSON şeması gönderilir. LLM çıktısındaki her atıf, retrieval ile dönen GİB kanıtlarıyla bire bir eşleşmek zorundadır; eşleşmeyen atıf reddedilir.
- Model sağlayıcısı: yerel LLM veya API sağlayıcısı, aynı yapılandırılmış çıktı sözleşmesini uygulayan değiştirilebilir bir adaptör üzerinden bağlanır. Varsayılan demo sağlayıcısı yerel Ollama `qwen2.5:7b` modelidir.
- MCP: agent araçları için aynı sözleşmeyi dış sistemlere açabilecek standart adaptör sınırıdır; ilk sürümde uygulama içi araçlar esas alınır.
- Düzeltme motoru: sadece izin listesinde bulunan, düşük riskli değişiklikleri çalışma kopyasına uygular.

## Güvenlik kuralları

- Orijinal dosya salt okunur korunur.
- Kullanıcı onayı olmadan XML değiştirilemez.
- E-imza, taraf bilgileri, vergi kimlik bilgileri, fatura numarası, tarih ve ticari tutarı değiştiren alanlar otomatik düzeltilmez.
- Her işlem, dosya bütünlük özeti ve karar kaydıyla ilişkilendirilir.
- Kaynak bulunmadığında agent kesin bir yönlendirme yapmaz.
- RAG kaynak envanteri `resources/gib/official_sources.json` dosyasında tutulur; kaynak dışı içerik indekslenmez.
- Her yerel kaynak kopyası RAG'a alınmadan önce envanterdeki SHA-256 değeriyle doğrulanır.
- İlk RAG sürümü GİB PDF sayfalarını parçalara bölüp yerel ve açıklanabilir arama yapar; her sonuçta belge, URL ve sayfa numarası zorunludur.
- XML, GİB kaynağı, kullanıcı girdisi ve RAG metni güvenilmeyen veri kabul edilir; hiçbiri agent sistem talimatını, araç allowlist'ini veya kullanıcı onayı gereğini değiştiremez.
- Agent'ın LLM çıktısı Pydantic şema ile doğrulanır. Şema dışı çıktı veya yeterli kaynak yoksa işlem "insan incelemesi gerekli" durumuna yönlenir.
- Chroma koleksiyonuna yalnızca envanter + SHA-256 denetiminden geçen GİB kaynakları yazılabilir.

## RAG kalite ölçümü

- Golden sorgu setinde `Recall@k` ve `MRR` kaydedilir.
- Semantic, lexical ve hibrit+rereank sonuçları karşılaştırılır.
- Her cevapta kaynak kapsamı (citation coverage) ve kaynaksız kesin cevap oranı ölçülür.
