#!/usr/bin/env python3
"""Ok tuslu (yon tuslari) manuel surus teleop node'u.

ONEMLI KISIT: Standart bir terminalde (X11 klavye tekrari) AYNI ANDA yalnizca
TEK bir tusun "basili tutma" sinyali uretilir - ikinci bir tusa basildiginda
isletim sistemi ilk tusun tekrarini durdurup ikinciye gecer. Yani "iki tusu
ayni anda basili tutmak" duz klavyeyle guvenilir sekilde algilanamaz (bu bir
donanim/OS siniri, kod hatasi degil).

Bu yuzden GAZ (ileri/geri) ve DIREKSIYON (sol/sag) FARKLI mantiklarla
calisir:
  - Gaz (Yukari/Asagi ok): gercek bir arabanin gaz pedali gibi KALICI'dir.
    Yukari ok hizi arttirir ve o hiz SADECE Asagi ok (frenle/azalt) veya
    BOSLUK (tam dur) ile degisir - sirf baska bir tusa gecince KAYBOLMAZ.
    Bu sayede ileri giderken direksiyon tusuna gecildiginde (klavye artik
    yukari ok tekrarini DURDURMUS olsa bile) hiz kaybolmaz.
  - Direksiyon (Sol/Sag ok): gercek bir direksiyon simidi gibi ANLIK'tir -
    basili tuttugun surece doner, biraktiginda (release_timeout icinde yeni
    tekrar sinyali gelmezse) kendiliginden duzlenir (0'a yumusakca iner).

Tuslar:
  Yukari ok  : ileri hizlan (kalici)
  Asagi ok   : yavasla / frenle / geri (kalici)
  Sol ok     : sola don (basili tut, birakinca duzlenir)
  Sag ok     : saga don (basili tut, birakinca duzlenir)
  BOSLUK     : aninda TAM dur (hiz + donus sifirlanir, kilitlemez)
  e          : ACIL DURUS - arac KILITLENIR, 'r' basilana kadar hicbir
               /cmd_vel komutu etkili olmaz (manual_drive_node'daki
               /emergency_stop latch mantigi)
  r          : acil durusu sifirla (kilidi ac)
  q          : cikis (guvenlik icin sifir komut + acil durus gonderip cikar)

cmd_vel'e NORMAL/sezgisel isaretle yazar (ileri = pozitif linear.x) - ters
isaret duzeltmesi (bkz. ackermann_sign_convention) manual_drive_node
tarafinda, TEK bir merkezi yerde yapilir.
"""
import select
import sys
import termios
import time
import tty

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool

UP = '\x1b[A'
DOWN = '\x1b[B'
RIGHT = '\x1b[C'
LEFT = '\x1b[D'


class KeyboardTeleopNode(Node):

    def __init__(self):
        super().__init__('keyboard_teleop_node')

        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('emergency_stop_topic', '/emergency_stop')
        self.declare_parameter('linear_step', 0.15)
        self.declare_parameter('angular_step', 0.15)
        self.declare_parameter('linear_decay', 0.12)
        self.declare_parameter('angular_decay', 0.15)
        self.declare_parameter('max_linear_speed', 1.0)
        self.declare_parameter('max_angular_speed', 0.4)
        self.declare_parameter('release_timeout', 0.2)
        self.declare_parameter('publish_rate', 20.0)

        self._topic = self.get_parameter('cmd_vel_topic').value
        self._estop_topic = self.get_parameter('emergency_stop_topic').value
        self._linear_step = self.get_parameter('linear_step').value
        self._angular_step = self.get_parameter('angular_step').value
        self._linear_decay = self.get_parameter('linear_decay').value
        self._angular_decay = self.get_parameter('angular_decay').value
        self._max_linear = self.get_parameter('max_linear_speed').value
        self._max_angular = self.get_parameter('max_angular_speed').value
        self._release_timeout = self.get_parameter('release_timeout').value
        self._rate = self.get_parameter('publish_rate').value

        self._pub = self.create_publisher(Twist, self._topic, 10)
        self._estop_pub = self.create_publisher(Bool, self._estop_topic, 10)
        self._linear = 0.0
        self._angular = 0.0
        self._estop = False

        now = time.monotonic()
        self._last_seen = {UP: -1e9, DOWN: -1e9, LEFT: -1e9, RIGHT: -1e9}
        _ = now

    def run(self) -> None:
        settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
        self.get_logger().info(
            "Klavye teleop hazir | Yon tuslarini BASILI TUT: hareket, "
            "BIRAK: yumusakca durur | BOSLUK: ani dur, q: cikis"
        )
        try:
            period = 1.0 / self._rate
            while rclpy.ok():
                key = self._read_key(timeout=period)
                now = time.monotonic()

                if key == 'q':
                    break
                if key == 'e':
                    self._estop = True
                    self.get_logger().error("ACIL DURUS tetiklendi (klavye: 'e').")
                elif key == 'r':
                    self._estop = False
                    self.get_logger().info("Acil durus sifirlandi (klavye: 'r').")
                if key == ' ':
                    self._linear = 0.0
                    self._angular = 0.0
                elif key in self._last_seen:
                    self._last_seen[key] = now

                up_active = (now - self._last_seen[UP]) < self._release_timeout
                down_active = (now - self._last_seen[DOWN]) < self._release_timeout
                left_active = (now - self._last_seen[LEFT]) < self._release_timeout
                right_active = (now - self._last_seen[RIGHT]) < self._release_timeout

                # Gaz KALICI: baska bir tusa gecilince (X11 tekrarini o tusa
                # kaydirdiginda) ileri hiz KAYBOLMAZ - yalnizca Asagi ok veya
                # BOSLUK degistirir.
                if up_active:
                    self._linear = _clamp(self._linear + self._linear_step, self._max_linear)
                elif down_active:
                    self._linear = _clamp(self._linear - self._linear_step, self._max_linear)

                if left_active:
                    self._angular = _clamp(self._angular + self._angular_step, self._max_angular)
                elif right_active:
                    self._angular = _clamp(self._angular - self._angular_step, self._max_angular)
                else:
                    self._angular = _decay(self._angular, self._angular_decay)

                msg = Twist()
                msg.linear.x = self._linear
                msg.angular.z = self._angular
                self._pub.publish(msg)
                self._estop_pub.publish(Bool(data=self._estop))
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
            self._pub.publish(Twist())           # cikista guvenlik: sifir komut
            self._estop_pub.publish(Bool(data=True))  # ve kilitli birak

    def _read_key(self, timeout: float) -> str:
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if not ready:
            return ''
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            ready, _, _ = select.select([sys.stdin], [], [], 0.05)
            if ready:
                ch += sys.stdin.read(2)
        return ch


def _clamp(value: float, limit: float) -> float:
    return max(-limit, min(limit, value))


def _decay(value: float, step: float) -> float:
    if abs(value) <= step:
        return 0.0
    return value - step if value > 0 else value + step


def main(args=None):
    rclpy.init(args=args)
    node = KeyboardTeleopNode()
    try:
        node.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
