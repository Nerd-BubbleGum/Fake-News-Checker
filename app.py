/*
 * Dravyavraksh Environmental Monitoring System
 * 
 * Components:
 * - Arduino UNO
 * - DHT11 Temperature & Humidity Sensor
 * - MQ135 Gas Sensor (CO2 detection)
 * - SSD1306 OLED Display (128x64, I2C)
 * 
 * Features:
 * - Animated startup screen with "DravyaVraksh" text
 * - Real-time CO2 monitoring in PPM with realistic values
 * - Temperature reading (air temperature, not water - DHT11 limitation)
 * - Scanning mode for gas detection with trend analysis
 * - Visual indicators for air quality levels
 */

// Include required libraries
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <DHT.h>

// Pin definitions
#define DHT_PIN 2         // DHT11 data pin
#define MQ135_PIN A0      // MQ135 analog output pin

// Display settings
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// DHT11 sensor setup
#define DHT_TYPE DHT11
DHT dht(DHT_PIN, DHT_TYPE);

// MQ135 calibration constants (based on research)
#define RLOAD 22.0        // Load resistor value in KOhms (changed from default 1K to 22K for better accuracy)
#define RZERO 76.63       // Calibration resistance at atmospheric CO2 level
#define ATMOCO2 410.0     // Current atmospheric CO2 level (updated from 397 to 410 PPM)

// Global variables
float temperature_c;
float humidity;
float co2_ppm;
int raw_adc;
bool scanning_mode = false;
unsigned long last_scan_time = 0;
float co2_readings[10];  // Array to store last 10 readings for trend analysis
int reading_index = 0;
String air_quality_status = "";

// Air quality thresholds (based on research)
const float GOOD_AIR_MAX = 750.0;     // Good air quality: < 750 PPM
const float MODERATE_AIR_MAX = 1200.0; // Moderate: 750-1200 PPM
// Above 1200 PPM is considered harmful

void setup() {
  Serial.begin(9600);
  Serial.println(F("Initializing Dravyavraksh System..."));
  
  // Initialize DHT11
  dht.begin();
  
  // Initialize OLED display
  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("SSD1306 allocation failed"));
    for(;;); // Don't proceed, loop forever
  }
  
  // Show animated startup screen
  showStartupAnimation();
  
  // Initialize CO2 readings array
  for(int i = 0; i < 10; i++) {
    co2_readings[i] = ATMOCO2;
  }
  
  // Warm-up message
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println("Warming up sensors...");
  display.println("Please wait 30 seconds");
  display.display();
  
  // Sensor warm-up period
  delay(30000); // 30 second warm-up
  
  Serial.println(F("System initialized. Starting measurements..."));
}

void loop() {
  // Read all sensors
  readSensors();
  
  // Update CO2 trend analysis
  updateCO2Trend();
  
  // Check if scanning mode should be activated
  checkScanningMode();
  
  // Update display
  updateDisplay();
  
  // Print to serial for debugging
  printToSerial();
  
  // Delay between readings
  delay(2000);
}

void showStartupAnimation() {
  display.clearDisplay();
  
  // Animated text reveal for "DravyaVraksh"
  String projectName = "DravyaVraksh";
  
  // Calculate center position
  int textWidth = projectName.length() * 12; // Approximate width for size 2 text
  int startX = (SCREEN_WIDTH - textWidth) / 2;
  int startY = (SCREEN_HEIGHT - 16) / 2; // Height for size 2 text is ~16 pixels
  
  display.setTextSize(2);
  display.setTextColor(SSD1306_WHITE);
  
  // Animate each character appearing
  for(int i = 0; i <= projectName.length(); i++) {
    display.clearDisplay();
    display.setCursor(startX, startY);
    
    // Print characters up to current index
    for(int j = 0; j < i; j++) {
      display.print(projectName.charAt(j));
    }
    
    // Add blinking cursor effect
    if(i < projectName.length()) {
      display.print("_");
    }
    
    display.display();
    delay(150); // Speed of animation
  }
  
  // Hold the complete name for 2 seconds
  delay(2000);
  
  // Fade out effect (simulate by clearing sections)
  for(int fade = 0; fade < 4; fade++) {
    display.clearDisplay();
    if(fade < 3) {
      display.setTextSize(2);
      display.setCursor(startX, startY);
      display.print(projectName);
    }
    display.display();
    delay(300);
  }
}

void readSensors() {
  // Read DHT11 sensor
  humidity = dht.readHumidity();
  temperature_c = dht.readTemperature();
  
  // Check if DHT11 readings are valid
  if (isnan(humidity) || isnan(temperature_c)) {
    Serial.println(F("Failed to read from DHT sensor!"));
    humidity = 0;
    temperature_c = 0;
  }
  
  // Read MQ135 sensor
  raw_adc = analogRead(MQ135_PIN);
  
  // Convert ADC reading to CO2 PPM using improved formula
  co2_ppm = calculateCO2PPM(raw_adc);
}

float calculateCO2PPM(int adc_reading) {
  // Convert ADC reading to voltage
  float voltage = (adc_reading / 1023.0) * 5.0;
  
  // Calculate sensor resistance
  float sensor_resistance = ((5.0 - voltage) / voltage) * RLOAD;
  
  // Calculate Rs/R0 ratio
  float ratio = sensor_resistance / RZERO;
  
  // Convert ratio to CO2 PPM using MQ135 characteristic curve
  // Formula derived from datasheet: PPM = 116.6020682 * pow(ratio, -2.769034857)
  float ppm = 116.6020682 * pow(ratio, -2.769034857);
  
  // Apply atmospheric CO2 correction
  ppm = ppm + ATMOCO2;
  
  // Constrain to realistic values (300-5000 PPM)
  ppm = constrain(ppm, 300, 5000);
  
  return ppm;
}

void updateCO2Trend() {
  // Store current reading in circular buffer
  co2_readings[reading_index] = co2_ppm;
  reading_index = (reading_index + 1) % 10;
  
  // Calculate trend (average of last 5 vs previous 5 readings)
  float recent_avg = 0;
  float previous_avg = 0;
  
  for(int i = 0; i < 5; i++) {
    recent_avg += co2_readings[(reading_index - 1 - i + 10) % 10];
    previous_avg += co2_readings[(reading_index - 6 - i + 10) % 10];
  }
  
  recent_avg /= 5;
  previous_avg /= 5;
  
  // Determine air quality status
  if(co2_ppm <= GOOD_AIR_MAX) {
    air_quality_status = "GOOD";
  } else if(co2_ppm <= MODERATE_AIR_MAX) {
    air_quality_status = "MODERATE";
  } else {
    air_quality_status = "HARMFUL";
  }
}

void checkScanningMode() {
  // Activate scanning mode if CO2 levels are changing significantly
  float current_reading = co2_ppm;
  static float last_stable_reading = co2_ppm;
  static unsigned long last_change_time = millis();
  
  // Check if reading has changed by more than 50 PPM
  if(abs(current_reading - last_stable_reading) > 50) {
    scanning_mode = true;
    last_scan_time = millis();
    last_change_time = millis();
    last_stable_reading = current_reading;
  }
  
  // Exit scanning mode after 30 seconds of stable readings
  if(scanning_mode && (millis() - last_scan_time > 30000)) {
    scanning_mode = false;
  }
}

void updateDisplay() {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  
  // Title
  display.setCursor(0, 0);
  display.print("DravyaVraksh Monitor");
  
  // CO2 reading with scanning indicator
  display.setCursor(0, 12);
  display.print("CO2: ");
  display.print((int)co2_ppm);
  display.print(" PPM");
  
  if(scanning_mode) {
    // Blinking scanning indicator
    if((millis() / 500) % 2) {
      display.print(" *SCAN*");
    }
  }
  
  // Air quality status
  display.setCursor(0, 24);
  display.print("Air: ");
  display.print(air_quality_status);
  
  // Temperature reading
  display.setCursor(0, 36);
  display.print("Temp: ");
  display.print(temperature_c, 1);
  display.print("C");
  
  // Humidity reading
  display.setCursor(0, 48);
  display.print("Humidity: ");
  display.print(humidity, 0);
  display.print("%");
  
  // Status bar at bottom
  display.setCursor(0, 56);
  if(scanning_mode) {
    display.print("Scanning for changes...");
  } else {
    display.print("Monitoring stable");
  }
  
  display.display();
}

void printToSerial() {
  Serial.print("CO2: ");
  Serial.print(co2_ppm, 1);
  Serial.print(" PPM | Temp: ");
  Serial.print(temperature_c, 1);
  Serial.print("C | Humidity: ");
  Serial.print(humidity, 1);
  Serial.print("% | ADC: ");
  Serial.print(raw_adc);
  Serial.print(" | Air Quality: ");
  Serial.print(air_quality_status);
  
  if(scanning_mode) {
    Serial.print(" | SCANNING");
  }
  
  Serial.println();
}
