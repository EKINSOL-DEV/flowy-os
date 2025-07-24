# Makefile for RFAL library on Raspberry Pi 5
# Compiles RFAL with Pi 5 platform layer

CC = gcc
CFLAGS = -Wall -Wextra -O2 -fPIC -std=c99 -DST25R3916 -DRFAL_ANALOG_CONFIG_CUSTOM
INCLUDES = -I./include -I./source/st25r3916 -I./source -I.
LIBS = -lm -llgpio
TARGET = librfal.so
TEST_TARGET = rfal_test

# Source files
RFAL_SOURCES = \
	source/rfal_analogConfig.c \
	source/rfal_cd.c \
	source/rfal_crc.c \
	source/rfal_dlma.c \
	source/rfal_dpo.c \
	source/rfal_iso15693_2.c \
	source/rfal_isoDep.c \
	source/rfal_nfca.c \
	source/rfal_nfcb.c \
	source/rfal_nfc.c \
	source/rfal_nfcDep.c \
	source/rfal_nfcf.c \
	source/rfal_nfcv.c \
	source/rfal_st25tb.c \
	source/rfal_st25xv.c \
	source/rfal_t1t.c \
	source/rfal_t2t.c \
	source/rfal_t4t.c

ST25R3916_SOURCES = \
	source/st25r3916/rfal_rfst25r3916.c \
	source/st25r3916/st25r3916_aat.c \
	source/st25r3916/st25r3916.c \
	source/st25r3916/st25r3916_com.c \
	source/st25r3916/st25r3916_irq.c \
	source/st25r3916/st25r3916_led.c

PLATFORM_SOURCES = \
	platform_pi5.c \
	simple_analog_config.c \
	rfal_stubs.c

ALL_SOURCES = $(RFAL_SOURCES) $(ST25R3916_SOURCES) $(PLATFORM_SOURCES)
OBJECTS = $(ALL_SOURCES:.c=.o)

# Default target
all: $(TARGET)

# Shared library
$(TARGET): $(OBJECTS)
	$(CC) -shared -o $@ $^ $(LIBS)
	@echo "Built RFAL shared library: $(TARGET)"

# Object files
%.o: %.c
	$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@

# Test program
test: $(TARGET)
	@echo "Creating simple test program..."
	@echo '#include <stdio.h>' > test_simple.c
	@echo '#include <unistd.h>' >> test_simple.c
	@echo '#include "platform_pi5.h"' >> test_simple.c
	@echo 'int main() {' >> test_simple.c
	@echo '    printf("RFAL Platform Test\\n");' >> test_simple.c
	@echo '    if (platformInit() == 0) {' >> test_simple.c
	@echo '        printf("Platform initialized successfully\\n");' >> test_simple.c
	@echo '        platformDeinit();' >> test_simple.c
	@echo '        return 0;' >> test_simple.c
	@echo '    } else {' >> test_simple.c
	@echo '        printf("Platform initialization failed\\n");' >> test_simple.c
	@echo '        return 1;' >> test_simple.c
	@echo '    }' >> test_simple.c
	@echo '}' >> test_simple.c
	$(CC) $(CFLAGS) $(INCLUDES) -o test_simple test_simple.c -L. -lrfal $(LIBS)
	@echo "Built test program: test_simple"

# Clean build files
clean:
	rm -f $(OBJECTS) $(TARGET) test_simple test_simple.c

# Install library
install: $(TARGET)
	sudo cp $(TARGET) /usr/local/lib/
	sudo ldconfig
	@echo "RFAL library installed to /usr/local/lib/"

# Development dependencies
deps:
	sudo apt update
	sudo apt install -y build-essential

.PHONY: all clean install deps test