# FaturaGuard AI — Yazılım Gereksinimleri

## Amaç

Kullanıcının e-Fatura XML belgesini yüklemesini, doğrulama sonuçlarını öncelikli şekilde incelemesini ve yalnızca güvenli önerileri onaylayarak düzeltilmiş bir kopya üretmesini sağlamak.

## V1 kapsamı

- XML yükleme ve orijinali koruma
- XSD, Schematron ve aritmetik denetimler
- Yapılandırılmış hata bulguları ve önceliklendirme
- Yalnızca resmî GİB kaynaklarını kullanan hibrit RAG açıklamaları: chunking, embedding, Chroma, semantic retrieval, lexical retrieval ve rerank
- Tek bir sınırlandırılmış agent'ın çok adımlı LangGraph iş akışı ve izinli araçları
- Kullanıcı onayı/reddiyle sınırlı düzeltme
- Yeniden doğrulama, XML diff ve raporlama
- İsteğe bağlı n8n webhook'u ile tamamlanan işlem raporunun otomasyon akışına aktarılması

## Kapsam dışı

- E-imza/mali mühür atma
- GİB sistemine belge gönderme
- Taraf, vergi numarası, fatura numarası, tarih veya ticari anlamı değiştiren alanların otomatik değişimi

## Kabul kriterleri

1. Orijinal XML hiçbir akışta değiştirilmez.
2. Onay olmadan hiçbir düzeltme uygulanmaz.
3. Uygulanan her düzeltme öncesi/sonrası diff ile gösterilir.
4. Düzeltme sonrası belge yeniden doğrulanır.
5. RAG ile verilen açıklamalar kaynak bilgisi taşır.
6. RAG yanıtı, resmî GİB kaynağı bulunmadığında kesin bir teknik veya hukukî yönlendirme üretmez.
7. Her RAG cevabı kaynak başlığı, resmî URL ve sayfa numarası içerir.
8. Agent, yalnızca izin verilen araçları kullanır; onay bekleyen düzeltme akışından kendisi çıkamaz.
