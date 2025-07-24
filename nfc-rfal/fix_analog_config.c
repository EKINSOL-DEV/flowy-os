/*
 * Fix for missing rfalAnalogConfigDefaultSettings
 * This file provides the missing symbol by including the table directly
 */

// Force inclusion of the analog config table
#undef RFAL_ANALOG_CONFIG_CUSTOM
#include "rfal_analogConfigTbl.h"

// Verify the symbol is available (this will fail compilation if it's not)
const uint8_t* verify_analog_config_available(void) {
    return rfalAnalogConfigDefaultSettings;
}