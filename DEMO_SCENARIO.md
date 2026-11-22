# Tekrar edilebilir demo

## Hazırlık

Temiz kurulum ve kaynak/model hazırlığı README.md içindedir. Test belgeleri:

```bash
python scripts/prepare_demo.py --fixtures-only
```

`data/demo-fixtures/` altında vergi hariç, vergi dahil ve ödenecek toplam
hataları oluşturulur. Bu komut LLM çağırmaz ve kaynak fatura değişmez.
Tam AI demo için resmî kaynaklar, embedding/Chroma ve kendi ücretsiz sağlayıcı
ayarlarınız gerekir. Anahtarları kayda veya sunuma koymayın.

## Web kabulü

1. Siteyi 8011 portunda açın.
2. demo_tax_exclusive_error.xml yükleyin: 0 hata / 2 uyarı / 1 bilgi.
3. Kaynaklı plan hazırsa 15.00 yerine 15.15 teklifini inceleyip açıkça onaylayın.
4. Yeni sonuç 0 hata / 0 uyarı / 1 bilgi olmalı. Diff tek alanı göstermeli.
5. Önce/sonra sohbetini ve sağlayıcı/dayanakları inceleyin.
6. n8n hazırlanmışsa yeni işlem mesajını Mailpit'te işlem kimliğiyle eşleştirin.

Reddetme yeni düzeltme veya bildirim olayı oluşturmamalı. İmza bilgisi kalabilir;
uygulama imza atmaz veya GİB'e göndermez. Ayrıntılı konuşma ve yedek demo
[SUNUM_HAZIRLIK.md](SUNUM_HAZIRLIK.md) içinde.

## Yerel CLI aritmetik demosu

```bash
python scripts/run_demo_e2e.py data/demo-fixtures/demo_tax_exclusive_error.xml
```

`--approve-first-proposal` yalnızca bu CLI demosunda açık kullanıcı onayı
anlamına gelir. Web uygulamasının kaynaklı plan/onay kapısının testi değildir.
Gerçek XML ve kişisel veriler yerine repodaki örnekleri kullanın.
