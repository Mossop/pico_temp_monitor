import time
import board
import microcontroller
from busio import I2C
from supervisor import runtime
from adafruit_htu31d import HTU31D
from adafruit_htu21d import HTU21D

from .measurements import Measurement, TAGS, upload, build_tags
from .net import connect, update_time
from .log import Logger

log = Logger("MAIN")


def sleep_s(timeout):
    time.sleep(timeout)


class Main:
    MEASUREMENT_INTERVAL = 60

    BASE_TICKS = time.monotonic()

    def __init__(self):
        self.measurements = []
        self.failures = 0

        with log.safe("Failed to initialise htu31d"):
            i2c = I2C(board.GP9, board.GP8)
            self.htu31d = HTU31D(i2c)
            self.htu31d.humidity_resolution = "0.014%"
            self.htu31d.temp_resolution = "0.012"

        with log.safe("Failed to initialise htu21d"):
            i2c = I2C(board.GP7, board.GP6)
            self.htu21d = HTU21D(i2c)
            self.htu21d.temp_rh_resolution = 0

    def measurement(self):
        with log.safe("Failed to take measurements from htu31d"):
            try:
                reading = Measurement("htu31d")
                reading.tag("serial", str(self.htu31d.serial_number))
                temp, humidity = self.htu31d.measurements
                reading.value("temperature", temp)
                reading.value("relative_humidity", humidity)

                self.measurements.append(reading)
            except:
                self.failures = self.failures + 1
                raise

        with log.safe("Failed to take measurements from htu21d"):
            try:
                reading = Measurement("htu21d")
                reading.value("temperature", self.htu21d.temperature)
                reading.value("relative_humidity", self.htu21d.relative_humidity)

                self.measurements.append(reading)
            except:
                self.failures = self.failures + 1
                raise

    def monitor(self):
        with log.safe("Failed to monitor"):
            reading = Measurement("pico_state")
            reading.value("ticks", int(time.monotonic() - self.BASE_TICKS))
            reading.value("freq", microcontroller.cpu.frequency)
            reading.value("cpu_temp", microcontroller.cpu.temperature)
            reading.value("voltage", microcontroller.cpu.voltage)
            reading.value("usb", 1 if runtime.usb_connected else 0)
            reading.value("serial", 1 if runtime.serial_connected else 0)
            reading.value("pending", len(self.measurements))
            reading.value("failures", self.failures)
            # reading.value("reset_cause", microcontroller.cpu.reset_reason)

            self.measurements.append(reading)

    def submit(self):
        log.trace("Sending %d measurements" % (len(self.measurements)))
        with connect() as network:
            try:
                update_time(network)
            except Exception:
                pass

            upload(self.measurements, network)

    def main_loop(self):
        log.info("Starting main loop")

        while True:
            last_measures = time.monotonic()
            self.monitor()
            self.measurement()

            with log.safe("Failed to report measurements"):
                self.failures = self.failures + 1
                self.submit()
                self.measurements = []
                self.failures = 0

            delay = (last_measures + self.MEASUREMENT_INTERVAL) - time.monotonic()
            if delay > 0:
                sleep_s(delay)

    def set_time(self):
        attempts = 1
        while attempts > 0:
            with log.safe("Failed to connect"):
                with connect(timeout = 60) as network:
                    with log.safe("Failed to update time"):
                        update_time(network, 3)
                        return

            sleep_s(2)
            attempts -= 1

        log.error("Failed to complete initial connection")
        raise Exception("Failed to complete initial connection")


    def run(self):
        print("Startup. Measurement timeout %d" % (self.MEASUREMENT_INTERVAL))

        # Make sure we get an accurate time before running the loop
        try:
            self.set_time()
        except Exception:
            # Failed to get the time, try rebooting in case there is a hardware issue
            # machine.reset()
            return

        build_tags()
        print("Tags:")
        for k in TAGS.keys():
            print("  %s: %s" % (k, TAGS[k]))
        print()

        self.main_loop()

def main():
    main = Main()
    main.run()
