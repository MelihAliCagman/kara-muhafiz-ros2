cmake_minimum_required(VERSION 3.8)
project(karamuhafiz_base)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY urdf meshes worlds
  DESTINATION share/${PROJECT_NAME}
)

install(
  FILES model.config
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
