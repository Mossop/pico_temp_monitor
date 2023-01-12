import network
import ntptime
import time

from log import Logger
from config import CONFIG


log = Logger("NET")


class Network:
    def __init__(self, timeout):
        self.timeout = timeout


    def __enter__(self):
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.wlan.connect(CONFIG.ssid, CONFIG.password)

        while self.timeout != 0 and self.wlan.status() < 3:
            self.timeout -= 1
            time.sleep_ms(1000)

        if self.wlan.status() < 3:
            raise Exception("Failed to connect, status %d" % self.wlan.status())

        log.trace("Connected")

    def __exit__(self, ex_type, ex, tb):
        self.wlan.disconnect()
        self.wlan.active(False)
        log.trace("Disconnected")


def connect(timeout = 20):
    return Network(timeout)


def update_time(attempts = 1):
    while attempts > 0:
        with log.safe("Failed to update time"):
            ntptime.settime()
            log.trace("Time updated")
            return

        attempts -= 1
        time.sleep_ms(1000)

    raise Exception("Failed to update time in the required number of attempts")
