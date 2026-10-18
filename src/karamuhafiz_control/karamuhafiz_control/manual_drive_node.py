#!/usr/bin/env python3
"""Manuel surus komut adaptoru.

/cmd_vel (standart teleop ciktisi) -> guvenlik limitleri + isaret duzeltmesi
-> /ackermann_steering_controller/reference_unstamped

Ackermann controller'in kendi reference_timeout'u (controllers.yaml) zaten bir
guvenlik agi sagliyor, ama o yalnizca "en son gelen komut" uzerinden calisir.
Bu node AYRICA kendi command_timeout'unu tutar: /cmd_vel akisi kesilirse
(teleop_twist_keyboard tus birakildiginda yeni mesaj GONDERMEZ) sifir komuta
donup sureki yayinlamaya devam eder - boylece arac "son basilan tusla" sonsuza
kadar hareket etmeye devam etmez.

AYRICA ayri bir ACIL DURUS (e-stop) mekanizmasi tasir: /emergency_stop
(std_msgs/Bool) topic'i True oldugunda arac KILITLENIR - /cmd_vel'den ne
gelirse gelsin sifir komut yayinlanir, ta ki acikca False (reset) gelene
kadar. Bu, command_timeout'tan FARKLI bir guvenlik katmani: command_timeout
"komut akisi kesildi" durumunu yakalar (pasif/kazayla), e-stop ise operatorun
BILINCLI olarak "DUR" dedigi aktif/acil durumu temsil eder ve siradan komut
akisi devam etse bile gecerliligini korur (latch/kilitli).
"""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool


class ManualDriveNode(Node):

    def __init__(self):
        super().__init__('manual_drive_node')

        # Parametreler kaynak koda gomulmemeli (gorev sartnamesi) - hepsi
        # launch/yaml'dan degistirilebilir, varsayilan degerler sadece guvenli
        # bir baslangic noktasi.
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter(
            'output_topic', '/ackermann_steering_controller/reference_unstamped')
        self.declare_parameter('emergency_stop_topic', '/emergency_stop')
        self.declare_parameter('invert_linear', True)
        self.declare_parameter('max_linear_speed', 1.5)   # m/s
        self.declare_parameter('max_angular_speed', 0.5)  # rad/s
        self.declare_parameter('command_timeout', 0.3)    # s
        self.declare_parameter('publish_rate', 20.0)       # Hz

        self._cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        self._output_topic = self.get_parameter('output_topic').value
        self._estop_topic = self.get_parameter('emergency_stop_topic').value
        self._invert_linear = self.get_parameter('invert_linear').value
        self._max_linear = self.get_parameter('max_linear_speed').value
        self._max_angular = self.get_parameter('max_angular_speed').value
        self._command_timeout = self.get_parameter('command_timeout').value
        publish_rate = self.get_parameter('publish_rate').value

        self._last_cmd = Twist()
        self._last_cmd_time = self.get_clock().now()
        self._stopped_logged = False
        self._estop = False

        self._sub = self.create_subscription(
            Twist, self._cmd_vel_topic, self._cmd_vel_callback, 10)
        self._estop_sub = self.create_subscription(
            Bool, self._estop_topic, self._estop_callback, 10)
        self._pub = self.create_publisher(Twist, self._output_topic, 10)
        self._timer = self.create_timer(1.0 / publish_rate, self._tick)

        self.get_logger().info(
            f"manual_drive_node hazir: '{self._cmd_vel_topic}' -> "
            f"'{self._output_topic}' | invert_linear={self._invert_linear} "
            f"max_linear={self._max_linear} m/s max_angular={self._max_angular} "
            f"rad/s command_timeout={self._command_timeout}s "
            f"emergency_stop_topic='{self._estop_topic}'"
        )

    def _cmd_vel_callback(self, msg: Twist) -> None:
        self._last_cmd = msg
        self._last_cmd_time = self.get_clock().now()
        self._stopped_logged = False

    def _estop_callback(self, msg: Bool) -> None:
        if msg.data != self._estop:
            if msg.data:
                self.get_logger().error("ACIL DURUS tetiklendi - arac kilitlendi.")
            else:
                self.get_logger().info("Acil durus sifirlandi - arac tekrar komut alabilir.")
        self._estop = msg.data

    def _tick(self) -> None:
        if self._estop:
            # Acil durus AKTIF: /cmd_vel'den ne gelirse gelsin arac kilitli
            # kalir - command_timeout mantigindan farkli olarak taze komut
            # gelmesi bunu GECERSIZ KILMAZ, yalnizca /emergency_stop'a False
            # gelmesi (bilincli reset) kilidi acar.
            self._pub.publish(Twist())
            return

        elapsed_s = (self.get_clock().now() - self._last_cmd_time).nanoseconds / 1e9

        out = Twist()
        if elapsed_s > self._command_timeout:
            # Guvenlik: /cmd_vel akisi kesildi (teleop kapandi, dugum coktu,
            # haberlesme koptu...) -> arac SIFIR komutla durur.
            out.linear.x = 0.0
            out.angular.z = 0.0
            if not self._stopped_logged:
                self.get_logger().warn(
                    f"/cmd_vel {self._command_timeout}s'den uzun suredir sessiz - "
                    "guvenlik icin arac durduruluyor.")
                self._stopped_logged = True
        else:
            linear = _clamp(self._last_cmd.linear.x, self._max_linear)
            angular = _clamp(self._last_cmd.angular.z, self._max_angular)
            out.linear.x = -linear if self._invert_linear else linear
            out.angular.z = angular

        self._pub.publish(out)


def _clamp(value: float, limit: float) -> float:
    return max(-limit, min(limit, value))


def main(args=None):
    rclpy.init(args=args)
    node = ManualDriveNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
