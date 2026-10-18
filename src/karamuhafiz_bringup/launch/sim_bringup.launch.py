#!/usr/bin/env python3
"""Kara Muhafız: Gazebo + parkur + araç + robot_state_publisher + joint_state_broadcaster.

Gün 2 kapsamı: simülasyonu ayağa kaldırmak ve TF/robot_description akışını doğrulamak.
Direksiyon/tahrik controller'ları (Ackermann) Gün 3'te eklenecek.

NOT (bilinen Gazebo Classic hatası): spawn_entity.py'yi "-topic robot_description" ile
canlı URDF spawn etmek icin kullanirsak, gazebo_ros paketinin dahili URDF->SDF
donusturucusu <ros2_control> blogu icin otomatik olarak "robot_description" XML'ini
"--param robot_description:=<xml>" seklinde bozuk bir parametre override'i olarak
ekliyor (XML icindeki tirnak/satir sonlari rclcpp'nin parametre ayristiricisini
bozuyor) ve controller_manager node'u hic baslamiyor. Bu, karamuhafiz_base'teki
urdf/controllers_yaml ile ilgili DEGIL, gazebo_ros'un kendi donusturucusundeki bilinen
bir hata (ayni sorun guncel paket surumunde de devam ediyor). Cozum: xacro'yu once
"gz sdf -p" ile (libsdformat9, ayni hataya sahip degil) SDF dosyasina cevirip
spawn_entity.py'yi "-file" ile dosyadan spawn etmek - bu, hatali kod yolunu tamamen
atliyor.
"""
import os
import re
import subprocess
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

# Arkadasin istegi uzerine eklenen 2D LiDAR. Verilen karamuhafiz.urdf.xacro
# dosyasina DOKUNMADAN ekleniyor: asagida xacro -> URDF donusumunden sonra bu
# parca, uretilen metnin SONUNA (</robot> etiketinden once) eklenir - disk
# uzerindeki orijinal dosya tamamen degismeden kalir. Mevcut sonar
# sensorlerinde zaten kanitlanmis ayni plugin (libgazebo_ros_ray_sensor.so)
# kullanildi, yeni/bilinmeyen bir plugin riski yok. Govde ustu, taretin
# (x=0, z=0.57) onunde, cakismayacak sekilde konumlandirildi.
LIDAR_SNIPPET = """
  <link name="lidar_link">
    <visual>
      <geometry><cylinder radius="0.035" length="0.04"/></geometry>
      <material name="black"/>
    </visual>
    <collision>
      <geometry><cylinder radius="0.035" length="0.04"/></geometry>
    </collision>
    <inertial>
      <mass value="0.15"/>
      <inertia ixx="0.0001" ixy="0" ixz="0" iyy="0.0001" iyz="0" izz="0.0001"/>
    </inertial>
  </link>
  <joint name="lidar_joint" type="fixed">
    <parent link="base_link"/><child link="lidar_link"/>
    <origin xyz="0.3 0 0.56" rpy="0 0 0"/>
  </joint>
  <gazebo reference="lidar_link">
    <sensor name="lidar" type="ray">
      <always_on>true</always_on>
      <visualize>true</visualize>
      <update_rate>10</update_rate>
      <ray>
        <scan>
          <horizontal>
            <samples>360</samples>
            <resolution>1</resolution>
            <min_angle>-3.14159265</min_angle>
            <max_angle>3.14159265</max_angle>
          </horizontal>
        </scan>
        <range><min>0.12</min><max>12.0</max><resolution>0.01</resolution></range>
      </ray>
      <plugin name="lidar_plugin" filename="libgazebo_ros_ray_sensor.so">
        <ros>
          <remapping>~/out:=scan</remapping>
        </ros>
        <output_type>sensor_msgs/LaserScan</output_type>
        <frame_name>lidar_link</frame_name>
      </plugin>
    </sensor>
    <material>Gazebo/Black</material>
  </gazebo>
"""

# Araca SABIT bagli, genis acili "takip kamerasi" (chase cam). Gazebo'nun
# kendi "Follow" modu sabit bir yakinlikta kilitleniyor ve genis aci ayari
# sunmuyor; bu kamera ise aracin govdesine (base_link) sabit bir eklemle
# bagli oldugu icin arac her dondugunde kamera da ONUNLA BIRLIKTE doner -
# ayri bir goruntu penceresinde (rqt_image_view) izlenir, Gazebo GUI
# kisitlarindan bagimsizdir. LiDAR ile ayni enjeksiyon yontemi: verilen
# xacro dosyasina dokunulmuyor, sadece uretilen URDF metninin sonuna eklenir.
CHASE_CAM_SNIPPET = """
  <link name="chase_cam_link">
    <visual>
      <geometry><box size="0.03 0.03 0.03"/></geometry>
      <material name="black"/>
    </visual>
    <inertial>
      <mass value="0.01"/>
      <inertia ixx="0.0001" ixy="0" ixz="0" iyy="0.0001" iyz="0" izz="0.0001"/>
    </inertial>
  </link>
  <joint name="chase_cam_joint" type="fixed">
    <parent link="base_link"/><child link="chase_cam_link"/>
    <!-- Aracin 2.2m gerisinde, 1.3m yukarisinda; hafif asagi egik (~20 derece
         pitch) bakarak araci kadraja alir. -->
    <origin xyz="-2.2 0 1.3" rpy="0 0.35 0"/>
  </joint>
  <gazebo reference="chase_cam_link">
    <sensor name="chase_cam" type="camera">
      <update_rate>30</update_rate>
      <camera>
        <horizontal_fov>1.8</horizontal_fov>
        <image><width>960</width><height>540</height><format>R8G8B8</format></image>
        <clip><near>0.1</near><far>100.0</far></clip>
      </camera>
      <plugin name="chase_cam_plugin" filename="libgazebo_ros_camera.so">
        <ros>
          <remapping>~/image_raw:=/chase_cam/image_raw</remapping>
          <remapping>~/camera_info:=/chase_cam/camera_info</remapping>
        </ros>
      </plugin>
      <material>Gazebo/Black</material>
    </sensor>
  </gazebo>
"""


def generate_launch_description():
    # Aracin spawn yonu (yaw, radyan). Parkurda ilerlenecek yone gore
    # ayarlanir - kaynak koda gomulmek yerine launch argumani: degistirmek
    # icin "ros2 launch ... spawn_yaw:=0.0" gibi komut satirindan override
    # edilebilir, dosya duzenlemeye gerek yok.
    spawn_yaw_arg = DeclareLaunchArgument(
        "spawn_yaw", default_value="3.14159265",
        description="Aracin baslangic yonelimi (yaw, radyan)."
    )
    spawn_yaw = LaunchConfiguration("spawn_yaw")

    base_share = get_package_share_directory("karamuhafiz_base")
    bringup_share = get_package_share_directory("karamuhafiz_bringup")

    xacro_file = os.path.join(base_share, "urdf", "karamuhafiz.urdf.xacro")
    world_file = os.path.join(base_share, "worlds", "teknofest_parkur.world")
    controllers_yaml = os.path.join(bringup_share, "config", "controllers.yaml")

    # world dosyasi "model://karamuhafiz_base/meshes/..." kullaniyor; Gazebo bunu
    # GAZEBO_MODEL_PATH icindeki bir dizinde "karamuhafiz_base/" alt klasoru olarak
    # arar. base_share zaten ".../share/karamuhafiz_base" oldugundan, bir ust dizini
    # (".../share") model path'e eklemek yeterli.
    gazebo_model_path = os.path.dirname(base_share)

    # 1) xacro -> URDF metni (robot_state_publisher'a robot_description parametresi
    #    olarak bu metin verilecek - TF ve /robot_description topic'i buradan gelir).
    urdf_xml = subprocess.run(
        ["xacro", xacro_file, f"controllers_yaml:={controllers_yaml}"],
        check=True, capture_output=True, text=True,
    ).stdout

    # LiDAR ve takip kamerasini, verilen xacro dosyasina DOKUNMADAN, uretilen
    # URDF metninin sonuna ekliyoruz (bkz. LIDAR_SNIPPET / CHASE_CAM_SNIPPET).
    urdf_xml = urdf_xml.replace(
        "</robot>", LIDAR_SNIPPET + CHASE_CAM_SNIPPET + "\n</robot>")

    # 2) Ayni URDF'i Gazebo'ya "-file" ile spawn etmek icin onceden SDF'e cevir
    #    (yukaridaki NOT'ta aciklanan bug'dan kacinmak icin).
    tmp_dir = tempfile.mkdtemp(prefix="karamuhafiz_sdf_")
    urdf_path = os.path.join(tmp_dir, "karamuhafiz.urdf")
    sdf_path = os.path.join(tmp_dir, "karamuhafiz.sdf")
    with open(urdf_path, "w") as f:
        f.write(urdf_xml)
    with open(sdf_path, "w") as f:
        subprocess.run(["gz", "sdf", "-p", urdf_path], check=True, stdout=f)

    # gazebo_ros2_control (0.4.x, Humble apt) bilinen bug: <robot_param_node> ile
    # robot_description'i uzaktan cekip controller_manager node'una "--param
    # robot_description:=<xml>" seklinde komut satiri override'i olarak aktariyor.
    # Bu deger dusuk seviyede (rcl/arguments.c) YAML olarak ayristiriliyor;
    # icinde "kelime: kelime" (iki nokta ustuste + bosluk) gecen HERHANGI bir
    # metin -- bizim xacro'daki Turkce aciklama YORUMLARINDA bolca var (orn.
    # "<!-- NOT: ... -->") -- YAML'e yeni bir anahtar-deger ciftinin basladigi
    # izlenimi verip "Couldn't parse parameter override rule" hatasina yol
    # aciyor. Asil .xacro dosyasina DOKUNMADAN, yalnizca robot_state_publisher'a
    # VERILECEK bellek-ici kopyadan XML yorumlarini temizleyip tek satira
    # sikistirarak bu YAML ayristirma hatasini bypass ediyoruz.
    urdf_no_comments = re.sub(r"<!--.*?-->", "", urdf_xml, flags=re.DOTALL)
    urdf_xml_flat = " ".join(urdf_no_comments.split())

    robot_description = ParameterValue(urdf_xml_flat, value_type=str)

    set_model_path = SetEnvironmentVariable(
        name="GAZEBO_MODEL_PATH",
        value=gazebo_model_path + ":" + os.environ.get("GAZEBO_MODEL_PATH", ""),
    )

    gzserver = ExecuteProcess(
        cmd=[
            "gzserver", world_file,
            "-s", "libgazebo_ros_init.so",
            "-s", "libgazebo_ros_factory.so",
        ],
        output="screen",
    )

    gzclient = ExecuteProcess(
        cmd=["gzclient"],
        output="screen",
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[{
            "use_sim_time": True,
            "robot_description": robot_description,
        }],
    )

    spawn_entity = Node(
        package="gazebo_ros",
        executable="spawn_entity.py",
        arguments=[
            "-file", sdf_path,
            "-entity", "karamuhafiz",
            "-z", "0.05",
            "-Y", spawn_yaw,
        ],
        output="screen",
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster"],
        output="screen",
    )

    ackermann_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["ackermann_steering_controller"],
        output="screen",
    )

    return LaunchDescription([
        spawn_yaw_arg,
        set_model_path,
        gzserver,
        gzclient,
        robot_state_publisher,
        spawn_entity,
        joint_state_broadcaster_spawner,
        ackermann_controller_spawner,
    ])
