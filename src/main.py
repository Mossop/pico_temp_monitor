import machine
import time

from measurements import serialized, Measurement, TAGS, upload
from net import connect, update_time
from log import Logger

# Theoretically gives the sensor voltage. ADC measures from 0 to 65535 against
# a reference voltage of 3.3V
conversion_factor = 3.3 / 65535

MEASUREMENT_INTERVAL = 60000

WATCHDOG_TIMEOUT = 8000

BASE_TICKS = time.ticks_ms()

SUBMIT_MINIMUM = 1

log = Logger("MAIN")


# wdt = machine.WDT(timeout=WATCHDOG_TIMEOUT)
def feed():
    # wdt.feed()
    pass


def sleep_ms(timeout):
    max_sleep = WATCHDOG_TIMEOUT - 1000

    feed()
    while timeout > max_sleep:
        timeout -= max_sleep
        time.sleep_ms(max_sleep)
        feed()

    time.sleep_ms(timeout)
    feed()


def measurement(measurements):
    for i in range(5):
        with log.safe("Failed to measure adc %d" % i):
            adc = machine.ADC(i)
            raw = adc.read_u16()
            reading = Measurement("pico_adc")
            reading.tag("adc", str(i))
            reading.value("raw", raw)
            reading.value("volts", raw * conversion_factor)

            measurements.append(reading)


def monitor(measurements):
    SIE_STATUS=const(0x50110000 + 0x50)
    CONNECTED=const(1<<16)
    SUSPENDED=const(1<<4)

    with log.safe("Failed to monitor"):
        usb_state = machine.mem32[SIE_STATUS] & (CONNECTED | SUSPENDED)

        reading = Measurement("pico_state")
        reading.value("ticks", (time.ticks_ms() - BASE_TICKS) / 1000)
        reading.value("freq", machine.freq())
        reading.value("reset_cause", machine.reset_cause())

        if usb_state == 0:
            reading.value("usb", 0)
        elif usb_state == SUSPENDED:
            reading.value("usb", 1)
        else:
            reading.value("usb", 2)

        measurements.append(reading)


def submit(measurements):
    log.trace("Sending %d measurements" % (len(measurements)))
    with connect():
        feed()

        try:
            update_time()
        except Exception:
            pass
        feed()

        upload(measurements)


def main_loop():
    feed()

    measurements = []

    log.info("Starting main loop")

    while True:
        last_measures = time.ticks_ms()
        measurement(measurements)
        monitor(measurements)

        with log.safe("Failed to report measurements"):
            if len(measurements) >= SUBMIT_MINIMUM:
                submit(measurements)
                measurements = []

        delay = (last_measures + MEASUREMENT_INTERVAL) - time.ticks_ms()
        if delay > 0:
            sleep_ms(delay)


def set_time():
    attempts = 1
    while attempts > 0:
        feed()

        with log.safe("Failed to connect"):
            with connect(timeout = 60):
                feed()

                with log.safe("Failed to update time"):
                    update_time(3)
                    return

        sleep_ms(2000)
        attempts -= 1

    log.error("Failed to complete initial connection")
    raise Exception("Failed to complete initial connection")


def main():
    print("Startup. Watchdog timeout %d. Measurement timeout %d" % (WATCHDOG_TIMEOUT, MEASUREMENT_INTERVAL))
    print("Tags:")
    for k in TAGS.keys():
        print("  %s: %s" % (k, TAGS[k]))
    print()

    # Make sure we get an accurate time before running the loop
    try:
        set_time()
    except Exception:
        # Failed to get the time, try rebooting in case there is a hardware issue
        # machine.reset()
        return

    main_loop()


main()
