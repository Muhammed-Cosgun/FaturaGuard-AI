# FaturaGuard AI çalışma kuralları

Bu depo yerel bootcamp prototipidir. Gereksinimler SRS.md, mimari
Architecture_and_AI_Safety.md, güncel kurulum README.md içinde. Teslim
kapısı TESLIM_KONTROLU.md, sunum SUNUM_HAZIRLIK.md ve sunum/ altında.

## Temel sınırlar

- Orijinal XML'i değiştirme. İzinli aritmetik düzeltme, kullanıcı onayı, ayrı
  kopya, diff ve yeniden doğrulama sınırlarını koru.
- Sohbet salt okunurdur; ham XML'i uzak servise gönderme. Sırları okuma/yazdırma.
- Anahtarları, local.env, SQLite iş verilerini ve model cache'ini Git'e ekleme.
- Kullanıcı ücret istemiyor. Ücretli plan/servis açma; testlerde canlı LLM
  çağrısı varsayma. Sağlayıcı ücretsiz kotasını yazılım garanti etmez.
- n8n akışı LLM kullanmaz. Dış alıcı yerine yerel Mailpit kullanılır.
- Paket sürümü efatura-kontrol==0.1.0, Windows 3.14 kilidi referans kurulumdur.
- Saxon native nesnelerini yaşam döngüsü sonunda ilgili iş parçacığında kapat.
- Çalışma verilerini temizleme/silme. Temiz-klon testlerini ayrı dizinde yap.

## Kontroller

```bash
python -m pytest -p no:cacheprovider -o addopts="" -q --basetemp=.pytest-work-check
python -m ruff check .
python -m pip check
python scripts/check_submission.py --history
python scripts/run_document_chat_quality_evaluation.py
```

Teslim denetiminde pytest 9.0.3 güvenlik güncellemesi ve temiz-klon hazırlığı
eklendi. Chroma advisory sonucu temiz diye sunulmaz; SECURITY.md okunmalı.

Bu testler canlı API gerektirmez. Canlı smoke/benchmark betikleri ayrı
çalıştırılır; geçmiş kanıtı yeni canlı test diye raporlama. Dokümantasyon
bağlantılarını ve sunum görsellerinin kökenini koru. MCP veya tüm GİB hata
senaryolarının kapsandığını iddia etme. CI, üretim güvenliği onayı değildir.
