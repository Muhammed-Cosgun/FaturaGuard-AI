# FaturaGuard AI — Resmî GİB Kaynakları

Bu klasör, RAG katmanında kullanılmasına izin verilen kaynakların envanteridir. FaturaGuard AI, bu envanterde yer almayan web sitelerini veya dokümanları teknik/hukukî dayanak olarak kullanmaz.

## Kaynak erişim noktası

Ana envanter sayfası: <https://ebelge.gib.gov.tr/efaturamevzuat.html>

GİB bu sayfada e-Fatura teknik mimarisi, kılavuzlar, UBL-TR 1.2.1 paketleri, test planı ve entegrasyon kılavuzlarını yayımlar.

## İndirilen kaynaklar

| Kaynak | Resmî GİB adresi | Yerel kopya | Erişim tarihi |
|---|---|---|---|
| UBL-TR 1.2.1 Paketi | <https://ebelge.gib.gov.tr/dosyalar/kilavuzlar/UBL-TR1.2.1_Paketi.zip> | `raw/UBL-TR1.2.1_Paketi.zip` | 2026-11-09 |
| UBL-TR 1.2.1 Kılavuzları | <https://ebelge.gib.gov.tr/dosyalar/kilavuzlar/UBLTR_1.2.1_Kilavuzlar.zip> | `raw/UBLTR_1.2.1_Kilavuzlar.zip` | 2026-11-09 |
| e-Fatura Uygulaması Test Planı v1.3 | <https://ebelge.gib.gov.tr/dosyalar/kilavuzlar/e-FaturaTestPlani.pdf> | `raw/e-FaturaTestPlani-v1.3.pdf` | 2026-11-09 |
| e-Fatura Uygulaması Entegrasyon Kılavuzu v1.10 | <https://ebelge.gib.gov.tr/dosyalar/kilavuzlar/e-FaturaUygulamasiEntegrasyonKilavuzu-v1.10.pdf> | `raw/e-FaturaUygulamasiEntegrasyonKilavuzu-v1.10.pdf` | 2026-11-09 |

Yerel ikili kopyalar Git'e eklenmez. Her dosyanın SHA-256 özeti `official_sources.json` içinde saklanır. RAG çıktısında, kullanılan kaynağın başlığı ve resmî GİB bağlantısı görünmelidir.

## İndeks oluşturma

`python scripts/build_gib_index.py` komutu yalnızca SHA-256 doğrulamasından geçen PDF kaynaklarından yerel arama indeksi üretir. ZIP paketleri bu ilk indeks aşamasına dahil edilmez; bunlar şema ve örnek belge varlıklarıdır.

`python scripts/build_chroma_index.py` komutu bu doğrulanmış chunks'ları çok dilli embedding'lere dönüştürür ve `data/chroma/` altında kalıcı Chroma koleksiyonuna yazar. Koleksiyonun semantic retrieval sonuçları, lexical BM25 sonuçlarıyla birleştirilip rerank edilir.
