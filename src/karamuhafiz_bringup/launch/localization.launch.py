#!/usr/bin/env python3
"""Simulasyon + manuel surus + lokalizasyon (robot_localization cift-EKF + navsat_transform).

Hafta 2 Gun 1: tekerlek odometrisi + IMU (yerel EKF, odom->base_footprint) ve
+ GPS (global EKF, map->odom) fuzyonu. manual_drive.launch.py'yi (ki o da
sim_bringup.launch.py'yi) dahil eder - tek komutla tam yigin ayaga kalkar.

TF zinciri (hedeflenen): map -> odom -> base_footprint -> base_link -> ...
  - odom->base_footprint   : ekf_filter_node_odom (yerel EKF)
  - map->odom               : ekf_filter_node_map (global EKF)

NOT: Bu dosya simulasyonda CANLI TEST EDILMEDI (bkz. Hafta 2 Gun 1 raporu) -
robot_localization'in standart, belgelenmis cift-EKF deseni kullanildi;
parametre ince ayari (covariance/frequency) gercek calistirma sonrasi
gerekebilir.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    bringup_share = get_package_share_directory("karamuhafiz_bringup")

    manual_drive = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, "launch", "manual_drive.launch.py")
        )
    )

    ekf_local_yaml = os.path.join(bringup_share, "config", "ekf_local.yaml")
    ekf_global_yaml = os.path.join(bringup_share, "config", "ekf_global.yaml")
    navsat_yaml = os.path.join(bringup_share, "config", "navsat_transform.yaml")

    ekf_local_node = Node(
        package="robot_localization",
        executable="ekf_node",
        name="ekf_filter_node_odom",
        output="screen",
        parameters=[ekf_local_yaml, {"use_sim_time": True}],
        remappings=[("odometry/filtered", "odometry/filtered")],
    )

    navsat_transform_node = Node(
        package="robot_localization",
        executable="navsat_transform_node",
        name="navsat_transform_node",
        output="screen",
        parameters=[navsat_yaml, {"use_sim_time": True}],
        remappings=[
            ("imu/data", "/imu/data"),
            ("gps/fix", "/gps/fix"),
            ("odometry/filtered", "/odometry/filtered"),
            ("odometry/gps", "/odometry/gps"),
        ],
    )

    ekf_global_node = Node(
        package="robot_localization",
        executable="ekf_node",
        name="ekf_filter_node_map",
        output="screen",
        parameters=[ekf_global_yaml, {"use_sim_time": True}],
        # Global EKF'in /odometry/filtered ciktisini yerelden AYRI bir isimle
        # yayinliyoruz - aksi halde iki EKF ayni topic'e yazip cakisir.
        remappings=[("odometry/filtered", "odometry/filtered_map")],
    )

    return LaunchDescription([
        manual_drive,
        ekf_local_node,
        navsat_transform_node,
        ekf_global_node,
    ])
