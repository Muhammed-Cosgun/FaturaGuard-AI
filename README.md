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

Varsayılan yerel açıklama modeli, CPU üzerinde daha akıcı demo için `qwen2.5:3b-instruct`'tür. Daha kapsamlı ama yavaş yanıt için `OLLAMA_MODEL=qwen2.5:7b` seçilebilir. Ollama servisi açıkken, gerçek GİB kanıtı üzerinden kaynaklı ve yapılandırılmış çıktı testi için:

```powershell
python scripts/run_local_llm_smoke_test.py
```

Farklı bir yüklü model seçmek için `OLLAMA_MODEL` ortam değişkeni kullanılabilir.

## RAG kalite değerlendirmesi

RAG kalitesi yalnızca örnek bir sorguyla değil, beklenen resmî kaynak ve sayfa bilgisi tanımlanmış küçük bir golden sorgu setiyle de ölçülür. Aşağıdaki komut semantic, BM25 lexical ve hibrit retrieve→rerank akışlarını karşılaştırır:

```powershell
python scripts/evaluate_rag.py
```

Sonuç `data/evaluation/retrieval_metrics.json` dosyasına yazılır. İlk baz ölçümde üç sorguda bütün stratejiler `Recall@3 = 0.67`, `MRR@3 = 0.67` ve resmî GİB atıf kapsaması `1.00` elde etti. Eşit sonuç bir başarı iddiası olarak değil, golden veri setinin genişletilmesi ve ağırlıkların sonraki iterasyonda ayarlanması gereken bir kalite bulgusu olarak izlenir.

## İsteğe bağlı n8n otomasyonu

`n8n/faturaguard-webhook-workflow.json` dosyasını n8n'e içe aktarın. Ardından n8n webhook adresini `N8N_WEBHOOK_URL` ortam değişkenine yazın. FaturaGuard yalnızca işlem kimliği, dosya adı, hash, karar durumu ve doğrulama özetini gönderir; XML içeriğini göndermez.

## Temel ilke

Orijinal XML değiştirilemez. Her düzeltme kullanıcı onayıyla çalışma kopyasına uygulanır ve belge yeniden doğrulanır.

İş özeti ve denetim olayları yerel `data/faturaguard.sqlite3` veritabanında tutulur. Tam XML diff'i veritabanına yazılmaz; yalnızca ilgili işlem klasöründe saklanır.

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
