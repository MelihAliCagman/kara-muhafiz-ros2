#!/usr/bin/env python3
"""Simulasyon (sim_bringup) + manuel surus komut adaptoru (manual_drive_node).

teleop_twist_keyboard AYRI bir terminalde elle calistirilmali (klavye girdisi
icin kendi terminaline/stdin'ine ihtiyac duyuyor, launch icinden otomatik
baslatmak klavye etkilesimini bozar):

    ros2 run teleop_twist_keyboard teleop_twist_keyboard
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    bringup_share = get_package_share_directory("karamuhafiz_bringup")

    sim_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_share, "launch", "sim_bringup.launch.py")
        )
    )

    manual_drive_yaml = os.path.join(bringup_share, "config", "manual_drive.yaml")

    manual_drive_node = Node(
        package="karamuhafiz_control",
        executable="manual_drive_node",
        output="screen",
        parameters=[manual_drive_yaml],
    )

    return LaunchDescription([
        sim_bringup,
        manual_drive_node,
    ])
