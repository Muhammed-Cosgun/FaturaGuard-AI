# Üçüncü taraf bileşenler ve kaynaklar

FaturaGuard AI, aşağıdaki bileşenleri kullanır. Kurulum ve sürüm aralıkları
pyproject.toml, test edilmiş Windows sürümleri requirements-windows-py314.lock.txt
içindedir. Bileşenlerin kendi lisansları geçerlidir; bu belge yeni bir lisans vermez.

| Bileşen | Projedeki kullanım | Kaynak |
|---|---|---|
| efatura-kontrol 0.1.0 | GİB XSD/Schematron ve hesap bulguları | https://github.com/BerkantACUN/efatura-kontrol |
| FastAPI / Starlette / Uvicorn | Yerel web sunucusu | https://fastapi.tiangolo.com/ |
| Jinja2 | HTML şablonları | https://jinja.palletsprojects.com/ |
| LangGraph | Durum ve koşullu agent akışı | https://github.com/langchain-ai/langgraph |
| Chroma | Yerel vektör deposu | https://github.com/chroma-core/chroma |
| sentence-transformers / Hugging Face Hub | Yerel embedding yükleme | https://github.com/huggingface/sentence-transformers |
| intfloat/multilingual-e5-small | Embedding ağırlıkları; model dosyaları Git'e eklenmez | https://huggingface.co/intfloat/multilingual-e5-small |
| rank-bm25 | Sözcüksel retrieval | https://github.com/dorianbrown/rank_bm25 |
| lxml / pypdf / SaxonC-HE | XML, PDF ve Schematron altyapısı | https://github.com/lxml/lxml / https://github.com/py-pdf/pypdf / https://www.saxonica.com/ |
| n8n Community | Yerel iş süreci otomasyonu; AI Assistant kullanılmaz | https://github.com/n8n-io/n8n |
| Mailpit | Dışarı göndermeyen yerel test posta kutusu | https://github.com/axllent/mailpit |

Resmî GİB belgeleri ve bağlantıları resources/gib/official_sources.json
envanterindedir. Ham dosyalar hash doğrulamasıyla ayrıca temin edilir.
Repodaki baseline_invoice.xml resmî UBL-TR örnek senaryosuna dayanan test
belgesidir; buradaki kimlik/tutarlar gerçek müşteri verisi olarak kullanılmaz.
İmza testleri yapısal örneklerdir, gerçek özel anahtar/sertifika içermez.

n8n'in ücretsiz yerel Community sürümü kendi kullanım lisansına tabidir;
uygulamaya ücretli SaaS veya yeniden satış lisansı verildiği iddia edilmez.
Gemini/Groq API koşulları ve ücretsiz kotaları kullanıcı hesabına bağlıdır.
Proje sahibinin kodu için ayrıca açık kaynak lisansı seçilmedi; öğretmene
private repo erişimi vermek üçüncü taraf lisanslarını değiştirmez.
