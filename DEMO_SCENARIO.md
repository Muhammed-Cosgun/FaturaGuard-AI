# FaturaGuard AI — Uçtan Uca Demo Senaryosu

Bu senaryo; doğrulama, insan onayı, sınırlı düzeltme, yeniden doğrulama, orijinalin korunması ve rapor üretimini tek akışta gösterir.

## Ön koşul

- `.venv-runtime` etkin olmalı.
- `efatura-kontrol` ve proje bağımlılıkları kurulu olmalı.
- Daha önce oluşturulan GİB RAG indeksi korunmalı; AI açıklaması gösterilecekse Ollama servisi açık olmalı.

## Ana senaryo: aritmetik tutarsızlık

Kullanıcının mevcut test dosyasını kullanın:

```cmd
python scripts\run_demo_e2e.py C:\Users\Muhammed\Desktop\efatura_kutuphane_testi\test_hesap_hata.xml
```

Beklenen davranış:

1. Dosya doğrulanır ve `hesap-dip-satir` aritmetik bulgusu görülür.
2. Bir düzeltme teklifi üretilir fakat onay verilmediği için hiçbir XML değiştirilmez.
3. Komut sonunda giriş dosyasının SHA-256 özeti ilk değerle karşılaştırılır.
4. XML içeriğini taşımayan işlem raporu `data/reports/` altında üretilir.

Kullanıcının onayını temsil eden ikinci adım:

```cmd
python scripts\run_demo_e2e.py C:\Users\Muhammed\Desktop\efatura_kutuphane_testi\test_hesap_hata.xml --approve-first-proposal
```

Beklenen davranış:

1. Yalnızca allowlist'teki `recalculate-line-extension-total` kuralı uygulanır.
2. Düzeltilmiş XML, `data/working/` altında yeni bir çalışma kopyası olur.
3. Orijinal test dosyası korunur.
4. Çalışma kopyası yeniden doğrulanır; işlem raporu, hash'ler ve diff saklanır.

> `--approve-first-proposal` yalnızca komut satırı demosunda kullanıcının onay düğmesine basmasını temsil eder. Web arayüzünde aynı işlem açık bir Kabul/Red kararıyla yapılır.

## Web arayüzü senaryosu

```cmd
uvicorn faturaguard.main:app --reload
```

1. `http://127.0.0.1:8000` adresini açın ve aynı XML'i yükleyin.
2. Aritmetik bulguda **GİB kaynağıyla açıkla** düğmesine basın; kaynak, resmî URL ve sayfayı inceleyin.
3. Düzeltme kartındaki önce/sonra değerini kontrol edin.
4. **Kabul et** ile çalışma kopyasının oluşturulduğunu, diff'i ve yeniden doğrulama özetini gösterin.
5. İşlem raporunu HTML ve JSON olarak açın.

## Negatif senaryo

`test_bozuk_xml.xml` ile yükleme yapın. XML iyi biçimli olmadığından güvenli düzeltme teklifi üretilmemeli; sistem yalnızca doğrulama bulgusunu göstermelidir.
