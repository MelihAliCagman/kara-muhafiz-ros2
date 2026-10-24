#!/usr/bin/env python3
"""Otonom gorev baslatici: parametrelerden okunan gorev noktalarini
Nav2'nin FollowWaypoints action server'ina gonderir.

Gorev sartnamesi: "Otonom sistemin ... operatorun gorevi baslatmasindan
sonra ... Gorev noktalari ve calisma parametreleri kaynak kod icine
sabitlenmemeli" diyor. Bu node iki gereksinimi birden karsiliyor:
  1) Gorev noktalari (waypoint_x/y/yaw) parametre olarak DISARIDAN
     (mission_waypoints.yaml) okunuyor, kod icinde sabit deger YOK.
  2) Otonom gorev OTOMATIK baslamiyor - yalnizca operator
     /start_mission servisine (std_srvs/Trigger) cagri yapinca Nav2'ye
     FollowWaypoints hedefi gonderiliyor.

Ayrica /emergency_stop (bkz. manual_drive_node) True olursa devam eden
gorevi IPTAL eder - otonom sirasinda da acil durus gecerli olmali.
"""
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup

from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import FollowWaypoints
from std_msgs.msg import Bool
from std_srvs.srv import Trigger


class WaypointMissionNode(Node):

    def __init__(self):
        super().__init__('waypoint_mission_node')

        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('waypoint_x', [0.0])
        self.declare_parameter('waypoint_y', [0.0])
        self.declare_parameter('waypoint_yaw', [0.0])
        self.declare_parameter('emergency_stop_topic', '/emergency_stop')

        self._frame_id = self.get_parameter('frame_id').value
        self._wx = list(self.get_parameter('waypoint_x').value)
        self._wy = list(self.get_parameter('waypoint_y').value)
        self._wyaw = list(self.get_parameter('waypoint_yaw').value)

        if not (len(self._wx) == len(self._wy) == len(self._wyaw)):
            self.get_logger().error(
                "waypoint_x/y/yaw parametreleri AYNI uzunlukta olmali! "
                f"x={len(self._wx)} y={len(self._wy)} yaw={len(self._wyaw)} - "
                "gorev baslatilamaz.")
            self._wx = self._wy = self._wyaw = []

        self._estop = False
        self._goal_handle = None

        cb_group = ReentrantCallbackGroup()
        self._action_client = ActionClient(
            self, FollowWaypoints, 'follow_waypoints', callback_group=cb_group)
        self._start_srv = self.create_service(
            Trigger, 'start_mission', self._start_mission_cb, callback_group=cb_group)
        self._estop_sub = self.create_subscription(
            Bool, self.get_parameter('emergency_stop_topic').value,
            self._estop_cb, 10, callback_group=cb_group)

        self.get_logger().info(
            f"waypoint_mission_node hazir: {len(self._wx)} gorev noktasi "
            f"yuklendi (frame_id='{self._frame_id}'). Baslatmak icin: "
            "ros2 service call /start_mission std_srvs/srv/Trigger"
        )

    def _estop_cb(self, msg: Bool) -> None:
        was_estop = self._estop
        self._estop = msg.data
        if self._estop and not was_estop and self._goal_handle is not None:
            self.get_logger().error(
                "ACIL DURUS - devam eden otonom gorev iptal ediliyor.")
            self._goal_handle.cancel_goal_async()

    def _start_mission_cb(self, request, response):
        if not self._wx:
            response.success = False
            response.message = "Gorev noktasi yuklu degil (parametre hatasi)."
            return response

        if self._estop:
            response.success = False
            response.message = "Acil durus aktif - once /emergency_stop sifirlanmali."
            return response

        if not self._action_client.wait_for_server(timeout_sec=5.0):
            response.success = False
            response.message = (
                "Nav2 follow_waypoints action server'ina ulasilamadi "
                "(Nav2 calisiyor mu?).")
            return response

        goal = FollowWaypoints.Goal()
        for x, y, yaw in zip(self._wx, self._wy, self._wyaw):
            pose = PoseStamped()
            pose.header.frame_id = self._frame_id
            pose.pose.position.x = x
            pose.pose.position.y = y
            pose.pose.orientation.z = _yaw_to_qz(yaw)
            pose.pose.orientation.w = _yaw_to_qw(yaw)
            goal.poses.append(pose)

        self.get_logger().info(f"Gorev basliyor: {len(goal.poses)} nokta gonderildi.")
        send_future = self._action_client.send_goal_async(
            goal, feedback_callback=self._feedback_cb)
        send_future.add_done_callback(self._goal_response_cb)

        response.success = True
        response.message = f"{len(goal.poses)} gorev noktasiyla otonom gorev baslatildi."
        return response

    def _goal_response_cb(self, future) -> None:
        self._goal_handle = future.result()
        if not self._goal_handle.accepted:
            self.get_logger().error("Nav2 gorevi reddetti.")
            return
        result_future = self._goal_handle.get_result_async()
        result_future.add_done_callback(self._result_cb)

    def _feedback_cb(self, feedback_msg) -> None:
        current = feedback_msg.feedback.current_waypoint
        self.get_logger().info(f"Gorev noktasi {current} tamamlandi/yoldaa.")

    def _result_cb(self, future) -> None:
        result = future.result().result
        missed = list(result.missed_waypoints)
        if missed:
            self.get_logger().warn(f"Gorev TAMAMLANDI ama kacirilan noktalar: {missed}")
        else:
            self.get_logger().info("Gorev BASARIYLA tamamlandi - tum noktalara ulasildi.")
        self._goal_handle = None


def _yaw_to_qz(yaw: float) -> float:
    import math
    return math.sin(yaw / 2.0)


def _yaw_to_qw(yaw: float) -> float:
    import math
    return math.cos(yaw / 2.0)


def main(args=None):
    rclpy.init(args=args)
    node = WaypointMissionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
