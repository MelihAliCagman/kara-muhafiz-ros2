from setuptools import find_packages, setup

package_name = 'karamuhafiz_control'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='melihali',
    maintainer_email='cagmanmelihali@gmail.com',
    description='Kara Muhafız manuel sürüş ve güvenlik (komut aktarma/watchdog) ROS 2 node\'ları.',
    license='TODO',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'manual_drive_node = karamuhafiz_control.manual_drive_node:main',
            'keyboard_teleop_node = karamuhafiz_control.keyboard_teleop_node:main',
            'global_keyboard_teleop_node = karamuhafiz_control.global_keyboard_teleop_node:main',
            'waypoint_mission_node = karamuhafiz_control.waypoint_mission_node:main',
        ],
    },
)
