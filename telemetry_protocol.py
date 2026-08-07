import struct
from dataclasses import dataclass

# Must match telemetry_protocol.h exactly.
PROTOCOL_VERSION = 1

# Format string for struct.unpack, this MUST mirror the C struct exactly, in the same order,
# with #pragma pack(1) meaning
# no padding (hence '<' for little-endian, no alignment padding)

#   B = uint8, I = uint32, H = uint16, f = float (4 bytes)

PACKET_FORMAT = "<BIHfffffffB"
PACKET_SIZE = struct.calcsize(PACKET_FORMAT)  # should be 36 bytes


@dataclass
class TelemetryPacket:
    protocol_version: int
    timestamp_ms: int
    packet_id: int
    latitude: float
    longitude: float
    gps_altitude_m: float
    baro_altitude_m: float
    velocity_mps: float
    battery_voltage: float
    acceleration_z: float
    status_flags: int

    @property
    def armed(self) -> bool:
        return bool(self.status_flags & 0b0001)

    @property
    def launched(self) -> bool:
        return bool(self.status_flags & 0b0010)

    @property
    def apogee_detected(self) -> bool:
        return bool(self.status_flags & 0b0100)

    @property
    def landed(self) -> bool:
        return bool(self.status_flags & 0b1000)


def decode_packet(raw_bytes: bytes) -> TelemetryPacket:
    if len(raw_bytes) != PACKET_SIZE:
        raise ValueError(
            f"Expected {PACKET_SIZE} bytes, got {len(raw_bytes)}"
        )
    fields = struct.unpack(PACKET_FORMAT, raw_bytes)
    return TelemetryPacket(*fields)