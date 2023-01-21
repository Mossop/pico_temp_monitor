import time
import board
import microcontroller
from busio import I2C
from supervisor import runtime
from adafruit_htu31d import HTU31D

from .measurements import Measurement, TAGS, upload, build_tags
from .net import connect, update_time
from .log import Logger

MEASUREMENT_INTERVAL = 60

BASE_TICKS = time.monotonic()

SUBMIT_MINIMUM = 1

log = Logger("MAIN")

def sleep_s(timeout):
    time.sleep(timeout)


def measurement(measurements):
    with log.safe("Failed to take measurements"):
        with I2C(board.GP9, board.GP8) as i2c:
            ht = HTU31D(i2c)
            ht.humidity_resolution = "0.014%"
            ht.temp_resolution = "0.012"
            temp, humidity = ht.measurements
            reading = Measurement("htu31d")
            reading.value("temp", temp)
            reading.value("humidity", humidity)

            measurements.append(reading)


def monitor(measurements):
    with log.safe("Failed to monitor"):
        reading = Measurement("pico_state")
        reading.value("ticks", int(time.monotonic() - BASE_TICKS))
        reading.value("freq", microcontroller.cpu.frequency)
        reading.value("cpu_temp", microcontroller.cpu.temperature)
        reading.value("voltage", microcontroller.cpu.voltage)
        reading.value("usb", 1 if runtime.usb_connected else 0)
        reading.value("serial", 1 if runtime.serial_connected else 0)
        # reading.value("reset_cause", microcontroller.cpu.reset_reason)

        measurements.append(reading)


def submit(measurements):
    log.trace("Sending %d measurements" % (len(measurements)))
    with connect() as network:
        try:
            update_time(network)
        except Exception:
            pass

        upload(measurements, network)


def main_loop():
    measurements = []

    log.info("Starting main loop")

    while True:
        last_measures = time.monotonic()
        measurement(measurements)
        monitor(measurements)

        with log.safe("Failed to report measurements"):
            if len(measurements) >= SUBMIT_MINIMUM:
                submit(measurements)
                measurements = []

        delay = (last_measures + MEASUREMENT_INTERVAL) - time.monotonic()
        if delay > 0:
            sleep_s(delay)


def set_time():
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


def main():
    print("Startup. Measurement timeout %d" % (MEASUREMENT_INTERVAL))

    # Make sure we get an accurate time before running the loop
    try:
        set_time()
    except Exception:
        # Failed to get the time, try rebooting in case there is a hardware issue
        # machine.reset()
        return

    build_tags()
    print("Tags:")
    for k in TAGS.keys():
        print("  %s: %s" % (k, TAGS[k]))
    print()

    main_loop()
