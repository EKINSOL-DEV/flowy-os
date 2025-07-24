/*
 * Platform abstraction layer for Raspberry Pi 5
 * Connects RFAL library to Pi 5 hardware (SPI bus 0, GPIO 17/22, lgpio)
 */

#ifndef PLATFORM_PI5_H
#define PLATFORM_PI5_H

#include <stdint.h>
#include <stdbool.h>

/*
******************************************************************************
* INCLUDES
******************************************************************************
*/
#include <unistd.h>
#include <time.h>
#include <sys/time.h>

/*
******************************************************************************
* GLOBAL DEFINES
******************************************************************************
*/

// Pi 5 hardware configuration (from our debugging)
#define PI5_SPI_BUS         0      // SPI bus 0 (not 10)
#define PI5_SPI_DEVICE      0      // SPI device 0
#define PI5_GPIO_IRQ        17     // GPIO 17 for IRQ
#define PI5_GPIO_RESET      22     // GPIO 22 for reset
#define PI5_SPI_SPEED       1000000 // 1MHz SPI speed

// ST25R3916 GPIO pin definitions (for RFAL compatibility)
#define ST25R_INT_PORT      0      // GPIO chip (unused on Pi)
#define ST25R_INT_PIN       PI5_GPIO_IRQ  // GPIO 17

/*
******************************************************************************
* GLOBAL FUNCTION PROTOTYPES  
******************************************************************************
*/

// Platform initialization
int platformInit(void);
void platformDeinit(void);

// SPI communication
void platformSpiTxRx(const uint8_t *txBuf, uint8_t *rxBuf, uint16_t len);
void platformSpiSelect(void);
void platformSpiDeselect(void);

// Timing functions
uint32_t platformGetSysTick(void);
void platformDelay(uint32_t ms);

// GPIO/IRQ functions
void platformIrqST25RPinInitialize(void);
void platformIrqST25RSetCallback(void (*callback)(void));
bool platformGpioIsHigh(uint16_t port, uint16_t pin);
void platformGpioSet(uint16_t port, uint16_t pin);
void platformGpioClear(uint16_t port, uint16_t pin);

// Protection functions (no-op for single threaded)
void platformProtectST25RIrqStatus(void);
void platformUnprotectST25RIrqStatus(void);
void platformProtectWorker(void);
void platformUnprotectWorker(void);
void platformProtectST25RComm(void);
void platformUnprotectST25RComm(void);

// LED functions (no-op)
void platformLedsInitialize(void);
void platformLedOff(uint16_t port, uint16_t pin);
void platformLedOn(uint16_t port, uint16_t pin);
void platformLedToggle(uint16_t port, uint16_t pin);

// Timer functions (simplified)
uint32_t platformTimerCreate(uint32_t timeout_ms);
bool platformTimerIsExpired(uint32_t timer);
uint32_t platformTimerGetRemaining(uint32_t timer);
void platformTimerDestroy(uint32_t timer);

// Logging/debug
void platformLog(const char* format, ...);
void platformAssert(bool expression);
void platformErrorHandle(void);

#endif /* PLATFORM_PI5_H */