/*
 * Simple analog configuration replacement
 * Bypasses the complex RFAL analog config table
 */

#include <stdint.h>

// Custom analog configuration - minimal table
// This replaces the complex RFAL table with a simple version

const uint8_t rfalAnalogConfigCustomSettings[] = {
    // Minimal configuration - just end marker
    0x00, 0x00, 0x00
};

const uint16_t rfalAnalogConfigCustomSettingsLength = sizeof(rfalAnalogConfigCustomSettings);