# FaturaGuard AI

FaturaGuard AI, e-Fatura XML belgelerini doğrulayan, resmî GİB kaynaklarıyla hataları açıklayan ve kullanıcı onayıyla sınırlı düzeltmeler uygulayan bir web uygulamasıdır.

## Durum

V1 geliştirme ve temel kabul testleri tamamlandı. Uygulama, yerel demo ve eğitim projesi amacıyla hazırlanmıştır; GİB'e gerçek belge gönderimi veya e-imza üretimi yapmaz.

## Hedef teknoloji

- FastAPI
- Jinja2 ve HTMX
- `efatura-kontrol` doğrulama kütüphanesi

## Başlangıç

Python 3.11 veya üzeriyle:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
uvicorn faturaguard.main:app --reload
```

Tarayıcıdan `http://127.0.0.1:8000` adresini açın. Sağlık denetimi `http://127.0.0.1:8000/health` adresindedir.

Kalite kontrolleri:

```powershell
ruff check .
pytest
```

## Resmî GİB RAG indeksleri

Önce GİB PDF'lerinden kaynak parçaları, ardından Chroma vektör koleksiyonu üretilir:

```powershell
python scripts/build_gib_index.py
python scripts/build_chroma_index.py
```

Chroma koleksiyonu yerel olarak `data/chroma/` altında saklanır. Sadece `resources/gib/official_sources.json` envanterinde tanımlanan ve SHA-256 özeti doğrulanan GİB dosyaları indekslenir.

İlk `build_chroma_index.py` çalıştırması embedding modelini indirebilir. Sonraki sorgularda model yalnızca proje içindeki `data/models/` yerel önbelleğinden yüklenir.

## Yerel LLM smoke testi

Varsayılan yerel açıklama modeli `gemma3:4b`'tür. Dört gerçek bulgu vakasında geçerli yapılandırılmış LLM çıktısı oranı %100, ortalama yanıt süresi 43,42 saniye ölçüldü. Farklı bir model denemek için `OLLAMA_MODEL` ortam değişkeni kullanılabilir. Ollama servisi açıkken, gerçek GİB kanıtı üzerinden kaynaklı ve yapılandırılmış çıktı testi için:

```powershell
python scripts/run_local_llm_smoke_test.py
```

Farklı bir yüklü model seçmek için `OLLAMA_MODEL` ortam değişkeni kullanılabilir.

## Hızlı API modu ve yerel fallback

Sunumda daha kısa ilk-yanıt süresi istenirse `GEMINI_API_KEY` tanımlandığında uygulama düşük gecikmeli `gemini-3.5-flash-lite` modelini birincil açıklama üreticisi olarak kullanır. `GROQ_API_KEY` tanımlıysa GPT-OSS 120B ikinci uzak üretim katmanıdır. Tüm uzak API'ler başarısız olursa uygulama yerel modeli beklemez; doğrulanmış GİB atıflarıyla anında güvenli kaynak özeti gösterir. Anahtar tanımlı değilse uygulama tamamen yerel `gemma3:4b` modunda çalışır. API'ye XML, dosya adı, fatura taraf/tutar bilgileri, SHA-256 özeti veya yerel dosya yolu gönderilmez; yalnızca doğrulama kuralı ve yerelde seçilmiş resmî GİB kanıt parçaları gönderilir.

```powershell
$env:GEMINI_API_KEY = "AI-Studio-anahtarınız"
$env:GEMINI_MODEL = "gemini-3.5-flash-lite"
uvicorn faturaguard.main:app --reload
```

Anahtarı `.env`, kaynak kodu veya Git'e kaydetmeyin. Anahtar tanımlı değilse ek kurulum gerekmeden yerel mod devam eder. API performansı, sunum öncesi `scripts/benchmark_local_models.py` ile aynı dört vaka üzerinden ayrıca ölçülmelidir.

Anahtarın, seçilen modelin ve yapılandırılmış çıktı sözleşmesinin canlı kontrolü için sunucuyu başlatmadan önce şu smoke testi çalıştırılabilir; anahtarı ekrana yazdırmaz:

```cmd
python scripts\run_gemini_smoke_test.py
```

Uygulama açılırken RAG/embedding modeli ve küçük bir semantic retrieval sorgusu otomatik ısıtılır. Böylece bu maliyet ilk “Resmî GİB kaynağıyla açıkla” tıklamasında değil, `Application startup complete` mesajından önce ödenir. Başlangıç logunda `RAG başlangıç ısıtması tamamlandı.` görülmesi hattın hazır olduğunu gösterir.

Yerel model karşılaştırmasında `LLM_PROVIDER=local` ile başlatıldığında aynı başlangıç ısıtması Ollama modeline de bir tokenlık kısa çağrı yapar. Bu sayede Gemma ölçümü, model ağırlıklarının ilk yüklenmesini değil sıcak durumdaki gerçek açıklama süresini gösterir.

## Deneysel sağlayıcı: Cohere Command A+

Command A+ entegrasyonu, şemalı çıktı ve atıf doğrulaması için deneysel olarak bulunur. Gerçek hesap/imza vakalarında ilgisiz öneri ve gereksiz tekrar görüldüğü için `LLM_PROVIDER=auto` zincirinde kullanılmaz. Yalnızca kalite karşılaştırması için `LLM_PROVIDER=cohere` ile seçilmelidir.

```cmd
set "COHERE_API_KEY=Cohere-anahtarınız"
set "COHERE_MODEL=command-a-plus-05-2026"
python scripts\run_cohere_smoke_test.py
```

Anahtarı kaynak koduna, `.env` dışındaki izlenen bir dosyaya veya Git'e yazmayın.

## İkinci uzak API yedeği: Groq

`GROQ_API_KEY` tanımlıysa `LLM_PROVIDER=auto` akışında Gemini başarısız olduğunda Groq denenir. İki API de başarısız olursa uygulama anında resmî GİB kaynak özeti gösterir. Yerel Gemma bu otomatik yedek zincirinde kullanılmaz. Varsayılan Groq modeli `openai/gpt-oss-120b`'dir ve strict JSON Schema kullanır. Çıktı uygulama tarafında Pydantic şeması ve GİB atıflarıyla doğrulanır.

```cmd
set "GROQ_API_KEY=Groq-anahtarınız"
set "GROQ_MODEL=openai/gpt-oss-120b"
python scripts\run_groq_smoke_test.py
```

Anahtarı kaynak koduna, `.env` dışındaki izlenen bir dosyaya veya Git'e yazmayın.

## RAG kalite değerlendirmesi

RAG kalitesi yalnızca örnek bir sorguyla değil, beklenen resmî kaynak ve sayfa bilgisi tanımlanmış küçük bir golden sorgu setiyle de ölçülür. Aşağıdaki komut semantic, BM25 lexical ve hibrit retrieve→rerank akışlarını karşılaştırır:

```powershell
python scripts/evaluate_rag.py
```

Sonuç `data/evaluation/retrieval_metrics.json` dosyasına yazılır. Altı sorguluk güncel golden sette semantic arama `Recall@3 = 0.67`, `MRR@3 = 0.44`; BM25 ve hibrit rerank ise `Recall@3 = 0.83`, `MRR@3 = 0.72` elde etti. Tüm stratejilerde resmî GİB atıf kapsaması `1.00` olarak korundu. Sonuçlar başarı iddiası değil, sonraki ağırlık/model iyileştirmeleri için ölçüm tabanıdır.

## Yerel LLM model benchmark'ı

Yerel modelleri aynı dört gerçek bulgu senaryosunda hız, şemaya uygun LLM çıktısı, deterministik fallback oranı ve kaynaklı yanıt oranıyla karşılaştırmak için:

```cmd
python scripts\benchmark_local_models.py
```

Varsayılan karşılaştırma `qwen2.5:3b-instruct`, `qwen3:4b-instruct` ve `gemma3:4b` modelleridir. Son ölçümde sırasıyla ortalama 20,95 sn / %0 LLM başarı, 51,16 sn / %50 LLM başarı ve 43,42 sn / %100 LLM başarı elde edildi. Bu nedenle varsayılan `gemma3:4b` seçilmiştir. Sonuç `data/evaluation/local_model_benchmark.json` dosyasına yazılır. Tek model denemek için `--model qwen3:4b-instruct` kullanılabilir.

## İsteğe bağlı n8n otomasyonu

`n8n/faturaguard-webhook-workflow.json` dosyasını n8n'e içe aktarın. Ardından n8n webhook adresini `N8N_WEBHOOK_URL` ortam değişkenine yazın. FaturaGuard yalnızca işlem kimliği, dosya adı, hash, karar durumu ve doğrulama özetini gönderir; XML içeriğini göndermez.

## Temel ilke

Orijinal XML değiştirilemez. Her düzeltme kullanıcı onayıyla çalışma kopyasına uygulanır ve belge yeniden doğrulanır.

İş özeti ve denetim olayları yerel `data/faturaguard.sqlite3` veritabanında tutulur. Tam XML diff'i veritabanına yazılmaz; yalnızca ilgili işlem klasöründe saklanır.

Ana sayfadaki **İşlem geçmişi** bağlantısı, son 20 işlemi XML içeriğini göstermeden listeler. Her kaydın denetim izi, HTML ve JSON raporunda görüntülenebilir.

## Tek komutla uçtan uca demo

Doğrulama → teklif → isteğe bağlı onay → çalışma kopyası → yeniden doğrulama → rapor akışını gerçek bir XML üzerinde çalıştırmak için:

```cmd
python scripts\run_demo_e2e.py C:\Users\Muhammed\Desktop\efatura_kutuphane_testi\test_hesap_hata.xml --approve-first-proposal
```

Ayrıntılı demo ve web arayüzü sunum akışı için [DEMO_SCENARIO.md](DEMO_SCENARIO.md) dosyasına bakın.

## Proje belgeleri

| Belge | Amaç |
|---|---|
| `SRS.md` | V1 kapsamı, gereksinimler ve kabul kriterleri |
| `Architecture_and_AI_Safety.md` | Mimari kararlar, agent sınırları ve yapay zekâ güvenlik kuralları |
| `Project_Plan.md` | İş paketleri, kilometre taşları, riskler ve teslim yaklaşımı |
| `Development_Lifecycle_and_Quality.md` | Geliştirme yaşam döngüsü, Git/CI/test ve tamamlanma ölçütleri |
| `Test_and_Delivery_Report.md` | Test kanıtları, bilinen sınırlılıklar ve final teslim kontrolü |
| `resources/gib/README.md` | Yalnızca resmî GİB kaynaklarından oluşan RAG kaynak envanteri |
| `resources/evaluation/golden_queries.json` | RAG retrieval değerlendirmesinde kullanılan beklentili sorgu seti |

Bu belgeler kısa tutulur ve proje ilerledikçe güncellenir; amaç bürokrasi değil, kararların ve kalite kanıtlarının izlenebilir olmasıdır.
