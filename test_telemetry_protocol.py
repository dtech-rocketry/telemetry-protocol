# to run with verbose:
# python -m unittest test_telemetry_protocol.py -v

# just dots:
# python test_telemetry_protocol.py

# These tests check that the Python's byte layout, size, and field
# order actually match telemetry_protocol.h 


# PACKET_FORMAT is hand-kept in sync with the C struct

import struct
import unittest

from telemetry_protocol import (
    PACKET_FORMAT,
    PACKET_SIZE,
    PROTOCOL_VERSION,
    TelemetryPacket,
    decode_packet,
)

# A representative set of field values, in the same order as the C
# struct / PACKET_FORMAT: version, timestamp_ms, packet_id, latitude,
# longitude, gps_altitude_m, baro_altitude_m, velocity_mps,
# battery_voltage, acceleration_z, status_flags
SAMPLE_VALUES = (
    PROTOCOL_VERSION,
    123_456,
    42,
    38.897957,
    -77.036560,
    152.3,
    150.1,
    12.5,
    7.4,
    -9.81,
    0b0000,
)


def pack_sample(**overrides):
    """Pack SAMPLE_VALUES into raw bytes, with optional field overrides."""
    fields = dict(zip(
        [
            "protocol_version", "timestamp_ms", "packet_id",
            "latitude", "longitude", "gps_altitude_m", "baro_altitude_m",
            "velocity_mps", "battery_voltage", "acceleration_z",
            "status_flags",
        ],
        SAMPLE_VALUES,
    ))
    fields.update(overrides)
    ordered = [
        fields["protocol_version"], fields["timestamp_ms"], fields["packet_id"],
        fields["latitude"], fields["longitude"], fields["gps_altitude_m"],
        fields["baro_altitude_m"], fields["velocity_mps"], fields["battery_voltage"],
        fields["acceleration_z"], fields["status_flags"],
    ]
    return struct.pack(PACKET_FORMAT, *ordered)


class PacketSizeTests(unittest.TestCase):
    def test_packet_size_is_36_bytes(self):
        # Matches the comment in telemetry_protocol.h:
        # 1+4+2+4+4+4+4+4+4+4+1 = 36 bytes
        self.assertEqual(PACKET_SIZE, 36)

    def test_format_string_is_little_endian_no_padding(self):
        # '<' enforces no alignment padding, matching #pragma pack(1).
        self.assertTrue(PACKET_FORMAT.startswith("<"))

    def test_format_field_count_matches_struct_fields(self):
        # 11 fields in TelemetryPacket / the C struct.
        num_fields = len(TelemetryPacket.__dataclass_fields__)
        # '<' plus one type char per field.
        self.assertEqual(len(PACKET_FORMAT), 1 + num_fields)


class DecodePacketTests(unittest.TestCase):
    def test_round_trip_decodes_expected_values(self):
        raw = pack_sample()
        packet = decode_packet(raw)

        self.assertEqual(packet.protocol_version, PROTOCOL_VERSION)
        self.assertEqual(packet.timestamp_ms, 123_456)
        self.assertEqual(packet.packet_id, 42)
        self.assertAlmostEqual(packet.latitude, 38.897957, places=3)
        self.assertAlmostEqual(packet.longitude, -77.036560, places=3)
        self.assertAlmostEqual(packet.gps_altitude_m, 152.3, places=1)
        self.assertAlmostEqual(packet.baro_altitude_m, 150.1, places=1)
        self.assertAlmostEqual(packet.velocity_mps, 12.5, places=1)
        self.assertAlmostEqual(packet.battery_voltage, 7.4, places=1)
        self.assertAlmostEqual(packet.acceleration_z, -9.81, places=2)
        self.assertEqual(packet.status_flags, 0)

    def test_field_order_matches_c_struct(self):
        # If timestamp_ms and packet_id were swapped (both integer
        # types), this catches it: packet_id (H) must stay 16-bit /
        # 0-65535, timestamp_ms (I) is 32-bit and can exceed that.
        raw = pack_sample(timestamp_ms=1_000_000, packet_id=65_535)
        packet = decode_packet(raw)
        self.assertEqual(packet.timestamp_ms, 1_000_000)
        self.assertEqual(packet.packet_id, 65_535)

    def test_wrong_length_raises_value_error(self):
        with self.assertRaises(ValueError):
            decode_packet(b"\x00" * (PACKET_SIZE - 1))

        with self.assertRaises(ValueError):
            decode_packet(b"\x00" * (PACKET_SIZE + 1))

    def test_empty_bytes_raises_value_error(self):
        with self.assertRaises(ValueError):
            decode_packet(b"")


class StatusFlagsTests(unittest.TestCase):
    def _packet_with_flags(self, flags):
        return decode_packet(pack_sample(status_flags=flags))

    def test_no_flags_set(self):
        p = self._packet_with_flags(0b0000)
        self.assertFalse(p.armed)
        self.assertFalse(p.launched)
        self.assertFalse(p.apogee_detected)
        self.assertFalse(p.landed)

    def test_armed_bit(self):
        p = self._packet_with_flags(0b0001)
        self.assertTrue(p.armed)
        self.assertFalse(p.launched)
        self.assertFalse(p.apogee_detected)
        self.assertFalse(p.landed)

    def test_launched_bit(self):
        p = self._packet_with_flags(0b0010)
        self.assertFalse(p.armed)
        self.assertTrue(p.launched)

    def test_apogee_bit(self):
        p = self._packet_with_flags(0b0100)
        self.assertTrue(p.apogee_detected)

    def test_landed_bit(self):
        p = self._packet_with_flags(0b1000)
        self.assertTrue(p.landed)

    def test_all_flags_set(self):
        p = self._packet_with_flags(0b1111)
        self.assertTrue(p.armed)
        self.assertTrue(p.launched)
        self.assertTrue(p.apogee_detected)
        self.assertTrue(p.landed)

    def test_flags_are_independent_bits(self):
        # armed + apogee, without launched/landed, shouldn't cross-trigger.
        p = self._packet_with_flags(0b0101)
        self.assertTrue(p.armed)
        self.assertFalse(p.launched)
        self.assertTrue(p.apogee_detected)
        self.assertFalse(p.landed)


class BoundaryValueTests(unittest.TestCase):
    def test_max_uint8_protocol_version(self):
        raw = pack_sample(protocol_version=255)
        self.assertEqual(decode_packet(raw).protocol_version, 255)

    def test_max_uint32_timestamp(self):
        raw = pack_sample(timestamp_ms=0xFFFFFFFF)
        self.assertEqual(decode_packet(raw).timestamp_ms, 0xFFFFFFFF)

    def test_max_uint16_packet_id_wraps_in_c_but_not_in_python(self):
        # packet_id "wraps at 65535" on the firmware side; the Python
        # decoder just reports whatever 16-bit value it's given.
        raw = pack_sample(packet_id=65_535)
        self.assertEqual(decode_packet(raw).packet_id, 65_535)

    def test_negative_latitude_longitude(self):
        raw = pack_sample(latitude=-38.897957, longitude=-77.036560)
        packet = decode_packet(raw)
        self.assertLess(packet.latitude, 0)
        self.assertLess(packet.longitude, 0)


if __name__ == "__main__":
    unittest.main()
