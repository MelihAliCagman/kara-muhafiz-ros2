#!/usr/bin/env python3
"""Global (pencere odagindan bagimsiz) ok tuslu manuel surus teleop node'u.

Onceki keyboard_teleop_node yalnizca KENDI terminali odaktayken calisiyordu
(cunku ham terminal girdisini - stdin - okuyordu, ve terminal bir tusun
GERCEKTEN ne zaman birakildigini bilemiyordu - yalnizca OS'in tekrar eden
"key repeat" sinyallerini goruyordu, bu da ayni anda iki tus icin guvenilir
degildi).

Bu node X11'in GLOBAL klavye olaylarini (pynput kutuphanesi ile) dinler:
  - Herhangi bir pencere (orn. Gazebo) odaktayken de calisir.
  - GERCEK tusa-bas / tusu-birak olaylarini yakalar (tahmine dayali zaman
    asimi degil) - bu sayede birden fazla tus GERCEKTEN ayni anda basili
    tutulabilir (ileri + sola donus gibi).

Tuslar:
  Yukari ok  : ileri (basili tut = hareket, birak = yavaslar/durur)
  Asagi ok   : geri / fren (basili tut = hareket, birak = yavaslar/durur)
  Sol ok     : sola don (basili tut)
  Sag ok     : saga don (basili tut)
  BOSLUK     : aninda TAM dur (yalnizca gaz/donusu sifirlar, kilitlemez)
  e          : ACIL DURUS - arac KILITLENIR, 'r' basilana kadar hicbir
               /cmd_vel komutu etkili olmaz (manual_drive_node'daki
               /emergency_stop latch mantigi)
  r          : acil durusu sifirla (kilidi ac)
  ESC        : node'u kapat (guvenlik icin sifir komut + acil durus gonderip cikar)

cmd_vel'e NORMAL/sezgisel isaretle yazar (ileri = pozitif linear.x) - ters
isaret duzeltmesi gerekiyorsa (bkz. ackermann_sign_convention) bu
manual_drive_node tarafinda, TEK bir merkezi yerde (invert_linear parametresi)
yapilir.
"""
import threading

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool

try:
    from pynput import keyboard
except ImportError:
    keyboard = None


class GlobalKeyboardTeleopNode(Node):

    def __init__(self):
        super().__init__('global_keyboard_teleop_node')

        if keyboard is None:
            self.get_logger().error(
                "pynput kurulu degil. Kurulum: pip3 install --user pynput")
            raise SystemExit(1)

        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('emergency_stop_topic', '/emergency_stop')
        self.declare_parameter('linear_step', 0.15)
        self.declare_parameter('angular_step', 0.15)
        self.declare_parameter('linear_decay', 0.20)
        self.declare_parameter('angular_decay', 0.25)
        self.declare_parameter('max_linear_speed', 1.0)
        self.declare_parameter('max_angular_speed', 0.4)
        self.declare_parameter('publish_rate', 20.0)

        self._topic = self.get_parameter('cmd_vel_topic').value
        self._estop_topic = self.get_parameter('emergency_stop_topic').value
        self._linear_step = self.get_parameter('linear_step').value
        self._angular_step = self.get_parameter('angular_step').value
        self._linear_decay = self.get_parameter('linear_decay').value
        self._angular_decay = self.get_parameter('angular_decay').value
        self._max_linear = self.get_parameter('max_linear_speed').value
        self._max_angular = self.get_parameter('max_angular_speed').value
        publish_rate = self.get_parameter('publish_rate').value

        self._pub = self.create_publisher(Twist, self._topic, 10)
        self._estop_pub = self.create_publisher(Bool, self._estop_topic, 10)
        self._linear = 0.0
        self._angular = 0.0
        self._estop = False

        # pynput'un on_press/on_release callback'leri AYRI bir thread'de
        # calisir; bu yuzden paylasilan "basili tuslar" kumesini bir lock
        # ile koruyoruz (rclpy timer callback'i de ana thread'de calisiyor).
        self._lock = threading.Lock()
        self._pressed = set()

        self._listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release)
        self._listener.start()

        self._timer = self.create_timer(1.0 / publish_rate, self._tick)

        self.get_logger().info(
            "Global klavye teleop hazir (pencere odagindan BAGIMSIZ calisir) | "
            "Yon tuslari: basili tut = hareket | BOSLUK: ani dur | "
            "e: ACIL DURUS | r: acil durusu sifirla | ESC: cikis"
        )

    def _on_press(self, key) -> None:
        with self._lock:
            self._pressed.add(key)
        if key == keyboard.Key.esc:
            self._shutdown_requested = True
            rclpy.shutdown()
            return

        char = getattr(key, 'char', None)
        if char == 'e':
            self._estop = True
            self.get_logger().error("ACIL DURUS tetiklendi (klavye: 'e').")
        elif char == 'r':
            self._estop = False
            self.get_logger().info("Acil durus sifirlandi (klavye: 'r').")

    def _on_release(self, key) -> None:
        with self._lock:
            self._pressed.discard(key)

    def _tick(self) -> None:
        with self._lock:
            pressed = set(self._pressed)

        up = keyboard.Key.up in pressed
        down = keyboard.Key.down in pressed
        left = keyboard.Key.left in pressed
        right = keyboard.Key.right in pressed
        space = keyboard.Key.space in pressed

        if space:
            self._linear = 0.0
            self._angular = 0.0
        else:
            if up:
                self._linear = _clamp(self._linear + self._linear_step, self._max_linear)
            elif down:
                self._linear = _clamp(self._linear - self._linear_step, self._max_linear)
            else:
                self._linear = _decay(self._linear, self._linear_decay)

            if left:
                self._angular = _clamp(self._angular + self._angular_step, self._max_angular)
            elif right:
                self._angular = _clamp(self._angular - self._angular_step, self._max_angular)
            else:
                self._angular = _decay(self._angular, self._angular_decay)

        msg = Twist()
        msg.linear.x = self._linear
        msg.angular.z = self._angular
        self._pub.publish(msg)

        # Acil durus durumu her tik'te YENIDEN yayinlanir (tek seferlik
        # mesaj degil) - boylece manual_drive_node gec baslarsa veya bir
        # mesaj kaybolursa bile kilit durumu kisa surede yeniden iletilir.
        self._estop_pub.publish(Bool(data=self._estop))

    def destroy_node(self) -> bool:
        self._listener.stop()
        self._pub.publish(Twist())           # guvenlik: kapanirken sifir komut
        self._estop_pub.publish(Bool(data=True))  # ve kilitli birak
        return super().destroy_node()


def _clamp(value: float, limit: float) -> float:
    return max(-limit, min(limit, value))


def _decay(value: float, step: float) -> float:
    if abs(value) <= step:
        return 0.0
    return value - step if value > 0 else value + step


def main(args=None):
    rclpy.init(args=args)
    node = GlobalKeyboardTeleopNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
