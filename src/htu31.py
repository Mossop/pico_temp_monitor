from machine import I2C, Pin
import time
import struct

class HTU31:
    def __init__(self, i2c = I2C(0, scl=Pin(9), sda=Pin(8)), address = 0x40):
        self._i2c = i2c
        self._address = address
        self.reset()

    def reset(self):
        self._i2c.writeto(self._address, b'0x1E')
        time.sleep(0.015)

    def _write(self, buf):
        self._i2c.writeto(self._address, buf)

    def _write_then_read(self, buf, len):
        self._i2c.writeto(self._address, buf, False)
        return self._i2c.readfrom(self._address, len)

    @staticmethod
    def _crc(value) -> int:
        polynom = 0x988000  # x^8 + x^5 + x^4 + 1
        msb = 0x800000
        mask = 0xFF8000
        result = value << 8  # Pad with zeros as specified in spec

        while msb != 0x80:
            # Check if msb of current value is 1 and apply XOR mask
            if result & msb:
                result = ((result ^ polynom) & mask) | (result & ~mask)
            # Shift by one
            msb >>= 1
            mask >>= 1
            polynom >>= 1

        return result

    @property
    def serial_number(self) -> int:
        """The unique 32-bit serial number"""
        buf = self._write_then_read(b'0x0A', 4)
        return struct.unpack(">I", buf)[0]

    @property
    def measurements(self):
        temperature = None
        humidity = None

        self._write(b'0x40')

        # wait conversion time
        time.sleep(0.02)

        buf = self._write_then_read(b'0x00', 6)

        # separate the read data
        return struct.unpack_from(">HBHB", buf)

        # # check CRC of bytes
        # if temp_crc != self._crc(temperature) or humidity_crc != self._crc(humidity):
        #     raise RuntimeError("Invalid CRC calculated")

        # # decode data into human values:
        # # convert bytes into 16-bit signed integer
        # # convert the LSB value to a human value according to the datasheet
        # temperature = -40.0 + 165.0 * temperature / 65535.0

        # # repeat above steps for humidity data
        # humidity = 100 * humidity / 65535.0
        # humidity = max(min(humidity, 100), 0)

        # return (temperature, humidity)

