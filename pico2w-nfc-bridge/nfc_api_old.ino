/**
 * PN7160 NFC Bridge - New Version
 * Combines the reliable library initialization from working example
 * with the bridge command interface from the old non-functional script
 */

#include "Electroniccats_PN7150.h"

// Pin Configuration (matching the old script)
#define PN7160_IRQ (18)
#define PN7160_VEN (19)
#define PN7160_ADDR (0x28)
#define PN7160_SDA (16) 
#define PN7160_SCL (17)

// Create NFC device using the working library
Electroniccats_PN7150 nfc(PN7160_IRQ, PN7160_VEN, PN7160_ADDR, PN7160);

// Global NDEF message objects
NdefMessage ndefMessage;     // For receiving content
NdefMessage writeMessage;    // For writing content
String lastNdefText = "";
bool ndefReceived = false;
bool ndefWritten = false;

// Callback function for when NDEF messages are received
void messageReceivedCallback() {
    NdefRecord record;
    lastNdefText = "";
    ndefReceived = true;
    
    if (ndefMessage.isEmpty()) {
        lastNdefText = "Empty message";
        return;
    }
    
    // Process individual records
    do {
        record.create(ndefMessage.getRecord());
        
        if (record.getType() == record.type.WELL_KNOWN_SIMPLE_TEXT) {
            lastNdefText = record.getText();
        } else if (record.getType() == record.type.WELL_KNOWN_SIMPLE_URI) {
            lastNdefText = record.getUri();
        }
        // Add more record types as needed
        
    } while (record.isNotEmpty());
    
    if (lastNdefText == "") {
        lastNdefText = "No text content found";
    }
}

// Callback function for when NDEF messages are sent/written
void messageSentCallback() {
    ndefWritten = true;
    Serial.println("NFC: NDEF message written successfully");
}

class NFCBridge {
private:
    bool initialized;
    unsigned long last_keepalive;
    
public:
    NFCBridge() : initialized(false), last_keepalive(0) {}
    
    bool initialize() {
        Serial.println("NFC: Starting initialization using library...");
        
        // Critical: Set I2C pins before calling connectNCI
        Wire.setSDA(PN7160_SDA);
        Wire.setSCL(PN7160_SCL);
        
        // Initialize the global NDEF message objects
        ndefMessage.begin();
        writeMessage.begin();
        
        // Register callbacks for NDEF message reception and sending
        nfc.setReadMsgCallback(messageReceivedCallback);
        nfc.setSendMsgCallback(messageSentCallback);
        
        // Use the library's proven initialization sequence
        if (nfc.connectNCI()) {
            Serial.println("NFC: Error during connectNCI - check connections!");
            return false;
        }
        
        if (nfc.configureSettings()) {
            Serial.println("NFC: Error during configureSettings!");
            return false;
        }
        
        if (nfc.configMode()) {
            Serial.println("NFC: Error during configMode!");
            return false;
        }
        
        Serial.println("NFC: Library initialization successful");
        initialized = true;
        last_keepalive = millis();
        return true;
    }
    
    void maintainConnection() {
        if (!initialized) return;
        
        // Send keep-alive every 2 seconds to prevent timeout
        if (millis() - last_keepalive > 2000) {
            // Use a simple presence check as keep-alive
            nfc.reset(); // Gentle reset to keep connection alive
            last_keepalive = millis();
        }
    }
    
    bool pollForTags(int maxTags = 1, uint32_t timeout_ms = 10000) {
        if (!initialized) {
            Serial.println("ERROR: NFC not initialized");
            return false;
        }
        
        int tagsFound = 0;
        unsigned long startTime = millis();
        
        // Start discovery to detect tags
        nfc.startDiscovery();
        
        while (tagsFound < maxTags && (millis() - startTime) < timeout_ms) {
            // Check for tag detection with remaining timeout
            uint32_t remainingTimeout = timeout_ms - (millis() - startTime);
            if (remainingTimeout <= 0) break;
            
            if (nfc.isTagDetected(min(remainingTimeout, (uint32_t)1000))) {
                tagsFound++;
                
                // Start building compact response: OK:TAG#:PROTOCOL:TECH:ID:"MESSAGE"
                Serial.print("OK:");
                Serial.print(tagsFound);
                Serial.print(":");
                Serial.print(nfc.remoteDevice.getProtocol());
                Serial.print(":");
                Serial.print(nfc.remoteDevice.getModeTech());
                Serial.print(":");
                
                // Display tag ID (compact hex without spaces)
                switch (nfc.remoteDevice.getModeTech()) {
                    case nfc.tech.PASSIVE_NFCA:
                        printCompactHex(nfc.remoteDevice.getNFCID(), nfc.remoteDevice.getNFCIDLen());
                        break;
                    default:
                        Serial.print("NONE");
                        break;
                }
                
                Serial.print(":\"");
                
                // Read NDEF content if available
                if (nfc.remoteDevice.getProtocol() == nfc.protocol.T2T) {
                    readT2TNdefContentCompact();
                } else {
                    readTagContentCompact(); // Fallback to high-level method
                }
                
                Serial.println("\"");
                
                // Wait for tag removal before looking for next tag
                if (tagsFound < maxTags) {
                    nfc.waitForTagRemoval();
                    nfc.reset(); // Reset for next detection
                }
            }
            
            delay(100); // Small delay to prevent tight loop
        }
        
        // Stop discovery when done
        nfc.stopDiscovery();
        
        if (tagsFound == 0) {
            Serial.println("ERROR:TIMEOUT");
        }
        
        Serial.println("POLLEND");
        return tagsFound > 0;
    }
    
    void readT2TNdefContent() {
        bool status;
        unsigned char Resp[256];
        unsigned char RespSize;
        String extractedText = "";
        
        // Read block 4 first to check for NDEF TLV
        unsigned char ReadBlock4[] = {0x30, 0x04};
        
        status = nfc.readerTagCmd(ReadBlock4, sizeof(ReadBlock4), Resp, &RespSize);
        if ((status == NFC_ERROR) || (Resp[RespSize - 1] != 0x00)) {
            Serial.print("No NDEF content found");
            return;
        }
        
        // Check if block 4 starts with NDEF TLV (0x03)
        if (Resp[0] != 0x03) {
            Serial.print("No NDEF content found");
            return;
        }
        
        int ndefLength = Resp[1]; // NDEF message length
        if (ndefLength == 0) {
            Serial.print("Empty NDEF message");
            return;
        }
        
        // Read enough blocks to get the full NDEF message
        int blocksToRead = (ndefLength + 8) / 4; // +8 for TLV header and some padding, /4 bytes per block
        if (blocksToRead > 20) blocksToRead = 20; // Reasonable limit
        
        // Collect all NDEF data
        unsigned char ndefData[256];
        int ndefIndex = 0;
        
        for (int blockNum = 4; blockNum < 4 + blocksToRead && ndefIndex < 250; blockNum++) {
            unsigned char ReadBlock[] = {0x30, blockNum};
            
            status = nfc.readerTagCmd(ReadBlock, sizeof(ReadBlock), Resp, &RespSize);
            if ((status == NFC_ERROR) || (Resp[RespSize - 1] != 0x00)) {
                break; // Stop if we can't read more blocks
            }
            
            // Copy 4 bytes from this block
            for (int i = 0; i < 4 && ndefIndex < 250; i++) {
                ndefData[ndefIndex++] = Resp[i];
            }
        }
        
        // Parse NDEF content starting after TLV header (skip first 2 bytes: 0x03, length)
        if (ndefIndex > 8) { // Minimum for a text record
            int parseIndex = 2; // Skip TLV header
            
            // Check NDEF record header
            if (ndefData[parseIndex] == 0xD1) { // Text record header we wrote
                parseIndex++; // Skip record header
                
                if (ndefData[parseIndex] == 0x01) { // Type length = 1
                    parseIndex++; // Skip type length
                    
                    int payloadLen = ndefData[parseIndex++]; // Payload length
                    
                    if (ndefData[parseIndex] == 0x54) { // Type = "T"
                        parseIndex++; // Skip type
                        
                        int langCodeLen = ndefData[parseIndex++]; // Language code length
                        
                        // Skip language code
                        parseIndex += langCodeLen;
                        
                        // Extract text
                        int textLen = payloadLen - langCodeLen;
                        for (int i = 0; i < textLen && parseIndex < ndefIndex; i++) {
                            extractedText += (char)ndefData[parseIndex++];
                        }
                    }
                }
            }
        }
        
        if (extractedText.length() > 0) {
            Serial.print("Content: \"");
            Serial.print(extractedText);
            Serial.print("\"");
        } else {
            Serial.print("No readable text content found");
        }
    }
    
    void readTagContent() {
        // Reset NDEF reception flag
        ndefReceived = false;
        lastNdefText = "";
        
        // Try to read NDEF message content
        nfc.readNdefMessage();
        
        // Wait a moment for callback to process
        delay(100);
        
        // Check if we received NDEF content via callback
        if (ndefReceived && lastNdefText != "") {
            Serial.print("Content: \"");
            Serial.print(lastNdefText);
            Serial.print("\"");
        } else {
            Serial.print("No NDEF content found");
        }
    }
    
    int getGPIO(const char* name) {
        if (strcmp(name, "IRQ") == 0) return digitalRead(PN7160_IRQ);
        if (strcmp(name, "VEN") == 0) return digitalRead(PN7160_VEN);
        if (strcmp(name, "FWDL") == 0) return -1; // Not used in this version
        return -1;
    }
    
    bool isNFCPresent() {
        Wire.beginTransmission(PN7160_ADDR);
        return (Wire.endTransmission() == 0);
    }
    
    bool writeToTag(String text) {
        if (!initialized) {
            Serial.println("ERROR: NFC not initialized");
            return false;
        }
        
        // Start discovery to find a tag to write to
        nfc.startDiscovery();
        
        // Wait for tag detection with timeout
        if (nfc.isTagDetected(10000)) {
            // Check if it's a T2T tag (like NTAG215)
            if (nfc.remoteDevice.getProtocol() == nfc.protocol.T2T) {
                return writeNdefToT2T(text);
            } else {
                Serial.println("ERROR:UNSUPPORTED_TAG");
                nfc.stopDiscovery();
                return false;
            }
        } else {
            Serial.println("ERROR:TIMEOUT");
            nfc.stopDiscovery();
            return false;
        }
    }
    
    bool writeNdefToT2T(String text) {
        bool status;
        unsigned char Resp[256];
        unsigned char RespSize;
        
        // Determine write acknowledgment based on chip model
        uint8_t ChipWriteAck = (nfc.getChipModel() == PN7160) ? 0x14 : 0x00;
        
        // Calculate message length
        int textLen = text.length();
        int recordLen = 3 + 2 + textLen; // Header(1) + Type Length(1) + Payload Length(1) + Language(2) + Text
        int totalLen = recordLen + 2; // Add TLV header (2 bytes: Type + Length)
        
        if (totalLen > 48) { // NTAG215 has limited space in early blocks
            Serial.println("ERROR:TEXT_TOO_LONG");
            nfc.stopDiscovery();
            return false;
        }
        
        // Block 4: NDEF TLV + Text Record Header
        unsigned char block4[4];
        block4[0] = 0x03; // NDEF TLV Type
        block4[1] = recordLen; // NDEF message length
        block4[2] = 0xD1; // NDEF Record Header (MB=1, ME=1, CF=0, SR=1, IL=0, TNF=1)
        block4[3] = 0x01; // Type Length = 1
        
        unsigned char WriteBlock4[] = {0xA2, 0x04, block4[0], block4[1], block4[2], block4[3]};
        
        status = nfc.readerTagCmd(WriteBlock4, sizeof(WriteBlock4), Resp, &RespSize);
        if ((status == NFC_ERROR) || (Resp[RespSize - 1] != ChipWriteAck)) {
            Serial.println("ERROR:WRITE_FAILED");
            nfc.stopDiscovery();
            return false;
        }
        
        // Block 5: Payload Length + Type + Language Code start
        unsigned char block5[4];
        block5[0] = textLen + 2; // Payload length (text + 2-byte language code)
        block5[1] = 0x54; // Type = "T" (text record)
        block5[2] = 0x02; // Language code length = 2
        block5[3] = 0x65; // Language "en" part 1
        
        unsigned char WriteBlock5[] = {0xA2, 0x05, block5[0], block5[1], block5[2], block5[3]};
        
        status = nfc.readerTagCmd(WriteBlock5, sizeof(WriteBlock5), Resp, &RespSize);
        if ((status == NFC_ERROR) || (Resp[RespSize - 1] != ChipWriteAck)) {
            Serial.println("ERROR:WRITE_FAILED");
            nfc.stopDiscovery();
            return false;
        }
        
        // Block 6: Complete language code + start of text
        unsigned char block6[4];
        block6[0] = 0x6E; // Language "en" part 2
        int textIndex = 0;
        for (int i = 1; i < 4 && textIndex < textLen; i++, textIndex++) {
            block6[i] = text.charAt(textIndex);
        }
        // Fill remaining bytes with 0x00 if text is shorter
        for (int i = textIndex + 1; i < 4; i++) {
            block6[i] = 0x00;
        }
        
        unsigned char WriteBlock6[] = {0xA2, 0x06, block6[0], block6[1], block6[2], block6[3]};
        
        status = nfc.readerTagCmd(WriteBlock6, sizeof(WriteBlock6), Resp, &RespSize);
        if ((status == NFC_ERROR) || (Resp[RespSize - 1] != ChipWriteAck)) {
            Serial.println("ERROR:WRITE_FAILED");
            nfc.stopDiscovery();
            return false;
        }
        
        // Write remaining text blocks if needed
        int blockNum = 7;
        while (textIndex < textLen && blockNum < 50) { // Limit to reasonable block range
            unsigned char textBlock[4] = {0x00, 0x00, 0x00, 0x00};
            
            for (int i = 0; i < 4 && textIndex < textLen; i++, textIndex++) {
                textBlock[i] = text.charAt(textIndex);
            }
            
            unsigned char WriteTextBlock[] = {0xA2, blockNum, textBlock[0], textBlock[1], textBlock[2], textBlock[3]};
            
            status = nfc.readerTagCmd(WriteTextBlock, sizeof(WriteTextBlock), Resp, &RespSize);
            if ((status == NFC_ERROR) || (Resp[RespSize - 1] != ChipWriteAck)) {
                Serial.println("ERROR:WRITE_FAILED");
                nfc.stopDiscovery();
                return false;
            }
            
            blockNum++;
        }
        
        // Write NDEF terminator if there's space
        if (blockNum < 50) {
            unsigned char terminatorBlock[4] = {0xFE, 0x00, 0x00, 0x00}; // TLV Terminator
            unsigned char WriteTerminator[] = {0xA2, blockNum, terminatorBlock[0], terminatorBlock[1], terminatorBlock[2], terminatorBlock[3]};
            
            nfc.readerTagCmd(WriteTerminator, sizeof(WriteTerminator), Resp, &RespSize);
            // Don't check for error on terminator - not critical
        }
        
        nfc.stopDiscovery();
        return true;
    }
    
    void printHex(const uint8_t* data, int length) {
        for (int i = 0; i < length; i++) {
            if (data[i] < 16) Serial.print("0");
            Serial.print(data[i], HEX);
            Serial.print(" ");
        }
        Serial.println();
    }
    
    void printCompactHex(const uint8_t* data, int length) {
        for (int i = 0; i < length; i++) {
            if (data[i] < 16) Serial.print("0");
            Serial.print(data[i], HEX);
        }
    }
    
    void readT2TNdefContentCompact() {
        bool status;
        unsigned char Resp[256];
        unsigned char RespSize;
        String extractedText = "";
        
        // Read block 4 first to check for NDEF TLV
        unsigned char ReadBlock4[] = {0x30, 0x04};
        
        status = nfc.readerTagCmd(ReadBlock4, sizeof(ReadBlock4), Resp, &RespSize);
        if ((status == NFC_ERROR) || (Resp[RespSize - 1] != 0x00)) {
            return; // Empty string will be printed
        }
        
        // Check if block 4 starts with NDEF TLV (0x03)
        if (Resp[0] != 0x03) {
            return; // Empty string will be printed
        }
        
        int ndefLength = Resp[1]; // NDEF message length
        if (ndefLength == 0) {
            return; // Empty string will be printed
        }
        
        // Read enough blocks to get the full NDEF message
        int blocksToRead = (ndefLength + 8) / 4;
        if (blocksToRead > 20) blocksToRead = 20;
        
        // Collect all NDEF data
        unsigned char ndefData[256];
        int ndefIndex = 0;
        
        for (int blockNum = 4; blockNum < 4 + blocksToRead && ndefIndex < 250; blockNum++) {
            unsigned char ReadBlock[] = {0x30, blockNum};
            
            status = nfc.readerTagCmd(ReadBlock, sizeof(ReadBlock), Resp, &RespSize);
            if ((status == NFC_ERROR) || (Resp[RespSize - 1] != 0x00)) {
                break;
            }
            
            for (int i = 0; i < 4 && ndefIndex < 250; i++) {
                ndefData[ndefIndex++] = Resp[i];
            }
        }
        
        // Parse NDEF content starting after TLV header
        if (ndefIndex > 8) {
            int parseIndex = 2; // Skip TLV header
            
            // Check NDEF record header
            if (ndefData[parseIndex] == 0xD1) { // Text record header we wrote
                parseIndex++; // Skip record header
                
                if (ndefData[parseIndex] == 0x01) { // Type length = 1
                    parseIndex++; // Skip type length
                    
                    int payloadLen = ndefData[parseIndex++]; // Payload length
                    
                    if (ndefData[parseIndex] == 0x54) { // Type = "T"
                        parseIndex++; // Skip type
                        
                        int langCodeLen = ndefData[parseIndex++]; // Language code length
                        
                        // Skip language code
                        parseIndex += langCodeLen;
                        
                        // Extract text
                        int textLen = payloadLen - langCodeLen;
                        for (int i = 0; i < textLen && parseIndex < ndefIndex; i++) {
                            extractedText += (char)ndefData[parseIndex++];
                        }
                    }
                }
            }
        }
        
        Serial.print(extractedText); // Print text directly (will be empty string if nothing found)
    }
    
    void readTagContentCompact() {
        // Reset NDEF reception flag
        ndefReceived = false;
        lastNdefText = "";
        
        // Try to read NDEF message content
        nfc.readNdefMessage();
        
        // Wait a moment for callback to process
        delay(100);
        
        // Print the result (will be empty string if nothing found)
        if (ndefReceived && lastNdefText != "") {
            Serial.print(lastNdefText);
        }
    }
    
};

NFCBridge* bridge;

void setup() {
    Serial.begin(115200);
    while (!Serial) delay(10);
    
    Serial.println("==================================================");
    Serial.println("Pico W PN7160 NFC Bridge (Library-based version)");
    Serial.print("I2C: SDA=GP");
    Serial.print(PN7160_SDA);
    Serial.print(", SCL=GP");
    Serial.print(PN7160_SCL);
    Serial.println();
    Serial.println("==================================================");
    
    bridge = new NFCBridge();
    
    if (bridge->initialize()) {
        Serial.println("Ready for serial commands...");
        Serial.println("HELP for a list of commands");
        Serial.println("--------------------------------------------------");
    } else {
        Serial.println("FAILED to initialize NFC bridge!");
        Serial.println("Check connections and reset to retry.");
        while(1) delay(1000);
    }
}

void loop() {
    // Maintain connection to prevent timeouts
    bridge->maintainConnection();
    
    if (Serial.available()) {
        char c = Serial.read();
        static String inputBuffer = "";
        
        if (c == '\n' || c == '\r') {
            // Complete command received
            inputBuffer.trim();
            if (inputBuffer.length() > 0) {
                processCommand(inputBuffer);
                inputBuffer = ""; // Clear buffer
            }
        } else {
            // Add character to buffer
            inputBuffer += c;
        }
    }
}

void processCommand(String cmdline) {
    cmdline.toUpperCase();
    
    if (cmdline == "HELP") {
        Serial.println("Commands:");
        Serial.println("HELP");
        Serial.println("- Returns this");
        Serial.println("PING - Returns OK:PONG");
        Serial.println("POLL | POLL:<amount of tags>");
        Serial.println("- Returns OK:TAGNUMBER:PROTOCOL:TECH:ID:\"MESSAGE\" for every detected tag until either all tags have been found or 10 seconds have passed");
        Serial.println("- Ends with POLLEND when polling ends, even after an ERROR");
        Serial.println("WRITE:<message>");
        Serial.println("- Writes a message to the tag");
        
    }
    else if (cmdline == "PING") {
        Serial.println("OK:PONG");
    }
    else if (cmdline == "POLL" || cmdline.startsWith("POLL:")) {
        int maxTags = 1;
        
        // Parse optional argument
        if (cmdline.startsWith("POLL:")) {
            String argStr = cmdline.substring(5);
            maxTags = argStr.toInt();
            if (maxTags <= 0) maxTags = 1; // Default to 1 if invalid
        }
        
        if (bridge->pollForTags(maxTags)) {
            // Success message already printed by pollForTags
        } else {
            // Error message already printed by pollForTags
        }
    }
    else if (cmdline.startsWith("WRITE:")) {
        String message = cmdline.substring(6); // Remove "WRITE:" prefix
        if (bridge->writeToTag(message)) {
            Serial.println("OK:WRITE_SUCCESS");
        } else {
            // Error message already printed by writeToTag
        }
    }
    else {
        Serial.println("ERROR:UNKNOWN_COMMAND");
    }
}