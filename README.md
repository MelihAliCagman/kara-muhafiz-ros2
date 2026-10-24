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
| `karamuhafiz_bringup` | ament_cmake | Launch dosyaları, controller/lokalizasyon/Nav2 parametre YAML'ları, RViz config |
| `karamuhafiz_control` | ament_python | `manual_drive_node`, `keyboard_teleop_node`, `global_keyboard_teleop_node`, `waypoint_mission_node` |

## Gereksinimler

- Ubuntu 22.04
- ROS 2 Humble
- Gazebo Classic 11 (`gazebo_ros_pkgs`, `gazebo_ros2_control`, `ros2_controllers`)
- `robot_localization`, Nav2 paket ailesi (`ros-humble-navigation2` kapsamındaki tüm paketler)
- `ros-humble-twist-mux` — **henüz kurulu değil**, otonom/manuel geçiş testinden önce: `sudo apt install ros-humble-twist-mux`
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

### Lokalizasyon (Hafta 2)

```bash
ros2 launch karamuhafiz_bringup localization.launch.py
```

Simülasyon + manuel sürüş + `robot_localization` çift-EKF (tekerlek odometrisi + IMU + GPS) + RViz2 (`use_rviz:=false` ile kapatılabilir). TF zinciri: `map → odom → base_footprint → base_link → ...`

### Otonom sürüş (Hafta 3)

```bash
ros2 launch karamuhafiz_bringup autonomous_drive.launch.py
```

Yukarıdakinin üstüne Nav2 yığınını (costmap, controller, planner, behavior, waypoint_follower, velocity_smoother, collision_monitor) ve `waypoint_mission_node`'u ekler. Görevi başlatmak için (otomatik başlamaz — operatör tetiklemeli):

```bash
ros2 service call /start_mission std_srvs/srv/Trigger
```

Otonomi sırasında manuel sürmek istersen, ayrı bir terminalde (`twist_mux` sayesinde otonomiyi önceliğiyle ezer):

```bash
ros2 run karamuhafiz_control global_keyboard_teleop_node --ros-args -p cmd_vel_topic:=/cmd_vel_manual
```

## Özellikler

- **Ackermann sürüş**: `ackermann_steering_controller` (ros2_control) ile arkadan itişli (RWD), önden direksiyonlu kinematik
- **Manuel sürüş komut adaptörü** (`manual_drive_node`): `/cmd_vel` → güvenli hız/dönüş limitleri → Ackermann controller; parametreler koda gömülmemiştir, tamamı YAML'dan okunur
- **Çoklu güvenlik katmanı**:
  - *Pasif watchdog*: `/cmd_vel` akışı kesilirse (`command_timeout`) araç otomatik durur
  - *Aktif acil duruş*: `/emergency_stop` (latch) ile bilinçli, kalıcı durdurma — hem `manual_drive_node`'da hem `twist_mux` kilidinde bağımsız kontrol edilir
  - *collision_monitor*: Nav2'nin planlama mantığından bağımsız, ham LiDAR ile son-çare yakın-mesafe durdurma
  - *twist_mux*: manuel komutlar (öncelik 100) her zaman otonom komutları (öncelik 10) ezer
- **Lokalizasyon**: `robot_localization` çift-EKF (yerel: odom, global: map) + GPS (`navsat_transform`) — harita/AMCL kullanılmıyor, Nav2'nin resmi GPS-waypoint-follower desenine dayanıyor
- **Otonom sürüş**: Nav2 (`nav2_regulated_pure_pursuit_controller` — Ackermann'ın dönüş yarıçapı kısıtını destekler), görev noktaları `mission_waypoints.yaml`'dan okunur (koda gömülmez), operatör `/start_mission` servisiyle başlatır
- **2D LiDAR** (`/scan`, 360°) ve **araca bağlı takip kamerası** (`/chase_cam/image_raw`) — verilen xacro dosyasına dokunmadan, launch aşamasında modele enjekte edilmiştir
- **6 sonar sensörü** (verilen modelde mevcut) — 360° çevre koruması, hem local costmap'e hem güvenlik sistemine besleniyor

## Belgeler

- [`Kara_Muhafiz_ROS2_Yol_Haritasi.pdf`](Kara_Muhafiz_ROS2_Yol_Haritasi.pdf) — 4 haftalık geliştirme planı
- [`Konu_Anlatimi_ROS2.pdf`](Konu_Anlatimi_ROS2.pdf) — sıfırdan ROS 2 konu anlatımı (bu proje üzerinden)
- `calisma_raporlari/` — günlük ilerleme raporları (yapılanlar, karşılaşılan hatalar/çözümleri, kod analizi); bu klasör yalnızca **yerelde** tutulur, repoya dahil değildir (`.gitignore`)

## Bilinen Notlar

- Su geçişinde (`sudan_gecis.dae`) gerçek su fiziği (buoyancy/direnç) şu an simüle edilmiyor — performans nedeniyle kasıtlı olarak projenin ileri bir aşamasına ertelendi.
- LiDAR, belirli açılarda aracın kendi taret/namlu parçasını algılayabiliyor (kısa mesafe okuması); costmap entegrasyonunda filtrelenmesi planlanıyor.

## Durum

Hafta 1-3 kod tarafı tamamlandı (manuel sürüş, lokalizasyon, Nav2 otonomi). **Hafta 2-3'ün kodu Gazebo GUI'de henüz canlı test edilmedi** — geliştirme ortamında grafik arayüze erişim kısıtlıydı; doğrulama, her node'u tek tek başlatıp parametre/plugin hatalarını yakalayacak şekilde (`ros2 lifecycle set ... configure`) yapıldı, ama gerçek sensör verisiyle uçtan uca davranış test edilmedi.

### Geri dönüşte yapılacaklar sırası

1. **Rosbag kaydı** (Hafta 1 turu zaten tamamlanmıştı, kayıt alınmamıştı — `rosbags/` klasörü hazır)
2. `sudo apt install ros-humble-twist-mux` (henüz kurulmadı)
3. `ros2 launch karamuhafiz_bringup localization.launch.py` — TF ağacını ve EKF çıktılarını RViz'de gözlemle
4. `ros2 launch karamuhafiz_bringup autonomous_drive.launch.py` — Nav2 yığınının tam olarak ayağa kalkıp kalkmadığını kontrol et
5. `mission_waypoints.yaml`'daki yer tutucu koordinatları gerçek parkur ölçümleriyle güncelle, sonra `/start_mission` ile gerçek bir otonom tur dene
