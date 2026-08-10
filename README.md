# telemetry-protocol

Binary wire format for rocket flight telemetry sent from a flight computer
to a ground station over LoRa. The format is defined once as a packed C
struct ([telemetry_protocol.h](telemetry_protocol.h)) and mirrored by a
Python decoder ([telemetry_protocol.py](telemetry_protocol.py)) for the
ground station, with tests ([test_telemetry_protocol.py](test_telemetry_protocol.py))
that pin the two representations together.

There's no encoder in python, so the ground station only ever decodes.

## Packet layout

36 bytes, little-endian, no padding (`#pragma pack(1)` in C / `<` prefix in
Python's `struct` format). Field order matters and must match exactly on
both ends.

| Offset | Bytes | Field               | C type     | Python (`struct`) | Notes                                    |
|-------:|------:|----------------------|------------|--------------------|-------------------------------------------|
| 0      | 1     | `protocol_version`    | `uint8_t`  | `B`                | always `TELEMETRY_PROTOCOL_VERSION`       |
| 1      | 4     | `timestamp_ms`        | `uint32_t` | `I`                | ms since boot                             |
| 5      | 2     | `packet_id`           | `uint16_t` | `H`                | increments per send, wraps at 65535       |
| 7      | 4     | `latitude`             | `float`    | `f`                | degrees                                   |
| 11     | 4     | `longitude`            | `float`    | `f`                | degrees                                   |
| 15     | 4     | `gps_altitude_m`       | `float`    | `f`                | meters                                    |
| 19     | 4     | `baro_altitude_m`      | `float`    | `f`                | meters                                    |
| 23     | 4     | `velocity_mps`         | `float`    | `f`                | meters/second                             |
| 27     | 4     | `battery_voltage`      | `float`    | `f`                | volts                                     |
| 31     | 4     | `acceleration_z`       | `float`    | `f`                | m/s², vertical axis                       |
| 35     | 1     | `status_flags`         | `uint8_t`  | `B`                | bitfield, see below                       |

Total: **36 bytes** (`1+4+2+4+4+4+4+4+4+4+1`), given by
`PACKET_SIZE` in Python and `TELEMETRY_PACKET_SIZE` in C.

### `status_flags` bits

| Bit | Meaning         | Python property     |
|----:|-----------------|----------------------|
| 0   | armed            | `.armed`             |
| 1   | launched         | `.launched`           |
| 2   | apogee detected  | `.apogee_detected`    |
| 3   | landed           | `.landed`             |

## Versioning

`PROTOCOL_VERSION` (Python) and `TELEMETRY_PROTOCOL_VERSION` (C) must match.
Bump both together whenever the struct layout changes: field
add/remove/reorder, type width changes, etc... so the flight computer and
ground station can detect a mismatch instead of silently misparsing bytes.

## Usage (ground station / Python)

```python
from telemetry_protocol import decode_packet

raw = radio.read(36)  # however you're pulling bytes off the LoRa link
packet = decode_packet(raw)

print(packet.latitude, packet.longitude, packet.gps_altitude_m)
if packet.apogee_detected:
    print("apogee!")
```

`decode_packet` raises `ValueError` if `raw_bytes` isn't exactly
`PACKET_SIZE` (36) bytes.

## Usage (flight computer / C)

```c
#include "telemetry_protocol.h"

TelemetryPacket pkt = {
    .protocol_version = TELEMETRY_PROTOCOL_VERSION,
    .timestamp_ms = millis(),
    .packet_id = next_packet_id++,
    .latitude = gps.lat,
    .longitude = gps.lon,
    .gps_altitude_m = gps.altitude,
    .baro_altitude_m = baro.altitude,
    .velocity_mps = velocity,
    .battery_voltage = read_battery(),
    .acceleration_z = imu.accel_z,
    .status_flags = flags,
};

radio_send((uint8_t *)&pkt, TELEMETRY_PACKET_SIZE);
```

## Tests

The test suite checks that the Python side's byte layout, size, and field
order actually match `telemetry_protocol.h`: packet size, endianness,
field count, round-trip decoding, status-flag bits, and boundary/error
cases (wrong length, empty input, max values).

```sh
python -m unittest test_telemetry_protocol.py -v   # verbose
python test_telemetry_protocol.py                  # dots only
```

## Files

| File                          | Purpose                                             |
|--------------------------------|------------------------------------------------------|
| `telemetry_protocol.h`         | Canonical struct definition (flight computer, C)      |
| `telemetry_protocol.py`        | Decoder mirroring the struct (ground station, Python) |
| `test_telemetry_protocol.py`   | Tests pinning the Python decoder to the C layout       |
