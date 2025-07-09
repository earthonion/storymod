// ESP-SPI-Flasher Arduino Sketch
// Source: https://github.com/samipfjo/ESP-SPI-Flasher

#include <SPI.h>
#define LED 2
void setup() {
  Serial.begin(921600); // High baud rate for faster transfer
  SPI.begin();
  SPI.setBitOrder(MSBFIRST);
  SPI.setDataMode(SPI_MODE0);
  pinMode(D8, OUTPUT); // CS pin
  digitalWrite(D8, HIGH);
  pinMode(LED, OUTPUT);
  for (int i = 0; i < 8 ; i++){
    digitalWrite(LED, HIGH);
    //Serial.println("LED is on");
    delay(100);
    digitalWrite(LED, LOW);
    //Serial.println("LED is off");
    delay(100);
  }
}

void loop() {
  digitalWrite(LED, LOW);
  if (Serial.available() > 0) {
    byte command = Serial.read();

    if (command == 'I') { // Identify Chip
      digitalWrite(D8, LOW);
      SPI.transfer(0x9F); // JEDEC ID command
      byte manufacturer_id = SPI.transfer(0x00);
      byte memory_type = SPI.transfer(0x00);
      byte capacity = SPI.transfer(0x00);
      digitalWrite(D8, HIGH);
      Serial.write(manufacturer_id);
      Serial.write(memory_type);
      Serial.write(capacity);
    } else if (command == 'R') { // Read Data
      long address = Serial.parseInt();
      int length = Serial.parseInt();
      digitalWrite(D8, LOW);
      SPI.transfer(0x03); // Read command
      SPI.transfer((address >> 16) & 0xFF);
      SPI.transfer((address >> 8) & 0xFF);
      SPI.transfer(address & 0xFF);
      for (int i = 0; i < length; i++) {
        Serial.write(SPI.transfer(0x00));
      }
      digitalWrite(D8, HIGH);
    } else if (command == 'W') { // Write Data
      long address = Serial.parseInt();
      int length = Serial.parseInt();
      byte buffer[length];
      Serial.readBytes(buffer, length);

      digitalWrite(D8, LOW);
      SPI.transfer(0x06); // Write Enable
      digitalWrite(D8, HIGH);
      delay(5);
      digitalWrite(D8, LOW);
      SPI.transfer(0x02); // Page Program
      SPI.transfer((address >> 16) & 0xFF);
      SPI.transfer((address >> 8) & 0xFF);
      SPI.transfer(address & 0xFF);
      for (int i = 0; i < length; i++) {
        SPI.transfer(buffer[i]);
      }
      digitalWrite(D8, HIGH);
    } else if (command == 'E') { // Erase Chip
      digitalWrite(D8, LOW);
      SPI.transfer(0x06); // Write Enable
      digitalWrite(D8, HIGH);
      delay(5);
      digitalWrite(D8, LOW);
      SPI.transfer(0xC7); // Chip Erase
      digitalWrite(D8, HIGH);
      // Wait for erase to complete - this can take a while
      delay(5000);
    }
  }
}
