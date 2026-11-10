# FaturaGuard AI — Geliştirme Yaşam Döngüsü ve Kalite Süreci

## 1. Neden bu süreç var?

Amaç ağır bir kurumsal süreç kurmak değildir. Bu süreç, tek geliştiricinin kararlarını takip edebilmesini, hataları erken yakalamasını ve sunumda projenin kontrollü geliştirildiğini kanıtlamasını sağlar.

## 2. Yaşam döngüsü

```text
Gereksinim → Tasarım → Küçük geliştirme → Otomatik test → Manuel akış testi
     → Belge güncellemesi → Git kaydı → Kilometre taşı değerlendirmesi
```

1. `SRS.md` içinden küçük bir kabul kriteri seçilir.
2. Mimari ve güvenlik etkisi kontrol edilir.
3. Tek amaçlı geliştirme dalında kodlanır.
4. Birim ve entegrasyon testleri çalıştırılır.
5. İlgili web akışı manuel olarak doğrulanır.
6. Gerekliyse belge/test raporu güncellenir ve değişiklik Git'e kaydedilir.

## 3. Git çalışma düzeni

- `main`: her zaman çalışır ve demo yapılabilir sürüm.
- `feature/<kisa-ad>`: tek özellik veya tek düzeltme için kısa ömürlü dal.
- Anlamlı, küçük commit'ler kullanılır: `feat:`, `fix:`, `test:`, `docs:`.
- `main` dalına alınmadan önce testler çalıştırılır.
- Proje tek kişilik olsa da her özellik için kısa öz-denetim yapılır: kapsam, test, güvenlik etkisi ve belge güncellemesi.

## 4. Kalite kapıları

| Aşama | Zorunlu kontrol |
|---|---|
| Kod yazımı | Biçimlendirme, statik analiz ve birim test |
| Entegrasyon | Doğrulama kütüphanesi ve FastAPI uç testleri |
| Güvenli düzeltme | Onay yoksa değişiklik yapılmadığının testi |
| Yayına hazır sürüm | Uçtan uca demo, diff, yeniden doğrulama ve orijinal hash testi |

## 5. Test katmanları

- **Birim testleri:** öncelik puanı, izinli düzeltme kuralları, dosya/hash davranışı.
- **Entegrasyon testleri:** `efatura-kontrol` adaptörü, RAG kaynak çıktısı ve API uçları.
- **Uçtan uca test:** XML yükleme → doğrulama → öneri → onay → düzeltme → yeniden doğrulama → rapor.
- **Negatif testler:** bozuk XML, geçersiz dosya, büyük dosya, kaynaksız RAG, onaysız işlem.

## 6. Her iş paketi için tamamlanma tanımı

Bir iş paketi aşağıdakilerin tümü sağlanmadan tamamlanmış sayılmaz:

- Kabul kriteri karşılanır.
- İlgili otomatik test eklenir veya güncellenir.
- Hata durumunda anlaşılır kullanıcı mesajı vardır.
- Orijinal XML'i koruma ve onay kuralı etkileniyorsa bu kurallar ayrıca doğrulanır.
- İlgili belge ve teslim raporu güncellenir.

## 7. CI'da çalışacak asgari kontroller

- Bağımlılık kurulumu
- Kod biçimlendirme/lint kontrolü
- Test paketi
- Test raporu üretimi

## 8. Sunum öncesi kalite kontrolü

1. Temiz ortamda kurulum talimatı denenir.
2. Geçerli, bozuk ve aritmetik hatalı örneklerle demo tekrarlanır.
3. Onaysız değişikliğin engellendiği gösterilir.
4. Orijinal XML, diff, yeniden doğrulama ve rapor çıktısı kontrol edilir.
5. Bilinen sınırlılıklar dürüstçe `Test_and_Delivery_Report.md` dosyasına eklenir.
