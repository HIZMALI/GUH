# Katkı Kuralları

Teknik kapsam [proje spesifikasyonunda](MASTER_SPEC.md), veri dayanakları [kaynak analizinde](docs/source-analysis.md), arayüzler [API sözleşmesinde](docs/api-contract.md) tanımlıdır.

- Değişiklikler on-premise çalışma, salt okunur cihaz erişimi ve koruma bağımsızlığı sınırlarını korur.
- API ve veri şeması değişikliklerinde geriye uyumluluk ve kalıcı kayıtların korunması esastır.
- Sentetik veri, organizatör replay'i ve kaynak temelli donanım eşlemeleri açıkça ayrılır; saha doğruluğu veya sertifikasyon iddiası kanıt gerektirir.
- Register tanımlarında kaynak sayfa, adresleme, genişlik, ölçek ve signedness bulunur. Belirsiz word order yapılandırılabilir kalır.
- Sırlar, bağımlılıklar, runtime çıktıları ve yerel teslim paketleri Git'e eklenmez. `.env.example` yalnız boş yapılandırma şablonudur.
- Testler değişen davranışın anlamlı sınırlarını kapsar. Sonuçlar ortam, tarih ve kapsamıyla kaydedilir; çalıştırılmayan kontroller doğrulanmış sayılmaz.
- Doküman yolları ve örnek komutlar Windows/Linux kullanımıyla tutarlı tutulur. Orijinal kaynak hashleri ve teknik kanıtlar korunur.

Orijinal PDF/XLSX dosyaları harici referans girdileridir. Kaynak çıkarımı ve orijinal dosya hash kontrolü, bu girdilerin mevcut olduğu ayrı doğrulama alanında yürütülür.
