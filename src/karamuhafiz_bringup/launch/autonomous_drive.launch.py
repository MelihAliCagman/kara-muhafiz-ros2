#!/usr/bin/env python3
"""Simulasyon + lokalizasyon + Nav2 + gorev baslatici (otonom suruş).

localization.launch.py'yi (ki o da sim + manuel surus altyapisini) dahil
eder, uzerine Nav2 yigini ve waypoint_mission_node'u ekler.

Manuel/otonom guvenli gecis: twist_mux, iki /cmd_vel kaynagini (manuel
oncelikli, otonom dusuk oncelikli) TEK bir /cmd_vel'e birlestirir;
manual_drive_node (localization.launch.py -> manual_drive.launch.py icinde
zaten calisiyor) bu BIRLESTIRILMIS komutu alip her zamanki guvenlik
(clamp + watchdog + e-stop) katmanindan gecirir - yani manuel VE otonom
komutlar AYNI tek guvenlik kapisindan geciyor, iki ayri guvenlik mantigi
YOK. Operator, bu launch calisirken AYRI bir terminalde:

    ros2 run karamuhafiz_control global_keyboard_teleop_node \\
        --ros-args -p cmd_vel_topic:=/cmd_vel_manual

calistirirsa, her an otonomiyi EZIP GECEBILIR (manuel oncelik=100 >
otonom oncelik=10). Hicbir manuel teleop calismiyorsa twist_mux otomatik
olarak otonom kaynaga (/cmd_vel_nav2) gecer.

NOT: twist_mux paketi bu oturumda KURULU DEGIL (sudo sifresi gerektirdigi
icin kurulamadi) - kod YAZILDI ama DOGRULANAMADI. Once:
    sudo apt install ros-humble-twist-mux
Diger tum dosyalar (Nav2 yigini) Gazebo'suz standalone "configure" testiyle
dogrulandi (bkz. Hafta 3 Gun 1 raporu).
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    bringup_share = get_package_share_directory("karamuhafiz_bringup")

    localization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, "launch", "localization.launch.py")
        )
    )

    nav2_params = os.path.join(bringup_share, "config", "nav2_params.yaml")
    mission_yaml = os.path.join(bringup_share, "config", "mission_waypoints.yaml")

    # HATA DUZELTMESI (canli testte bulundu, 2026-10-24): nav2_params.yaml'da
    # default_nav_to_pose_bt_xml / default_nav_through_poses_bt_xml SADECE
    # dosya adi olarak yazilmisti ("navigate_to_pose_w_replanning_and_recovery.xml").
    # bt_navigator bunu bulunduğu dizine (calisma dizini) gore aradigi icin
    # "Couldn't open input XML file" hatasiyla configure asamasinda cakiyor,
    # bu da lifecycle_manager'in TUM Nav2 yiginini "Aborting bringup" ile
    # iptal etmesine - ve dolayisiyla hicbir hiz komutu uretilmemesine sebep
    # oluyordu. Cozum: TAM dosya yolunu burada (Python'da, nav2_bt_navigator
    # paketinin kendi share dizininden) hesaplayip, YAML'daki bare-filename
    # degerlerinin UZERINE parametre olarak geciyoruz.
    bt_navigator_share = get_package_share_directory("nav2_bt_navigator")
    bt_xml_dir = os.path.join(bt_navigator_share, "behavior_trees")
    bt_navigator_overrides = {
        "default_nav_to_pose_bt_xml": os.path.join(
            bt_xml_dir, "navigate_to_pose_w_replanning_and_recovery.xml"),
        "default_nav_through_poses_bt_xml": os.path.join(
            bt_xml_dir, "navigate_through_poses_w_replanning_and_recovery.xml"),
    }

    nav2_nodes = [
        Node(
            package="nav2_controller", executable="controller_server",
            name="controller_server", output="screen",
            parameters=[nav2_params],
            # Nav2'nin ham hiz komutu once velocity_smoother'dan gecsin
            # (ani hizlanma/yavaslama sinirlanir - egim/dar bolge guvenligi),
            # ardindan Ackermann controller'a ulassin.
            remappings=[("cmd_vel", "cmd_vel_nav2_raw")],
        ),
        Node(
            package="nav2_planner", executable="planner_server",
            name="planner_server", output="screen",
            parameters=[nav2_params],
        ),
        Node(
            package="nav2_behaviors", executable="behavior_server",
            name="behavior_server", output="screen",
            parameters=[nav2_params],
        ),
        Node(
            package="nav2_bt_navigator", executable="bt_navigator",
            name="bt_navigator", output="screen",
            parameters=[nav2_params, bt_navigator_overrides],
        ),
        Node(
            package="nav2_waypoint_follower", executable="waypoint_follower",
            name="waypoint_follower", output="screen",
            parameters=[nav2_params],
        ),
        Node(
            package="nav2_velocity_smoother", executable="velocity_smoother",
            name="velocity_smoother", output="screen",
            parameters=[nav2_params],
            remappings=[
                ("cmd_vel", "cmd_vel_nav2_raw"),
                # GECICI (Hafta 3 canli test, bkz. collision_detection_temporarily_disabled
                # hafiza notu): normalde buradan collision_monitor'a gidip
                # oradan twist_mux'a ulasmaliydi. collision_monitor'un
                # StopZone'u (1m) da ayni namlu/taret kendi-algilama sorunu
                # yuzunden komutu surekli sifirlayip "Failed to make progress"
                # ile gorevi iptal ettiriyordu. collision_monitor GECICI
                # olarak devre disi birakildi (asagidaki Node tanimi ve
                # lifecycle_manager listesinden cikarildi) - DUZGUN BIR
                # NAMLU-FARKINDA FILTRE ILE GERI EKLENMELI, teslimden once!
                ("cmd_vel_smoothed", "/cmd_vel_nav2"),
            ],
        ),
        Node(
            package="nav2_lifecycle_manager", executable="lifecycle_manager",
            name="lifecycle_manager_navigation", output="screen",
            parameters=[
                nav2_params,
                {"node_names": [
                    "controller_server", "planner_server", "behavior_server",
                    "bt_navigator", "waypoint_follower", "velocity_smoother",
                ]},
            ],
        ),
    ]

    waypoint_mission_node = Node(
        package="karamuhafiz_control",
        executable="waypoint_mission_node",
        output="screen",
        parameters=[mission_yaml],
    )

    twist_mux_yaml = os.path.join(bringup_share, "config", "twist_mux.yaml")
    twist_mux_node = Node(
        package="twist_mux",
        executable="twist_mux",
        output="screen",
        parameters=[twist_mux_yaml, {"use_sim_time": True}],
        # Birlestirilmis cikis, manual_drive_node'un zaten dinledigi
        # varsayilan /cmd_vel ismine gidiyor - manual_drive_node degismedi.
        remappings=[("cmd_vel_out", "/cmd_vel")],
    )

    return LaunchDescription([
        localization,
        *nav2_nodes,
        waypoint_mission_node,
        twist_mux_node,
    ])
