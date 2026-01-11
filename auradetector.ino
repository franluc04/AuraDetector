// I2C Communication Library
#include <Wire.h>
// QMC5883L Sensor Library
#include <QMC5883LCompass.h>
// Std UART Communication Library
#include <SoftwareSerial.h>

// Initialize Magnetometer Object
QMC5883LCompass magnetometer;

// Define UART Communication With ESP32 (RX, TX : 10, 11)
SoftwareSerial SerialESP32(10, 11);

// Define Analog Pin For The Inductive Sensor
const int INDUCTIVE_PIN = A0;

// Base Ambient Magnetic Field Intensity (used for calibration)
long baseMagneticField = 0;

void setup() {

  // Initialize Serial Communication For ESP32 UART Transmission
  SerialESP32.begin(9600);

  // Initialize I2C Communication For The Magnetometer
  Wire.begin();

  // Initialize The QMC5883L Magnetometer Sensor
  magnetometer.init();

  // Configure Inductive Sensor Pin As Input
  pinMode(INDUCTIVE_PIN, INPUT);

  // Synchronization System For ESP32 Boot
  delay(3000);
  SerialESP32.println("");
  delay(100);

  // Send Initial Message Via UART
  SerialESP32.println("#######################################################");
  SerialESP32.println("[ARDUINO] Starting calibration... ");
  SerialESP32.println("Do not bring metal objects near the sensors!");
  SerialESP32.println("#######################################################");

  // Safety Calibration Delay Before Starting Calibration
  delay(2000);

  // Execute Effective Calibration
  calibrateBaseField();

  // Send Calibration Complete Message Via UART
  SerialESP32.println("######################################################");
  SerialESP32.println("Calibration completed!");
  SerialESP32.println("######################################################");
}

void loop() {

  // Check Inductive Sensor Status (Active LOW)
  int inductiveState = digitalRead(INDUCTIVE_PIN);

  // LOW -> Metallic Object Detected By Inductive Sensor
  if (inductiveState == LOW) {

    // Now Reading Magnetometer Value
    long currentMagneticField = readTotalMagneticField();

    // Calculate Abs Difference From Base Ambient Magnetic Field
    long difference = abs(currentMagneticField - baseMagneticField);

    // Send Difference Via UART
    SerialESP32.println(String(difference));

    // HIGH -> No Object Currently Detected
  } else {
    
    // Send Data Via UART
    SerialESP32.println("STATE: NOT-DETECTED");

  }

  // Sampling Frequency
  delay(250);
}

// Read Total Magnetic Field value (combining the 3 axes)
long readTotalMagneticField() {
  magnetometer.read();

  // Get Magnetic Field Data On X, Y, Z Axes
  long x = magnetometer.getX();
  long y = magnetometer.getY();
  long z = magnetometer.getZ();

  // Calculate The Total Magnetic Field Intensity (3D Pythagorean Theorem)
  long totalmag = sqrt(x * x + y * y + z * z);

  return totalmag;
}

// Calculate Average Over 50 Total Magnetic Field Intensity Readings
void calibrateBaseField() {
  long total = 0;
  int numReadings = 50;

  for (int i = 0; i < numReadings; i++) {
    total += readTotalMagneticField();
    delay(20);
  }
  baseMagneticField = total / numReadings;
}
