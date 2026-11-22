# Güvenlik kapsamı ve teslim taraması

Bu uygulama yerel eğitim/gözetimli demo prototipidir. Ana site için çok
kullanıcılı kimlik/yetki yönetimi yoktur. İnternete açık üretim servisi olarak
kurulması desteklenmez. Sır içeren bir sorunu public issue veya ekran görüntüsüyle
paylaşmayın; anahtarı iptal edip sağlayıcı hesabında yenileyin.

## Sırlar ve veri

API anahtarları kullanıcı ortamından, otomasyon tokenı yerel ve Git dışında
üretilen ayardan gelir. `.env.example` yalnızca boş alanlar içerir. İşlem
verileri, XML'ler, SQLite, model ve ham doküman cache'i Git dışındadır.
Kaynak kod ve Git geçmişinde tanınan Gemini/Groq/GitHub/özel anahtar imzaları
`python scripts/check_submission.py --history` ile aranır. Bu bir desen taramasıdır,
bütün sır türlerini veya resim içindeki metni otomatik kanıtlayan bir araç değildir.

## 22.11.2026 bağımlılık taraması

Test edilmiş Windows bağımlılık listesi ayrı bir pip-audit 2.10.1 ortamıyla
PyPI advisory servisine karşı tarandı. Ham rapor yerelde
`data/evaluation/dependency_audit.json` altında üretilir; bu sonuç zamana bağlıdır.

- `pytest 8.4.2` için `PYSEC-2026-1845` / `GHSA-6w46-j5rx-g56g` bulundu.
  Kilit ve dev bağımlılığı **9.0.3 veya üzeri** olacak şekilde düzeltildi;
  test ortamları 9.0.3'e yükseltildi. [GitHub danışma kaydı](https://github.com/advisories/GHSA-6w46-j5rx-g56g).
- Son taramada `pytest` bildirimi kalktı. **ChromaDB 1.5.9 için dört ayrı
  danışma kaydı kaldı** (veritabanı çıktısında 5 satır; bir kimlik tekrarlanıyor).
  Taramada düzeltilmiş sürüm listelenmedi; bu bildirimler gizlenmedi/ignore edilmedi.

| PYSEC | CVE | Bildirilen yüzey |
|---|---|---|
| PYSEC-2026-311 | CVE-2026-45829 | Chroma sunucusunda güvenilmeyen model ve trust_remote_code=true ile kod çalıştırma |
| PYSEC-2026-3813 | CVE-2026-45830 | Chroma sunucusunda tenant erişim denetimi |
| PYSEC-2026-3815 | CVE-2026-45831 | Chroma SimpleRBAC kapsam denetimi |
| PYSEC-2026-3814 | CVE-2026-45833 | Chroma sunucusunda koleksiyon güncelleme/model kodu |

Projede Chroma **yalnızca yerel PersistentClient** olarak açılır; Chroma HTTP
sunucusu, HttpClient veya `/api/v2/tenants` uçları sunulmaz. Kullanıcıdan model
deposu/remote-code ayarı alınmaz. Embedding revizyonu sabittir ve
`trust_remote_code=False` açıkça verilir; bu sınır test edilir.
Bu nedenle bildirilen sunucu saldırı yüzeyi mevcut yerel akışta açılmıyor.
Bu değerlendirme paket açığının yamalandığı veya her kullanımın güvenli olduğu
iddiası değildir. Chroma'yı sunucu olarak açmak, uzaktan tenant veya model
yönetimi eklemek bu teslim kapsamının dışındadır ve yeni güvenlik incelemesi ister.

Kaynak: [Chroma deposundaki bildirim ve dört advisory bağlantısı](https://github.com/chroma-core/chroma/issues/7909).
Yerel prototip bu sınırlama ve belgelenmiş artık bağımlılık riskiyle teslim edilir;
**sıfır bilinen açık / üretime hazır** sonucu verilmez.

## Diğer sınırlar

Ham XML gönderilmez; sohbetin gerekli maskeli bağlamı API'ye gidebilir ve
maskeleme eksik kalabilir. LLM atıf kontrolü anlamsal doğruluğun tamamını
kanıtlamaz. Düzeltme için insan onayı, izinli dört aritmetik alan ve ayrı kopya
zorunludur. SMTP gönderimi sonrası kayıt öncesi çökmede yinelenme mümkündür.
n8n callback tokenlıdır; bu, ana site için kullanıcı yetkilendirmesi yerine geçmez.
