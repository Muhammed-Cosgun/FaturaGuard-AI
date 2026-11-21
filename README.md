# FaturaGuard AI

FaturaGuard AI, e-Fatura XML belgelerini doğrulayan, resmî GİB kaynaklarıyla hataları açıklayan ve kullanıcı onayıyla sınırlı düzeltmeler uygulayan bir web uygulamasıdır.

## Durum

V1 geliştirme ve temel kabul testleri tamamlandı. Uygulama, yerel demo ve eğitim projesi amacıyla hazırlanmıştır; GİB'e gerçek belge gönderimi veya e-imza üretimi yapmaz.

21.11.2026 format sonrası kurtarma tamamlandı: bağımsız Windows/Python 3.14 ortamı,
139 otomatik test, Gemini/Groq canlı smoke testleri ve üç web kabul senaryosu
normal süreç çıkışıyla doğrulandı. Eski veri yolları ve 69 commit'lik Git geçmişi
geri alındı. Devam kaydı: [PROJE_BAGLAMI.md](PROJE_BAGLAMI.md).

## Hedef teknoloji

- FastAPI
- Jinja2, HTML/CSS ve normal form POST akışı; düğme bekleme metni için küçük JavaScript
- `efatura-kontrol` doğrulama kütüphanesi

## Başlangıç

Bu bilgisayardaki hazır kurulumda proje kökünden `BASLAT.cmd` çalıştırın;
adres `http://127.0.0.1:8011` olur. Geliştirme sırasında:

```cmd
.venv-clean\Scripts\python.exe -m uvicorn faturaguard.main:app --host 127.0.0.1 --port 8011 --reload
```

`KUR.cmd`, Windows/Python 3.14 için test edilmiş paketleri
`requirements-windows-py314.lock.txt` üzerinden kurar. GİB kaynakları, Chroma
indeksi ve embedding önbelleği `resources/gib/raw` ve `data` yedeğinden gelir;
yalnızca Git klonu bu büyük varlıkları içermez. Kullanıcı ortam değişkenleri
tanımlandıktan sonra yeni terminalden başlatın; uygulama `.env` otomatik okumaz.

Başka bir ortam için genel kurulum:

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

`build_chroma_index.py` yalnızca `data/models/` yerel önbelleğini kullanır;
model eksikse otomatik indirme yapmaz. Aktif embedding modeli
`intfloat/multilingual-e5-small`'dır. Mevcut yedekte model ve 330 chunk'lık indeks hazırdır.

## Yerel LLM smoke testi

Varsayılan yerel açıklama modeli `gemma3:4b`'tür. Dört gerçek bulgu vakasında geçerli yapılandırılmış LLM çıktısı oranı %100, ortalama yanıt süresi 43,42 saniye ölçüldü. Farklı bir model denemek için `OLLAMA_MODEL` ortam değişkeni kullanılabilir. Ollama servisi açıkken, gerçek GİB kanıtı üzerinden kaynaklı ve yapılandırılmış çıktı testi için:

```powershell
python scripts/run_local_llm_smoke_test.py
```

Farklı bir yüklü model seçmek için `OLLAMA_MODEL` ortam değişkeni kullanılabilir.

## Hızlı API modu ve güvenli fallback

Sunumda daha kısa ilk-yanıt süresi istenirse `GEMINI_API_KEY` tanımlandığında uygulama düşük gecikmeli `gemini-3.5-flash-lite` modelini birincil açıklama üreticisi olarak kullanır. `GROQ_API_KEY` tanımlıysa GPT-OSS 120B ikinci uzak üretim katmanıdır. Tüm uzak API'ler başarısız olursa uygulama yerel modeli beklemez; doğrulanmış GİB atıflarıyla anında güvenli kaynak özeti gösterir. Anahtar tanımlı değilse uygulama tamamen yerel `gemma3:4b` modunda çalışır. API'ye XML, dosya adı, fatura taraf/tutar bilgileri, SHA-256 özeti veya yerel dosya yolu gönderilmez; yalnızca doğrulama kuralı ve yerelde seçilmiş resmî GİB kanıt parçaları gönderilir.

```powershell
$env:GEMINI_API_KEY = "AI-Studio-anahtarınız"
$env:GEMINI_MODEL = "gemini-3.5-flash-lite"
uvicorn faturaguard.main:app --reload
```

Anahtarı kaynak koduna veya Git'e kaydetmeyin. Anahtar yoksa yerel açıklama için
Ollama ve `gemma3:4b` kurulmuş olmalıdır. Yerel açıklama modu, LLM düzeltme planı
üretmez: Gemini/Groq olmadan web düzeltmesi insan incelemesinde durur.
API performansı `scripts/benchmark_api_providers.py` ile ölçülür.

Anahtarın, seçilen modelin ve yapılandırılmış çıktı sözleşmesinin canlı kontrolü için sunucuyu başlatmadan önce şu smoke testi çalıştırılabilir; anahtarı ekrana yazdırmaz:

```cmd
python scripts\run_gemini_smoke_test.py
```

Maskeli düzeltme-planı zincirinin ayrıca doğrulanması için:

```cmd
python scripts\run_correction_plan_smoke_test.py
```

Bu komut yalnızca `decision`, sağlayıcı modu, atıf sayısı ve güvenli sağlayıcı
izini gösterir. Correction-plan çağrılarında varsayılan süre bütçesi 12 saniyedir;
Gemini zaman aşımına uğrarsa Groq aynı güvenlik sözleşmesiyle devralır. Gerekirse
`CORRECTION_PLAN_TIMEOUT_SECONDS` ile değiştirilebilir.

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

Sonuç `data/evaluation/retrieval_metrics.json` dosyasına yazılır. Güncel 11 sorguda
semantic `Recall@3 = 0.82`, `MRR@3 = 0.76`; BM25 ve hibrit rerank
`Recall@3 = 0.91`, `MRR@3 = 0.71` elde etti. URL tabanlı kaynak kapsaması `1.00`.
Bu ölçümler kaynak bulmayı değerlendirir; LLM metninin tam doğruluğunu kanıtlamaz.
Rerank, ayrı bir model değil semantic/BM25/terim eşleşmesinin ağırlıklı puanıdır.

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

LLM düzeltme planı üretirken ham XML veya fatura kimlik bilgileri API'ye gönderilmez. Agent, yerelde hesaplanan izinli adayları maskeli alan/değer tokenlarıyla modele sunar; model yalnızca bir patch planı seçer. Plan, yereldeki gerçek adayla bire bir eşleşmezse kullanıcıya düzeltme onayı sunulmaz. Tüm uzak LLM istekleri ayrıca merkezi `PrivacyRedactor` katmanından geçer; VKN/TCKN, IBAN, e-posta, telefon, hesap numarası ve hassas alan adları maskelenir.

İzinli aritmetik düzeltme kataloğu yalnızca `LineExtensionAmount`, `TaxExclusiveAmount`, `TaxInclusiveAmount` ve `PayableAmount` dip toplamlarını kapsar. Agent alt toplam hatası varken ona bağımlı üst toplam için teklif üretmez; her adım kullanıcı onayı ve yeniden doğrulama ile ilerler.

Agent, birden fazla izinli teklif olduğunda ayrıca düzeltme bağımlılık sırasını ve her değişikliğin beklenen etkisini çıkarır. İnsan incelemesi için bağlama uygun soruları üretir; bu plan yalnızca ham XML içermeyen teklif meta verisini kullanır ve otomatik değişiklik yetkisi vermez.

İş özeti ve denetim olayları yerel `data/faturaguard.sqlite3` veritabanında tutulur. Tam XML diff'i veritabanına yazılmaz; yalnızca ilgili işlem klasöründe saklanır.

Ana sayfadaki **İşlem geçmişi** bağlantısı, son 20 işlemi XML içeriğini göstermeden listeler. Her kaydın denetim izi, HTML ve JSON raporunda görüntülenebilir.

## Tek komutla uçtan uca demo

Doğrulama → teklif → isteğe bağlı onay → çalışma kopyası → yeniden doğrulama → rapor akışını gerçek bir XML üzerinde çalıştırmak için:

```cmd
python scripts\run_demo_e2e.py data\demo-fixtures\demo_payable_error.xml --approve-first-proposal
```

Ayrıntılı demo ve web arayüzü sunum akışı için [DEMO_SCENARIO.md](DEMO_SCENARIO.md) dosyasına bakın.

Bu CLI demosu deterministik düzeltme çekirdeğini sınar. Gerçek LLM planı ve web
onay kapısını da içeren kabul için `python scripts\run_web_acceptance.py` çalıştırılır.

Genişletilmiş aritmetik düzeltme kuralları için tarayıcıda kullanılabilecek
doğrulanmış demo dosyalarını oluşturmak için:

```cmd
python scripts\generate_arithmetic_demo_fixtures.py
```

## Sunum öncesi kontrol

API anahtarlarını göstermeden RAG indeksini ve aktif sağlayıcı/fallback zincirini doğrulamak için:

```cmd
python scripts\run_demo_preflight.py
```

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
