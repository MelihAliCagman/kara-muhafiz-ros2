# Kara Muhafız — ROS 2 2025 Parkur Görevi

Teknofest 2025 parkuru için Kara Muhafız UGV'sinin ROS 2 (Humble) + Gazebo Classic tabanlı manuel sürüş ve otonomi altyapısı.

Görevde takıma yalnızca araç modeli (URDF/xacro, mesh'ler) ve parkur world dosyası verilmiştir; bu dosyalara **hiçbir satır dokunulmamıştır**. Launch sistemi, controller yapılandırması, manuel sürüş, güvenlik ve (ilerleyen aşamada) otonomi tamamen bu repoda sıfırdan geliştirilmektedir. Görev detayları için [GOREV_ACIKLAMASI_2025.md](GOREV_ACIKLAMASI_2025.md) dosyasına bakınız.

## Paket Yapısı

Bu bir [colcon](https://colcon.readthedocs.io/) workspace'idir:

```
src/
  karamuhafiz_base/      verilen (değiştirilmeyen) araç modeli, mesh'ler, parkur world dosyası
  karamuhafiz_bringup/   launch dosyaları ve controller/parametre konfigürasyonları
  karamuhafiz_control/   manuel sürüş ve güvenlik ROS 2 node'ları (Python)
```

| Paket | Tip | İçerik |
|---|---|---|
| `karamuhafiz_base` | ament_cmake | Verilen URDF/xacro, mesh'ler, `teknofest_parkur.world` |
| `karamuhafiz_bringup` | ament_cmake | `sim_bringup.launch.py`, `manual_drive.launch.py`, controller/parametre YAML'ları |
| `karamuhafiz_control` | ament_python | `manual_drive_node`, `keyboard_teleop_node`, `global_keyboard_teleop_node` |

## Gereksinimler

- Ubuntu 22.04
- ROS 2 Humble
- Gazebo Classic 11 (`gazebo_ros_pkgs`, `gazebo_ros2_control`, `ros2_controllers`)
- Python 3 — `pynput` (global klavye kontrolü için): `pip3 install --user pynput`

## Kurulum

```bash
cd kara-muhafiz-ros2
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

## Çalıştırma

### Yalnızca simülasyon (araç + parkur)

```bash
ros2 launch karamuhafiz_bringup sim_bringup.launch.py
```

### Manuel sürüş (simülasyon + komut adaptörü)

```bash
ros2 launch karamuhafiz_bringup manual_drive.launch.py
```

Ayrı bir terminalde klavye kontrolü (pencere odağından bağımsız, önerilen):

```bash
ros2 run karamuhafiz_control global_keyboard_teleop_node
```

ya da terminal odaklıyken çalışan basit sürüm:

```bash
ros2 run karamuhafiz_control keyboard_teleop_node
```

Takip kamerası (araca sabit bağlı, geniş açılı):

```bash
ros2 run rqt_image_view rqt_image_view /chase_cam/image_raw
```

#### Klavye Kontrolleri

| Tuş | İşlev |
|---|---|
| ↑ / ↓ | ileri hızlan / yavaşla-geri |
| ← / → | sola / sağa dön |
| BOŞLUK | anında dur (hız + dönüş sıfırlanır) |
| `e` | **ACİL DURUŞ** — araç kilitlenir, `r` gelene kadar hiçbir komut etkili olmaz |
| `r` | acil duruşu sıfırla |
| `q` / `ESC` | çıkış (güvenlik için sıfır komut + acil duruş bırakarak) |

## Özellikler

- **Ackermann sürüş**: `ackermann_steering_controller` (ros2_control) ile arkadan itişli (RWD), önden direksiyonlu kinematik
- **Manuel sürüş komut adaptörü** (`manual_drive_node`): `/cmd_vel` → güvenli hız/dönüş limitleri → Ackermann controller; parametreler koda gömülmemiştir, tamamı YAML'dan okunur
- **Çift güvenlik katmanı**:
  - *Pasif watchdog*: `/cmd_vel` akışı kesilirse (`command_timeout`) araç otomatik durur
  - *Aktif acil duruş*: `/emergency_stop` (latch) ile bilinçli, kalıcı durdurma
- **2D LiDAR** (`/scan`, 360°) ve **araca bağlı takip kamerası** (`/chase_cam/image_raw`) — verilen xacro dosyasına dokunmadan, launch aşamasında modele enjekte edilmiştir
- **6 sonar sensörü** (verilen modelde mevcut) — 360° çevre koruması

## Belgeler

- [`Kara_Muhafiz_ROS2_Yol_Haritasi.pdf`](Kara_Muhafiz_ROS2_Yol_Haritasi.pdf) — 4 haftalık geliştirme planı
- [`Konu_Anlatimi_ROS2.pdf`](Konu_Anlatimi_ROS2.pdf) — sıfırdan ROS 2 konu anlatımı (bu proje üzerinden)
- `Gun*_Calisma_Raporu.pdf` — günlük ilerleme raporları (yapılanlar, karşılaşılan hatalar/çözümleri, kod analizi)

## Bilinen Notlar

- Su geçişinde (`sudan_gecis.dae`) gerçek su fiziği (buoyancy/direnç) şu an simüle edilmiyor — performans nedeniyle kasıtlı olarak projenin ileri bir aşamasına ertelendi.
- LiDAR, belirli açılarda aracın kendi taret/namlu parçasını algılayabiliyor (kısa mesafe okuması); costmap entegrasyonunda filtrelenmesi planlanıyor.

## Durum

Hafta 1 (manuel sürüş + simülasyon kurulumu) tamamlandı. Sıradaki aşama: sensör füzyonu ve lokalizasyon (Hafta 2), ardından Nav2 ile otonom parkur görevi.
