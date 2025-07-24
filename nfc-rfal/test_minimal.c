#include <stdio.h>
#include "platform_pi5.h"
#include "rfal_analogConfig.h"

// Test our custom analog config symbols
extern const uint8_t rfalAnalogConfigCustomSettings[];
extern const uint16_t rfalAnalogConfigCustomSettingsLength;

int main() {
    printf("RFAL Minimal Compilation Test\n");
    
    // Test platform init
    if (platformInit() == 0) {
        printf("✓ Platform initialized successfully\n");
        
        // Test accessing custom analog config
        printf("✓ Custom analog config accessible at %p (length: %u)\n", 
               (void*)rfalAnalogConfigCustomSettings, rfalAnalogConfigCustomSettingsLength);
        
        platformDeinit();
        printf("✓ Test completed successfully\n");
        return 0;
    } else {
        printf("✗ Platform initialization failed\n");
        return 1;
    }
}