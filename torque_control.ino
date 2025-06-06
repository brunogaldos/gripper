/**
* Torque control example of adaptive gripper with Z-axis median filter. Based on SimpleFOC library.
*/
#include "TLE5012Sensor.h"
#include "TLx493D_inc.hpp"
#include "config.h"
#include <SimpleFOC.h>


bool autoMode=false;

// define SPI pins for TLE5012 sensor
#define PIN_SPI1_SS0 94    // Chip Select (CS) pin
#define PIN_SPI1_MOSI 69   // MOSI pin
#define PIN_SPI1_MISO 95   // MISO pin
#define PIN_SPI1_SCK 68    // SCK pin

// create an instance of SPIClass3W for 3-wire SPI communication
tle5012::SPIClass3W tle5012::SPI3W1(2);
// create an instance of TLE5012Sensor
TLE5012Sensor tle5012Sensor(&SPI3W1, PIN_SPI1_SS0, PIN_SPI1_MISO, PIN_SPI1_MOSI, PIN_SPI1_SCK);

// BLDC motor instance: (polepairs, resistance, KV, inductance)
BLDCMotor motor = BLDCMotor(7, 0.24, 360, 0.000133);
// BLDC driver instance
const int U = 11, V = 10, W = 9;
const int EN_U = 6, EN_V = 5, EN_W = 3;
BLDCDriver3PWM driver = BLDCDriver3PWM(U, V, W, EN_U, EN_V, EN_W);

// Torque control variable
float target_voltage = -1;

#if ENABLE_MAGNETIC_SENSOR
using namespace ifx::tlx493d;
TLx493D_A2B6 dut(Wire1, TLx493D_IIC_ADDR_A0_e);
// Calibration samples and offsets
const int CALIBRATION_SAMPLES = 20;
double xOffset = 0, yOffset = 0, zOffset = 0;

// Median filter configuration
const uint8_t MEDIAN_WINDOW_SIZE = 5;          // must be odd
static double zBuffer[MEDIAN_WINDOW_SIZE];
static uint8_t zIndex = 0;
static bool bufferFilled = false;
static bool closeCommandReceived = false;
// Helper: insertion sort for median
void insertionSort(double arr[], int n) {
  for (int i = 1; i < n; i++) {
    double key = arr[i];
    int j = i - 1;
    while (j >= 0 && arr[j] > key) {
      arr[j + 1] = arr[j];
      j--;
    }
    arr[j + 1] = key;
  }
}
#endif

#if ENABLE_COMMANDER
Commander command = Commander(Serial);
void doTarget(char *cmd) { command.scalar(&target_voltage, cmd); }
#endif

void setup() {
  Serial.begin(115200);
  SimpleFOCDebug::enable(&Serial);

  // Initialise magnetic sensor hardware
  tle5012Sensor.init();
  motor.linkSensor(&tle5012Sensor);

  // Driver setup
  driver.voltage_power_supply = 12;
  driver.voltage_limit = 6;
  if (!driver.init()) {
    Serial.println("Driver init failed!");
    return;
  }
  motor.linkDriver(&driver);

  // FOC and control setup
  motor.voltage_sensor_align = 2;
  motor.foc_modulation = FOCModulationType::SpaceVectorPWM;
  motor.controller = MotionControlType::torque;
  motor.init();
  motor.initFOC();
  Serial.println(F("Motor ready."));

  #if ENABLE_MAGNETIC_SENSOR
  // begin 3D magnetic sensor & calibrate
  dut.begin();
  calibrateSensor();
  Serial.println("3D magnetic sensor calibration completed.");
  pinMode(BUTTON1, INPUT);
  pinMode(BUTTON2, INPUT);
  #endif

  Serial.println(F("Setup done."));
  #if ENABLE_COMMANDER
  command.add('T', doTarget, "target voltage");
  Serial.println(F("Set the target voltage using serial terminal."));
  #endif
  delay(1000);
}

void loop() {
  #if ENABLE_MAGNETIC_SENSOR
  static float lastZ = 0;
  static bool grabbingDetected = false;
  double x, y, z_raw;

  // Read raw magnetic field
  dut.setSensitivity(TLx493D_FULL_RANGE_e);
  dut.getMagneticField(&x, &y, &z_raw);

  // Apply calibration
  x -= xOffset;
  y -= yOffset;
  z_raw -= zOffset;



  // Add to median buffer
  zBuffer[zIndex] = z_raw;
  zIndex = (zIndex + 1) % MEDIAN_WINDOW_SIZE;
  if (!bufferFilled && zIndex == 0) bufferFilled = true;
  // Compute filtered Z
  double zFiltered = z_raw;


  if (bufferFilled) {
    double tmp[MEDIAN_WINDOW_SIZE];
    memcpy(tmp, zBuffer, sizeof(tmp));
    insertionSort(tmp, MEDIAN_WINDOW_SIZE);
    zFiltered = tmp[MEDIAN_WINDOW_SIZE / 2];
  }

  float zDeviation = abs(zFiltered);
  float zDiff = abs(zFiltered - lastZ);
  lastZ = zFiltered;

  if (Serial.available()) {
      String command = Serial.readStringUntil('\n');
      command.trim();
      if (command == "CLOSE") {
          closeCommandReceived = true;
          Serial.println("ECHO: CLOSE");  // Added space for consistency
      }
      else if (command == "OPEN") {  // Example for other commands
          Serial.println("ECHO: OPEN");
      }
  }

  
  const float softThreshold = 0.20;
  const float hardThreshold = 0.245;

  static float integral = 0;
  static float previous_error = 0;

  float kp = 2.5, ki = 0.5, kd = 0.1;
  float setpoint = 0.3;
  if (autoMode) {
    if (!grabbingDetected) {
      float error = setpoint - zDiff;
      integral += error;
      float derivative = error - previous_error;
      previous_error = error;

      target_voltage = kp * error + ki * integral + kd * derivative;
      target_voltage = constrain(target_voltage, -6, 0); // Negative torque only

      // Fallback: Ensure at least -3V closing force if PID is too gentle
      if (target_voltage > -3) {
        target_voltage = -3;
      }

      // Grabbing detection logic
      if (zDeviation > softThreshold && zDeviation < hardThreshold) {
        grabbingDetected = true;
        target_voltage = 0;
        Serial.println("STOP");
      }

    } else {
      target_voltage = 0;
    }
    
  /**
  if (!grabbingDetected) {
  if (zDeviation > grabbingThreshold) {
  grabbingDetected = true; // Object detected
  target_voltage = 0; // Stop motor
  } else {
  target_voltage = -3; // Continue closing
  }
  } else {
  target_voltage = 0; // Maintain hold
  }
  */


  // Debug output
  Serial.print("Raw Z: "); Serial.print(z_raw);
  Serial.print(" Filtered Z: "); Serial.print(zFiltered);
  Serial.print(" Deviation: "); Serial.println(zDeviation);

} else {
  // Manual Mode
  if (closeCommandReceived) {
    target_voltage = -3;  // Close gripper
    Serial.println("CLOSING");
  } else if (digitalRead(BUTTON2) == LOW) {
    target_voltage = 3;   // Open gripper
  } else {
    target_voltage = 0;   // Hold position
  }
}
  #endif

  // FOC control
  tle5012Sensor.update();
  motor.loopFOC();
  motor.move(target_voltage);

  #if ENABLE_COMMANDER
  command.run();
  #endif
}

#if ENABLE_MAGNETIC_SENSOR
void calibrateSensor() {
  double sumX = 0, sumY = 0, sumZ = 0;
  for (int i = 0; i < CALIBRATION_SAMPLES; ++i) {
    double tx, ty, tz, tmp;
    dut.getMagneticFieldAndTemperature(&tx, &ty, &tz, &tmp);
    sumX += tx;
    sumY += ty;
    sumZ += tz;
    delay(10);
  }
  xOffset = sumX / CALIBRATION_SAMPLES;
  yOffset = sumY / CALIBRATION_SAMPLES;
  zOffset = sumZ / CALIBRATION_SAMPLES;
}
#endif
