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
9. Düzeltme sonrası üst sayaçlar ve işlem geçmişi yeniden doğrulama sonucunu
   gösterir. İlk bulgular/agent planı geçmiş kayıt olarak açıkça ayrılır;
   ilk raporun verileri değiştirilmez.

## Belgeye bağlı sohbet asistanı — ek kapsam

- Bütün bulgu kodları için aynı kayıt temelli açıklama sözleşmesi uygulanır:
  tespit edilen durum, XML konumu, yerel kural, izinli teklif/bağımlılık durumu
  ve sonraki inceleme adımı. Kaynaklı LLM yorumu bu gerçeklerden ayrı gösterilir.
- Düzeltme karşılaştırması tüm izinli kurallarda alan/değerleri ve bulgu adet
  farklarını açıklar; kısmen giderilen veya yeni oluşan bulguları saklamaz.
  Nedensellik yalnızca kayıtlı kural bağımlılığı ve doğrulama sonucuyla desteklenir.

- Sonuç ve rapor ekranında Fatura İnceleme Asistanı bulunur. Güncel bulguları
  özetler; teklifin durumunu, önce/sonra sonuçlarını ve kullanım adımlarını açıklar.
- Kullanıcı doğal dilde soru yazabilir veya hazır sorulardan/bulgu listesinden
  seçim yapabilir. Soruyu ve son 6 turdaki takip bağlamını model yorumlar;
  şemalı araç seçimi → salt okunur araçlar → model yanıtı LangGraph ile yürütülür.
- Soru/geçmiş ve gerekli bulgu ayrıntılarının maskelenmiş hâli Gemini/Groq'a
  gönderilir. Ham XML ve dosya kimliği gönderilmez. Teklif değerleri yalnızca
  yerelde açılan tokenlarla taşınır; maskelemenin sınırı arayüzde açıklanır.
- İzinli araçlar yalnızca aynı işin güncel bulguları, teklifleri, karşılaştırması
  ve güvenilir sorgu/kanıt eşiği kullanan GİB kaynak aramasıdır. En fazla dört
  araç çağrısı seçilebilir; serbest yol/iş kimliği/URL veya yazma aracı yoktur.
- Model veya geçerli şema/atıf hazır değilse açıkça etiketlenen yerel yedek
  yanıt verilir; modelin kullanıldığı izlenimi yaratılmaz.
- Şeması geçerli ancak yanıt kontrolünden geçemeyen model cevabı, aynı maskeli
  araç verisi ve sabit red koduyla en fazla bir kez yeniden üretilir; tanımlıysa
  Groq onarımda öncelenir. Reddedilen metin onarım isteğine eklenmez.
- Sayı/PII maskeleri kullanıcı yanıtında bırakılamaz. Teklif tutarları ve
  karşılaştırma adetleri yalnızca doğrulanmış yerel tokenlarla açılır; bilinmeyen
  token reddedilir. Yeni onay önerisi güncel onaylanabilir teklif durumuna bağlıdır.
- Sohbet XML değişikliği, teklif onayı/reddi, imza, silme veya gönderim yapamaz.
  Bu sohbet sınırı uygulamanın sonuç ekranındaki kullanıcı onayını kaldırmaz;
  asistan uygulamada düzeltme onayı bulunmadığını söylememelidir.
- Son 20 soru-cevap ilgili işin yerel SQLite kaydında tutulur; JSON işlem raporuna
  eklenmez. Audit yalnızca mod/bulgu/atıf sayısı, sağlayıcı denemeleri, araç
  adları ve maskeli konuşma gönderim denemesi bilgisini içerir; metinleri içermez.
  Yanıt kontrolünün sabit red kodu ve onarım denemesi de metadata olarak tutulur;
  başarısız sağlayıcı yanıtı veya reddedilen model metni saklanmaz.
- Yanıt beklerken sonuç ekranı kullanılabilir; hata ve bekleme durumu gösterilir.
  JavaScript kapalıysa normal HTML form yanıtı çalışır.
