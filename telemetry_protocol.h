#ifndef TELEMETRY_PROTOCOL_H
#define TELEMETRY_PROTOCOL_H

#include <stdint.h>

// version this WHENEVER the struct layout changes.
// ground station and flight computer must agree on this number.
#define TELEMETRY_PROTOCOL_VERSION 1

// #pragma pack(1) removes padding between fields so the struct's
// in-memory layout is EXACTLY the byte layout sent over LoRa.
// without this, the compiler may insert padding and the two ends
// will disagree on where each field starts.
#pragma pack(push, 1)
typedef struct {
    uint8_t  protocol_version;   // always TELEMETRY_PROTOCOL_VERSION
    uint32_t timestamp_ms;       // ms since boot
    uint16_t packet_id;          // increments each send, wraps at 65535
    float    latitude;           // degrees
    float    longitude;          // degrees
    float    gps_altitude_m;     // meters
    float    baro_altitude_m;    // meters
    float    velocity_mps;       // meters/second
    float    battery_voltage;    // volts
    float    acceleration_z;     // m/s^2, vertical axis
    uint8_t  status_flags;       // bit 0: armed, bit 1: launched,
                                 // bit 2: apogee, bit 3: landed
} TelemetryPacket;
#pragma pack(pop)

// Total size in bytes, check this matches on both ends.
// (1+4+2+4+4+4+4+4+4+4+1 = 36 bytes)
#define TELEMETRY_PACKET_SIZE sizeof(TelemetryPacket)

#endif