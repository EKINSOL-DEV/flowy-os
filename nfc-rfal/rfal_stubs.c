/*
 * RFAL stub implementations for disabled features
 * Provides empty implementations for functions referenced by enabled modules
 * but belonging to disabled protocols (NFC-B, NFC-F, NFC-V, ST25TB)
 */

#include "rfal_utils.h"
#include "rfal_nfcb.h"
#include "rfal_nfcf.h"
#include "rfal_nfcv.h"
#include "rfal_st25tb.h"

// Analog config symbols are defined in simple_analog_config.c

// NFC-B stubs (disabled in our config)
ReturnCode rfalNfcbPollerInitialize(void) {
    return RFAL_ERR_NOTSUPP;
}

ReturnCode rfalNfcbPollerTechnologyDetection(rfalComplianceMode compMode, rfalNfcbSensbRes *sensbRes, uint8_t *sensbResLen) {
    (void)compMode; (void)sensbRes; (void)sensbResLen;
    return RFAL_ERR_NOTSUPP;
}

ReturnCode rfalNfcbPollerStartCollisionResolution(rfalComplianceMode compMode, uint8_t devLimit, rfalNfcbListenDevice *nfcbDevList, uint8_t *devCnt) {
    (void)compMode; (void)devLimit; (void)nfcbDevList; (void)devCnt;
    return RFAL_ERR_NOTSUPP;
}

ReturnCode rfalNfcbPollerGetCollisionResolutionStatus(void) {
    return RFAL_ERR_NOTSUPP;
}

// NFC-F stubs (disabled in our config)
ReturnCode rfalNfcfPollerInitialize(rfalBitRate bitRate) {
    (void)bitRate;
    return RFAL_ERR_NOTSUPP;
}

ReturnCode rfalNfcfPollerStartCheckPresence(void) {
    return RFAL_ERR_NOTSUPP;
}

ReturnCode rfalNfcfPollerGetCheckPresenceStatus(void) {
    return RFAL_ERR_NOTSUPP;
}

ReturnCode rfalNfcfPollerStartCollisionResolution(rfalComplianceMode compMode, uint8_t devLimit, rfalNfcfListenDevice *nfcfDevList, uint8_t *devCnt) {
    (void)compMode; (void)devLimit; (void)nfcfDevList; (void)devCnt;
    return RFAL_ERR_NOTSUPP;
}

ReturnCode rfalNfcfPollerGetCollisionResolutionStatus(void) {
    return RFAL_ERR_NOTSUPP;
}

// NFC-V stubs (disabled in our config)  
ReturnCode rfalNfcvPollerInitialize(void) {
    return RFAL_ERR_NOTSUPP;
}

ReturnCode rfalNfcvPollerCheckPresence(rfalNfcvInventoryRes *invRes) {
    (void)invRes;
    return RFAL_ERR_NOTSUPP;
}

// ST25TB stubs (disabled in our config)
ReturnCode rfalSt25tbPollerInitialize(void) {
    return RFAL_ERR_NOTSUPP;
}

ReturnCode rfalSt25tbPollerCheckPresence(uint8_t *chipId) {
    (void)chipId;
    return RFAL_ERR_NOTSUPP;
}