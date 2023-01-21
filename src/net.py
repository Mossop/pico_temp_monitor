import time
import wifi
from socketpool import SocketPool
from rtc import RTC
from adafruit_ntp import NTP
from adafruit_requests import Session
import ssl

from .log import Logger
from .config import CONFIG


log = Logger("NET")


class Network:
    def __init__(self, timeout):
        self.timeout = timeout

    def __enter__(self):
        now = time.monotonic()
        end = now + self.timeout

        wifi.radio.enabled = True
        while True:
            try:
                wifi.radio.connect(CONFIG.ssid, CONFIG.password, timeout=(end - now))
                log.trace("Connected")
                self.socket_pool = SocketPool(wifi.radio)
                self.session = Session(self.socket_pool, ssl.create_default_context())
                return self
            except Exception as ex:
                now = time.monotonic()
                if now >= end:
                    raise ex

    def __exit__(self, ex_type, ex, tb):
        wifi.radio.stop_station()
        wifi.radio.enabled = False
        log.trace("Disconnected")


def connect(timeout = 20):
    return Network(timeout)


def update_time(network, attempts = 1):
    rtc = RTC()
    ntp = NTP(network.socket_pool, tz_offset=0)

    while attempts > 0:
        with log.safe("Failed to update time"):
            rtc.datetime = ntp.datetime
            log.trace("Time updated")
            return

        attempts -= 1
        time.sleep_ms(1000)

    raise Exception("Failed to update time in the required number of attempts")
