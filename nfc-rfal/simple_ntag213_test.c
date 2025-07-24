/*
 * Simple NTAG213 Detection using RFAL NFC-A API
 * This uses the basic RFAL NFC-A functions to detect NTAG213 tags
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include "platform_pi5.h"
#include "rfal_nfca.h"
#include "rfal_utils.h"
#include "rfal_rf.h"

int main() {
    printf("Simple RFAL NTAG213 Detection Test\n");
    printf("==================================\n");
    
    // Initialize platform
    printf("1. Initializing platform...\n");
    if (platformInit() != 0) {
        printf("✗ Platform initialization failed\n");
        return 1;
    }
    printf("✓ Platform initialized\n");
    
    // Initialize RFAL RF layer
    printf("2. Initializing RFAL RF layer...\n");
    if (rfalInitialize() != RFAL_ERR_NONE) {
        printf("✗ RFAL RF initialization failed\n");
        platformDeinit();
        return 1;
    }
    printf("✓ RFAL RF initialized\n");
    
    // Set field to NFC-A
    printf("3. Configuring for NFC-A...\n");
    if (rfalSetMode(RFAL_MODE_POLL_NFCA, RFAL_BR_106, RFAL_BR_106) != RFAL_ERR_NONE) {
        printf("✗ Failed to set NFC-A mode\n");
        rfalDeinitialize();
        platformDeinit();
        return 1;
    }
    printf("✓ NFC-A mode configured\n");
    
    // Turn on RF field
    printf("4. Turning on RF field...\n");
    if (rfalFieldOnAndStartGT() != RFAL_ERR_NONE) {
        printf("✗ Failed to turn on RF field\n");
        rfalDeinitialize();
        platformDeinit();
        return 1;
    }
    printf("✓ RF field is ON\n");
    
    // Wait for field to stabilize
    platformDelay(10);
    
    // Perform NFC-A detection
    printf("5. Scanning for NTAG213 tags...\n");
    printf("   Place your NTAG213 tag near the reader\n");
    
    for (int attempt = 0; attempt < 50; attempt++) {
        rfalNfcaSensRes sensRes;
        
        // Send REQA and wait for ATQA
        ReturnCode ret = rfalNfcaPollerCheckPresence(RFAL_14443A_SHORTFRAME_CMD_REQA, &sensRes);
        
        if (ret == RFAL_ERR_NONE) {
            printf("✓ NFC-A tag detected!\n");
            
            // Check if it's NTAG213-compatible
            uint16_t atqa = ((uint16_t)sensRes.anticollisionInfo << 8) | sensRes.platformInfo;
            printf("   ATQA: 0x%04X\n", atqa);
            
            if (atqa == 0x0044) {
                printf("✓ ATQA matches NTAG213 specification!\n");
                
                // Perform anticollision to get UID
                uint8_t uid[10];  // Max UID length
                uint8_t uidLen;
                rfalNfcaSelRes selRes;
                bool collPending;
                
                ret = rfalNfcaPollerSingleCollisionResolution(1, &collPending, &selRes, uid, &uidLen);
                
                if (ret == RFAL_ERR_NONE) {
                    printf("✓ UID retrieved successfully!\n");
                    printf("   UID Length: %d bytes\n", uidLen);
                    printf("   UID: ");
                    for (int i = 0; i < uidLen; i++) {
                        printf("%02X ", uid[i]);
                    }
                    printf("\n");
                    printf("   SAK: 0x%02X\n", selRes.sak);
                    
                    if (!collPending) {
                        printf("✓ No collision detected\n");
                    }
                    
                    printf("\n🎉 SUCCESS: NTAG213 communication working with RFAL!\n");
                    break;
                } else {
                    printf("⚠ UID retrieval failed (ret: %d)\n", ret);
                }
            } else {
                printf("⚠ Tag detected but ATQA doesn't match NTAG213\n");
            }
        }
        
        // Brief delay between attempts
        platformDelay(100);
    }
    
    // Cleanup
    printf("\n6. Cleaning up...\n");
    rfalFieldOff();
    rfalDeinitialize();
    platformDeinit();
    printf("✓ Cleanup completed\n");
    
    return 0;
}