/*
 * RFAL Platform Configuration for Raspberry Pi 5
 * This file overrides the default RFAL configuration
 * Referenced by rfal_defConfig.h
 */

#ifndef RFAL_PLATFORM_H
#define RFAL_PLATFORM_H

#include "platform_pi5.h"

// Make sure analog config table is included
#ifndef RFAL_ANALOG_CONFIG_CUSTOM
#include "rfal_analogConfigTbl.h"
#endif

/*
******************************************************************************
* PLATFORM FUNCTION OVERRIDES
******************************************************************************
*/

// SPI Communication
#define platformSpiTxRx( txBuf, rxBuf, len )    platformSpiTxRx( txBuf, rxBuf, len )

// Timing
#define platformGetSysTick()                    platformGetSysTick()
#define platformTimerGetRemaining( timer )      platformTimerGetRemaining( timer )
#define platformTimerDestroy( timer )           platformTimerDestroy( timer )

// GPIO/IRQ
#define platformIrqST25RPinInitialize()         platformIrqST25RPinInitialize()
#define platformIrqST25RSetCallback( cb )       platformIrqST25RSetCallback( cb )

// Protection (single threaded - no-op)
#define platformProtectST25RIrqStatus()         platformProtectST25RIrqStatus()
#define platformUnprotectST25RIrqStatus()       platformUnprotectST25RIrqStatus()
#define platformProtectWorker()                 platformProtectWorker()
#define platformUnprotectWorker()               platformUnprotectWorker()

// LEDs (no-op)
#define platformLedsInitialize()                platformLedsInitialize()
#define platformLedOff( port, pin )             platformLedOff( port, pin )
#define platformLedOn( port, pin )              platformLedOn( port, pin )
#define platformLedToggle( port, pin )          platformLedToggle( port, pin )

// Logging/Debug
#define platformLog(...)                        platformLog(__VA_ARGS__)
#define platformAssert( exp )                   platformAssert( exp )
#define platformErrorHandle()                   platformErrorHandle()

/*
******************************************************************************
* RFAL CONFIGURATION OVERRIDES
******************************************************************************
*/

// Enable the features we need for NTAG213
#define RFAL_FEATURE_NFCA                       true
#define RFAL_FEATURE_NFCB                       false  
#define RFAL_FEATURE_NFCF                       false
#define RFAL_FEATURE_NFCV                       false
#define RFAL_FEATURE_T1T                        false
#define RFAL_FEATURE_T2T                        true   // NTAG213 is Type 2
#define RFAL_FEATURE_T4T                        false
#define RFAL_FEATURE_ST25TB                     false
#define RFAL_FEATURE_NFC_DEP                    false  // NFC-DEP (P2P) disabled
#define RFAL_FEATURE_ISO_DEP                    false  // ISO-DEP disabled

// Buffer and length configurations
#define RFAL_FEATURE_NFC_RF_BUF_LEN             256U   // RF buffer size
#define RFAL_FEATURE_NFC_DEP_PDU_MAX_LEN        254U   // Max PDU length
#define RFAL_FEATURE_NFC_BUFF_MAX_SIZE          258U   // Max buffer size
#define RFAL_FEATURE_ISO_DEP_FSDI_MAX           8U     // Max FSDI
#define RFAL_FEATURE_ISO_DEP_FSD_MAX            256U   // Max FSD

// Timing configuration
#define RFAL_TIMING_TOLERANCE                   10U    // 10% timing tolerance

// FIFO configuration  
#define RFAL_FIFO_IN_WL                         200U   // FIFO Water Level
#define RFAL_FIFO_OUT_WL                        200U

#endif /* RFAL_PLATFORM_H */