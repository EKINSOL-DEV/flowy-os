/*
 * Platform abstraction layer for Raspberry Pi 5
 * Implementation connecting RFAL to Pi 5 hardware
 */

// For timespec and clock_gettime
#define _POSIX_C_SOURCE 199309L

#include "platform_pi5.h"
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <linux/spi/spidev.h>
#include <time.h>
#include <sys/time.h>
#include <lgpio.h>
/*
******************************************************************************
* LOCAL VARIABLES
******************************************************************************
*/
static int spi_fd = -1;
static void (*irq_callback)(void) = NULL;
static uint32_t start_time_ms = 0;

// GPIO handles for lgpio library
static int gpio_handle = -1;

/*
******************************************************************************
* LOCAL FUNCTIONS
******************************************************************************
*/

static uint32_t get_time_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint32_t)(ts.tv_sec * 1000 + ts.tv_nsec / 1000000);
}

static int gpio_init(void) {
    // Open GPIO chip (chip 0 on Pi 5)
    gpio_handle = lgGpiochipOpen(0);
    if (gpio_handle < 0) {
        printf("Failed to open GPIO chip 0: %s\n", lguErrorText(gpio_handle));
        return -1;
    }
    return 0;
}

static void gpio_cleanup(void) {
    if (gpio_handle >= 0) {
        lgGpiochipClose(gpio_handle);
        gpio_handle = -1;
    }
}

/*
******************************************************************************
* GLOBAL FUNCTIONS
******************************************************************************
*/

int platformInit(void) {
    printf("Initializing Pi 5 platform layer...\n");
    
    // Initialize timing
    start_time_ms = get_time_ms();
    
    // Open SPI device - try bus 10 first (Pi 5), fallback to bus 0  
    spi_fd = open("/dev/spidev10.0", O_RDWR);
    if (spi_fd < 0) {
        printf("SPI bus 10 not available, trying bus 0...\n");
        spi_fd = open("/dev/spidev0.0", O_RDWR);
        if (spi_fd < 0) {
            perror("Failed to open SPI device on bus 0 or 10");
            return -1;
        }
        printf("Using SPI bus 0\n");
    } else {
        printf("Using SPI bus 10\n");
    }
    
    // Configure SPI
    uint32_t mode = SPI_MODE_0;
    uint32_t speed = PI5_SPI_SPEED;
    uint8_t bits = 8;
    
    if (ioctl(spi_fd, SPI_IOC_WR_MODE32, &mode) < 0 ||
        ioctl(spi_fd, SPI_IOC_WR_MAX_SPEED_HZ, &speed) < 0 ||
        ioctl(spi_fd, SPI_IOC_WR_BITS_PER_WORD, &bits) < 0) {
        perror("Failed to configure SPI");
        close(spi_fd);
        return -1;
    }
    
    // Initialize GPIO
    if (gpio_init() < 0) {
        printf("Failed to initialize GPIO\n");
        close(spi_fd);
        return -1;
    }
    
    // Configure GPIO pins (only IRQ - no reset pin on this board)
    int ret = lgGpioClaimInput(gpio_handle, 0, PI5_GPIO_IRQ);
    if (ret < 0) {
        printf("Failed to claim IRQ GPIO: %s\n", lguErrorText(ret));
        close(spi_fd);
        gpio_cleanup();
        return -1;
    }
    
    // No hardware reset available on this board - skip reset sequence
    printf("Note: No hardware reset pin available, relying on software reset\n");
    
    printf("Pi 5 platform initialized successfully\n");
    return 0;
}

void platformDeinit(void) {
    // Free GPIO resources (only IRQ, no reset pin)
    if (gpio_handle >= 0) {
        lgGpioFree(gpio_handle, PI5_GPIO_IRQ);
    }
    gpio_cleanup();
    
    if (spi_fd >= 0) {
        close(spi_fd);
        spi_fd = -1;
    }
    
    printf("Pi 5 platform deinitialized\n");
}

void platformSpiTxRx(const uint8_t *txBuf, uint8_t *rxBuf, uint16_t len) {
    if (spi_fd < 0) {
        printf("SPI ERROR: spi_fd not initialized\n");
        return;
    }
    
    struct spi_ioc_transfer transfer = {
        .tx_buf = (unsigned long)txBuf,
        .rx_buf = (unsigned long)rxBuf,
        .len = len,
        .speed_hz = PI5_SPI_SPEED,
        .bits_per_word = 8,
        .cs_change = 0,
    };
    
    if (txBuf && len > 0) {
        printf("SPI TX (%d bytes): ", len);
        for (int i = 0; i < len && i < 8; i++) {
            printf("%02X ", txBuf[i]);
        }
        if (len > 8) printf("...");
        printf("\n");
    }
    
    if (ioctl(spi_fd, SPI_IOC_MESSAGE(1), &transfer) < 0) {
        perror("SPI transfer failed");
        return;
    }
    
    if (rxBuf && len > 0) {
        printf("SPI RX (%d bytes): ", len);
        for (int i = 0; i < len && i < 8; i++) {
            printf("%02X ", rxBuf[i]);
        }
        if (len > 8) printf("...");
        printf("\n");
    }
}

void platformSpiSelect(void) {
    // SPI CS is handled automatically by Linux SPI driver
    // No explicit action needed
}

void platformSpiDeselect(void) {
    // SPI CS is handled automatically by Linux SPI driver  
    // No explicit action needed
}

uint32_t platformGetSysTick(void) {
    return get_time_ms() - start_time_ms;
}

void platformDelay(uint32_t ms) {
    usleep(ms * 1000);
}

void platformIrqST25RPinInitialize(void) {
    // Already initialized in platformInit()
}

void platformIrqST25RSetCallback(void (*callback)(void)) {
    irq_callback = callback;
}

bool platformGpioIsHigh(uint16_t port, uint16_t pin) {
    (void)port; // Unused on Pi
    
    if (pin == PI5_GPIO_IRQ && gpio_handle >= 0) {
        int value = lgGpioRead(gpio_handle, PI5_GPIO_IRQ);
        return (value == 1);
    }
    return false;
}

void platformGpioSet(uint16_t port, uint16_t pin) {
    (void)port; // Unused on Pi
    (void)pin;  // No GPIO outputs available (no reset pin)
    // No-op: reset pin not available on this board
}

void platformGpioClear(uint16_t port, uint16_t pin) {
    (void)port; // Unused on Pi  
    (void)pin;  // No GPIO outputs available (no reset pin)
    // No-op: reset pin not available on this board
}

// Protection functions (no-op for single threaded)
void platformProtectST25RIrqStatus(void) { }
void platformUnprotectST25RIrqStatus(void) { }
void platformProtectWorker(void) { }
void platformUnprotectWorker(void) { }
void platformProtectST25RComm(void) { }
void platformUnprotectST25RComm(void) { }

// LED functions (no-op)
void platformLedsInitialize(void) { }
void platformLedOff(uint16_t port, uint16_t pin) { (void)port; (void)pin; }
void platformLedOn(uint16_t port, uint16_t pin) { (void)port; (void)pin; }
void platformLedToggle(uint16_t port, uint16_t pin) { (void)port; (void)pin; }

// Timer functions (simplified)
uint32_t platformTimerCreate(uint32_t timeout_ms) {
    // Return current time + timeout as timer handle
    return get_time_ms() + timeout_ms;
}

bool platformTimerIsExpired(uint32_t timer) {
    // Timer is expired if current time >= timer handle
    return get_time_ms() >= timer;
}

uint32_t platformTimerGetRemaining(uint32_t timer) {
    uint32_t current = get_time_ms();
    if (current >= timer) {
        return 0; // Expired
    }
    return timer - current; // Remaining time
}

void platformTimerDestroy(uint32_t timer) {
    (void)timer; // No cleanup needed for our simple implementation
}

void platformLog(const char* format, ...) {
    va_list args;
    va_start(args, format);
    printf("[RFAL] ");
    vprintf(format, args);
    printf("\n");
    va_end(args);
}

void platformAssert(bool expression) {
    if (!expression) {
        printf("PLATFORM ASSERTION FAILED!\n");
        exit(1);
    }
}

void platformErrorHandle(void) {
    printf("PLATFORM ERROR!\n");
    exit(1);
}