/*
 * NTAG213 Detection using RFAL Library
 * This program uses the compiled RFAL library to detect and communicate with NTAG213 tags
 */

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include "platform_pi5.h"
#include "rfal_nfc.h"
#include "rfal_nfca.h"
#include "rfal_utils.h"

int main() {
    printf("RFAL NTAG213 Detection Test\n");
    printf("==========================\n");
    
    // Initialize platform
    printf("1. Initializing platform...\n");
    if (platformInit() != 0) {
        printf("✗ Platform initialization failed\n");
        return 1;
    }
    printf("✓ Platform initialized\n");
    
    // Initialize RFAL
    printf("2. Initializing RFAL library...\n");
    if (rfalNfcInitialize() != RFAL_ERR_NONE) {
        printf("✗ RFAL initialization failed\n");
        platformDeinit();
        return 1;
    }
    printf("✓ RFAL initialized\n");
    
    // Start discovery for NFC-A tags (NTAG213 is NFC-A)
    printf("3. Starting NFC-A discovery...\n");
    
    rfalNfcDiscoverParam discoverParam;
    discoverParam.compMode      = RFAL_COMPLIANCE_MODE_NFC;
    discoverParam.techs2Find    = RFAL_NFC_POLL_TECH_A;
    discoverParam.totalDuration = 1000;  // 1 second discovery
    discoverParam.devLimit      = 1;     // Find 1 device
    discoverParam.wakeupEnabled = false;
    discoverParam.wakeupConfigDefault = true;
    discoverParam.nfcfBR        = RFAL_BR_212;
    discoverParam.ap2pBR        = RFAL_BR_424;
    
    if (rfalNfcDiscover(&discoverParam) != RFAL_ERR_NONE) {
        printf("✗ Failed to start discovery\n");
        rfalNfcDeactivate(false);
        platformDeinit();
        return 1;
    }
    printf("✓ Discovery started\n");
    
    // Wait for discovery to complete
    printf("4. Scanning for NTAG213 tags...\n");
    printf("   Place your NTAG213 tag near the reader\n");
    
    rfalNfcDevice *nfcDevice;
    uint8_t devCnt;
    
    // Poll for discovery completion
    for (int i = 0; i < 100; i++) {  // 10 second timeout
        rfalNfcState state = rfalNfcGetState();
        
        if (state == RFAL_NFC_STATE_ACTIVATED) {
            printf("✓ Tag detected and activated!\n");
            
            // Get discovered devices
            rfalNfcGetDevicesFound(&nfcDevice, &devCnt);
            
            if (devCnt > 0 && nfcDevice->type == RFAL_NFC_DEV_TYPE_NFCA_T2T) {
                printf("✓ NTAG213 (NFC-A Type 2) detected!\n");
                
                // Print tag information
                printf("\nTag Information:\n");
                printf("  Type: NFC-A Type 2 (NTAG213)\n");
                printf("  NFCID1 (UID): ");
                for (int j = 0; j < nfcDevice->nfcA.nfcId1Len; j++) {
                    printf("%02X ", nfcDevice->nfcA.nfcId1[j]);
                }
                printf("\n");
                printf("  ATQA: 0x%04X\n", 
                       (nfcDevice->nfcA.sensRes.anticollisionInfo << 8) | 
                       nfcDevice->nfcA.sensRes.platformInfo);
                printf("  SAK: 0x%02X\n", nfcDevice->nfcA.selRes.sak);
                
                printf("\n🎉 SUCCESS: NTAG213 communication working!\n");
                break;
            } else {
                printf("⚠ Tag detected but not NTAG213 (Type: %d)\n", nfcDevice->type);
            }
            break;
            
        } else if (state == RFAL_NFC_STATE_LISTEN_SLEEP) {
            // Discovery completed, no tags found
            printf("✗ No tags detected\n");
            break;
            
        } else if (state == RFAL_NFC_STATE_IDLE) {
            // Discovery finished
            printf("⚠ Discovery completed without finding tags\n");
            break;
        }
        
        // Continue discovery process
        rfalNfcWorker();
        usleep(100000);  // 100ms delay
    }
    
    // Cleanup
    printf("\n5. Cleaning up...\n");
    rfalNfcDeinitialize();
    platformDeinit();
    printf("✓ Cleanup completed\n");
    
    return 0;
}