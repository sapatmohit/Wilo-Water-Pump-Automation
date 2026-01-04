#include <SPI.h>
#include <LoRa.h>

// ==========================================
// CONFIGURATION
// ==========================================

// Pins for ESP32 (Standard SPI + LoRa)
#define SS_PIN   5
#define RST_PIN  14
#define DIO0_PIN 26

// Frequency: 433E6, 868E6, 915E6
#define BAND    433E6 

// ==========================================

int counter = 0;

void setup() {
  Serial.begin(115200);
  while (!Serial);

  Serial.println("LoRa Sender Setup...");

  // Override the default pins if necessary
  LoRa.setPins(SS_PIN, RST_PIN, DIO0_PIN);

  if (!LoRa.begin(BAND)) {
    Serial.println("Starting LoRa failed!");
    while (1);
  }
  
  // Optional: Set Spreading Factor (6-12), Bandwidth, etc.
  // LoRa.setSpreadingFactor(7);
  // LoRa.setSignalBandwidth(125E3);
  
  // Sync word ensures you only receive packets from your network
  // 0xF3 is a common test value, ranges from 0-0xFF
  LoRa.setSyncWord(0xF3);

  Serial.println("LoRa Initialized OK!");
}

void loop() {
  Serial.print("Sending packet: ");
  Serial.println(counter);

  // create a simple JSON-like string
  String payload = "{\"device\":\"esp32\",\"count\":" + String(counter) + ",\"value\":42}";

  // Send LoRa packet to receiver
  LoRa.beginPacket();
  LoRa.print(payload);
  LoRa.endPacket();

  counter++;

  // Wait 5 seconds
  delay(5000);
}
