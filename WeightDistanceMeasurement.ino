#include "HX711.h"

// Define pins for analog sensor
const int distanceSensorRaw[] = {A0};
float distanceArray[1];
const int numbAverageVoltages = 50;
const float operatingVoltage = 5.0;

// Define pins for Load Cell
#define loadCellDOUTPin 4
#define loadCellSCKPin 5

HX711 scale;

void setup() {
  // Initialize Serial communication
  Serial.begin(9600);
  Serial.println("Sensors Initialized. Waiting for Python signal...");

  // Initialize Load Cell
  scale.begin(loadCellDOUTPin, loadCellSCKPin);
  scale.set_scale(-427.7005); // Adjust scale factor based on calibration
  scale.tare();
}

void loop() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    if (command == "start") {
      Serial.println("Recording started...");
      for (int i = 0; i < 10; i++) {
        // Distance Reading from Analog Sensor
        readDistance(0);

        // Load Cell Reading
        float weight = scale.get_units(5);

        // Print Analog Distance Reading
        Serial.print("Distance: ");
        Serial.print(distanceArray[0]);
        Serial.println(" cm");

        // Print Load Cell Reading
        Serial.print("Weight: ");
        Serial.print(weight);
        Serial.println(" units");

        delay(500); // Adjust delay between readings
      }
      Serial.println("Done");
    }
  }
}

void readDistance(int sensor) { //Adapted from robojax.com
  float temporaryVoltage = 0; // Temporary average value
  for (int i = 0; i < numbAverageVoltages; i++) {
    int sensorValue = analogRead(distanceSensorRaw[sensor]);
    delay(1);

    temporaryVoltage += sensorValue * (operatingVoltage / 1023.0); // Convert to voltage
  }
  temporaryVoltage /= numbAverageVoltages;

  // Polynomial distance calculation
  distanceArray[sensor] = (33.9 + -69.5 * (temporaryVoltage) +
                     62.3 * pow(temporaryVoltage, 2) +
                     -25.4 * pow(temporaryVoltage, 3) +
                     3.83 * pow(temporaryVoltage, 4))*10.0;
}
