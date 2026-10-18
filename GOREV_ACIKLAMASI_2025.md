# Kara Muhafız ROS 2 Görevi — 2025 Parkuru

## Görev amacı

Bu görevde, verilen Kara Muhafız araç modeli ve 2025 parkur simülasyonu üzerinden çalışır, güvenli ve sürdürülebilir bir ROS 2 sistemi geliştirmeniz beklenmektedir.

Takım; manuel sürüşten tam otonom parkur görevine kadar gerekli bütün yazılım mimarisini kendisi tasarlamalı ve uygulamalıdır.

## Size verilenler

Takıma yalnızca aşağıdakiler verilecektir:

- Kara Muhafız araç modeli
- 2025 parkur world dosyası
- Aracın ve parkurun çalışması için gerekli mesh dosyaları

Hazır launch dosyası, controller ayarı, manuel kontrol düğümü, Nav2 yapılandırması, waypoint listesi, lokalizasyon çözümü veya otonomi kodu verilmeyecektir.

## Beklenen sonuç

Geliştirilecek sistem tek bir takım çözümü olarak:

1. Simülasyonu başlatabilmeli.
2. Aracı manuel olarak sürebilmeli.
3. Sensör verilerini ROS 2 üzerinden kullanabilmeli.
4. Aracın konumunu ve yönelimini tahmin edebilmeli.
5. Parkur üzerinde otonom hareket edebilmeli.
6. Engelleri algılayıp güvenli davranabilmeli.
7. Görevi tamamladığında güvenli şekilde durabilmeli.

## Manuel sürüş görevi

Araç, 2025 parkurunun tamamında manuel olarak sürülmelidir. Manuel sürüş sistemi:

- Araç hızını ve direksiyon komutlarını kontrol etmelidir.
- Komut kesildiğinde aracı güvenli biçimde durdurmalıdır.
- Acil duruş mekanizmasına sahip olmalıdır.
- Araç sınırlarını ve güvenli hız limitlerini aşmamalıdır.
- Manuel ve otonom modlar arasında güvenli geçiş yapmalıdır.

## Otonom sürüş görevi

Araç, operatörün görevi başlatmasından sonra 2025 parkurunu otonom olarak tamamlamalıdır.

Otonom sistemin:

- Başlangıç durumunu ele alması,
- Parkur üzerindeki görev noktalarını takip etmesi,
- Sensörlerden yararlanması,
- Engeller karşısında durması veya güvenli manevra yapması,
- Eğimli ve dar bölgelerde uygun hız kullanması,
- Görev tamamlandığında durması,
- Sensör veya haberleşme kaybında güvenli duruşa geçmesi

zorunludur.

Görev noktaları ve çalışma parametreleri kaynak kod içine sabitlenmemeli; yapılandırma dosyaları veya ROS 2 parametreleri üzerinden değiştirilebilmelidir.

## Parkur değerlendirmesi

Değerlendirmede 2025 parkurundaki arazi ve engel bölümleri kullanılacaktır. Aşağıdaki bölümler test edilebilir:

- Normal yol
- Dik eğim
- Yan eğim
- Su geçişi
- Koniler
- Tabelalar
- Bariyerler

Final testinde başlangıç konumu, görev noktaları veya bazı engel konumları değiştirilebilir. Bu nedenle yalnızca tek bir önceden kaydedilmiş sürüşe veya sabit koordinatlara bağlı çözümler yeterli kabul edilmeyecektir.

## Teknik kısıtlar

- Verilen araç ve parkur dosyaları değiştirilemez.
- Otonom görev sırasında klavye, joystick veya manuel komut kullanılamaz.
- Otonom sistem, kendi ROS 2 düğümleri ve yapılandırmalarıyla çalışmalıdır.
- Tüm hareket komutları bir güvenlik kontrolünden geçmelidir.
- Komut, sensör veya ana otonomi düğümü kesildiğinde araç hareket etmemelidir.
- Kullanılan bütün düğümler launch dosyalarıyla başlatılabilmelidir.
- Parametreler kaynak kod içerisine gömülmemelidir.

## Teslim edilmesi gerekenler

- ROS 2 çalışma alanı ve kaynak paketler
- Simülasyon başlatma launch dosyası
- Manuel sürüş sistemi
- Otonom sürüş sistemi
- Controller ve parametre dosyaları
- Lokalizasyon ve sensör yapılandırmaları
- Güvenlik ve watchdog sistemi
- Kurulum ve çalıştırma README dosyası
- Sistem mimarisi diyagramı
- Manuel sürüş rosbag kaydı
- Otonom sürüş rosbag kaydı
- Teknik rapor
- Manuel ve otonom sürüş videosu

## Değerlendirme

| Kategori | Puan |
|---|---:|
| Simülasyonun kurulması ve launch yapısı | 10 |
| ROS 2 mimarisi ve paket kalitesi | 15 |
| Manuel sürüş | 15 |
| TF, odometri ve lokalizasyon | 15 |
| Sensör kullanımı ve engel davranışı | 15 |
| Otonom parkur görevi | 20 |
| Güvenlik, watchdog ve hata yönetimi | 5 |
| Raporlama ve teknik sunum | 5 |
| **Toplam** | **100** |

## Başarısızlık durumları

Aşağıdaki durumlar kritik hata kabul edilir:

- Araçta acil duruş veya watchdog bulunmaması
- Komut kesildiğinde aracın hareket etmeye devam etmesi
- Otonom görev sırasında manuel müdahale yapılması
- Parkur veya araç dosyalarının değiştirilmesi
- Çarpışma sonrası göreve devam edilmesi
- Takım üyelerinin geliştirdikleri sistemi açıklayamaması

## Sözlü teknik değerlendirme

Her takım üyesi kendi geliştirdiği bölümle ilgili aşağıdaki konuları açıklayabilmelidir:

- ROS 2 düğümlerinin görevleri
- Topic, service ve action kullanımı
- TF frame ilişkileri
- Ackermann sürüş mantığı
- Odometri ve lokalizasyon yaklaşımı
- Sensör QoS seçimi
- Engel algılama ve güvenli duruş mantığı
- Simülasyon ile gerçek araç arasındaki farklar

Başarı ölçütü yalnızca parkuru tamamlamak değil; geliştirilen sistemin anlaşılabilir, parametrelenebilir, güvenli ve başka bir parkur koşuluna uyarlanabilir olmasıdır.
