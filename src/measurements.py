import time
import network
import urequests

from machine import RTC, unique_id
from config import CONFIG
from log import Logger


log = Logger("MEASURE")

TAGS = {}


def build_tags():
    import os
    import binascii
    machine_parts = os.uname().machine.split(" with ")

    wlan = network.WLAN(network.STA_IF)
    mac =  binascii.hexlify(wlan.config("mac")).decode()
    TAGS["machine_id"] = binascii.hexlify(unique_id()).decode()
    TAGS["device"] = machine_parts[0]
    TAGS["chip"] = machine_parts[1] if len(machine_parts) > 1 else "unknown"
    TAGS["mac"] = ":".join([mac[i:i+2] for i in range(0, len(mac), 2)])


URL = "https://%s/api/v2/write?bucket=%s&org=%s&precision=s" % (CONFIG.host, CONFIG.bucket, CONFIG.organisation)


def escape(st: str) -> str:
    return st.replace(' ', "\\ ").replace(',', "\\,")


class Serialized:
    def __init__(self, measurements):
        self.measurements = measurements

    def __iter__(self):
        for measurement in self.measurements:
            yield str(measurement).encode()

def serialized(measurements):
    # return Serialized(measurements)
    return "".join([str(m) for m in measurements])


class Measurement:
    def __init__(self, id: str, timestamp = None):
        self.tags = dict(TAGS)
        self.fields = dict()
        self.id = id
        if timestamp is None:
            self.timestamp = time.time()
        else:
            self.timestamp = timestamp

    def tag(self, key: str, value: str):
        self.tags[key] = value

    def value(self, key: str, value):
        self.fields[key] = value

    def __str__(self) -> str:
        tags = ["%s=%s" % (escape(k), escape(v)) for (k, v) in self.tags.items()]
        tags.insert(0, self.id)
        fields = ["%s=%s" % (escape(k), v) for (k, v) in self.fields.items()]
        return "%s %s %s\n" % (",".join(tags), ",".join(fields), self.timestamp)


def upload(measurements):
    data = serialized(measurements)

    log.trace("Upload")
    response = urequests.post(URL, data=data, headers={
        "Authorization": "Token %s" % CONFIG.token
    })

    response.close()

    if response.status_code < 200 or response.status_code >= 300:
        raise Exception("Failed to upload data: %d %s\n%s" % (response.status_code, response.reason, response.text))
