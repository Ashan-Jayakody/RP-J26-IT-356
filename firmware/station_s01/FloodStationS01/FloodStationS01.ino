#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <SPI.h>
#include <LoRa.h>
#include <Preferences.h>
#include <time.h>
#include "secrets.h.ino"

// =====================================================
// NETWORK CONFIGURATION
// =====================================================
const int LOCAL_PORT = 1883;
const char* LOCAL_BROKER = "192.168.163.126";
const char* LOCAL_USERNAME = "flood_station";

// Replace this placeholder with your NEW Mosquitto password locally.
const char* LOCAL_PASSWORD = "Flood2026";

const int AWS_PORT = 8883;
const char* MQTT_TOPIC = "flood/v1/stations/S01/telemetry";
const char* AWS_CLIENT_ID = "ESP32-S01";

// =====================================================
// HARDWARE PINS
// =====================================================
#define TRIG_PIN        13
#define ECHO_PIN        34
#define RAIN_AO_PIN     35
#define FLOW_SENSOR_PIN 27

#define LORA_SCK        18
#define LORA_MISO       19
#define LORA_MOSI       23
#define LORA_SS          5
#define LORA_RST        14
#define LORA_DIO0       26

#define CAL_BUTTON_PIN   0

// =====================================================
// SENSOR CONFIGURATION
// =====================================================
const float SENSOR_MIN_CM = 25.0;
const float SENSOR_MAX_CM = 200.0;
const float CAL_STABILITY_CM = 2.0;

const int RAIN_WET_THRESHOLD = 3100;
const int RAIN_LIGHT_THRESHOLD = 3800;
const bool RAIN_WET_VALUE_IS_LOW = true;

const float FLOW_PULSES_PER_LITER = 450.0f;

const unsigned long FLOW_CALC_INTERVAL_MS = 1000;
const unsigned long FLOW_STOP_TIMEOUT_MS = 3000;

// =====================================================
// GLOBAL VARIABLES
// =====================================================
Preferences preferences;

float sensorToBottomCm = 0.0;
float maxLevelCm = 0.0;

float lastValidDistance = -1.0;
float lastValidWaterLevel = 0.0;

unsigned long packetNumber = 0;
unsigned long lastWifiAttempt = 0;
unsigned long lastAwsAttempt = 0;
unsigned long lastLocalAttempt = 0;
unsigned long lastNtpAttempt = 0;

// Wi-Fi reconnect management
bool wifiConnecting = false;
unsigned long wifiConnectStarted = 0;

bool timeSynced = false;

WiFiClientSecure secureClient;
PubSubClient awsMqtt(secureClient);

WiFiClient espClient;
PubSubClient localMqtt(espClient);

// =====================================================
// FLOW SENSOR - ZJ-S201
// =====================================================
volatile uint32_t flowPulseCount = 0;

uint32_t lastFlowPulseSnapshot = 0;
unsigned long lastFlowCalcMs = 0;
unsigned long lastFlowPulseSeenMs = 0;

float flowRateLMin = 0.0f;
float flowTotalLiters = 0.0f;

void IRAM_ATTR flowPulseISR() {
  flowPulseCount++;
}

uint32_t getFlowPulseSnapshot() {
  noInterrupts();
  uint32_t pulses = flowPulseCount;
  interrupts();
  return pulses;
}

void updateFlowMeasurements() {
  unsigned long now = millis();
  uint32_t currentPulses = getFlowPulseSnapshot();

  flowTotalLiters =
      (float)currentPulses / FLOW_PULSES_PER_LITER;

  if (lastFlowCalcMs == 0) {
    lastFlowCalcMs = now;
    lastFlowPulseSnapshot = currentPulses;
    lastFlowPulseSeenMs = now;
    flowRateLMin = 0.0f;
    return;
  }

  if (currentPulses != lastFlowPulseSnapshot) {
    lastFlowPulseSeenMs = now;
  }

  unsigned long elapsedMs = now - lastFlowCalcMs;

  if (elapsedMs >= FLOW_CALC_INTERVAL_MS) {
    uint32_t pulseDifference =
        currentPulses - lastFlowPulseSnapshot;

    if (pulseDifference > 0) {
      flowRateLMin =
          ((float)pulseDifference * 60000.0f) /
          (FLOW_PULSES_PER_LITER * (float)elapsedMs);
    } else if (now - lastFlowPulseSeenMs >= FLOW_STOP_TIMEOUT_MS) {
      flowRateLMin = 0.0f;
    }

    Serial.print("[FLOW DEBUG] Total pulses: ");
    Serial.print(currentPulses);
    Serial.print(" | New pulses: ");
    Serial.print(pulseDifference);
    Serial.print(" | Interval: ");
    Serial.print(elapsedMs);
    Serial.print(" ms | Rate: ");
    Serial.print(flowRateLMin, 3);
    Serial.println(" L/min");

    lastFlowPulseSnapshot = currentPulses;
    lastFlowCalcMs = now;
  }
}

void printFlowDiagnostics() {
  uint32_t pulses = getFlowPulseSnapshot();

  Serial.print("[FLOW] Pulses: ");
  Serial.print(pulses);
  Serial.print(" | Rate: ");
  Serial.print(flowRateLMin, 3);
  Serial.print(" L/min | Total: ");
  Serial.print(flowTotalLiters, 3);
  Serial.println(" L");
}

// =====================================================
// WIFI
// =====================================================

// Start one Wi-Fi connection attempt without blocking setup.
void connectWiFi() {
  Serial.print("[WiFi] Starting connection to: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);

  wifiConnecting = true;
  wifiConnectStarted = millis();
  lastWifiAttempt = millis();

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

// Manage Wi-Fi without repeatedly calling begin/reconnect
// while a connection attempt is already active.
void maintainWiFi() {
  wl_status_t status = WiFi.status();

  if (status == WL_CONNECTED) {
    if (wifiConnecting) {
      Serial.println("[WiFi] Connected successfully.");
      Serial.print("[WiFi] IP address: ");
      Serial.println(WiFi.localIP());
    }

    wifiConnecting = false;
    return;
  }

  unsigned long now = millis();

  // An attempt is in progress: do not start another one.
  if (wifiConnecting) {
    if (now - wifiConnectStarted < 15000) {
      return;
    }

    wifiConnecting = false;
    lastWifiAttempt = now;

    Serial.println("[WiFi] Connection attempt timed out.");
    Serial.println("[WiFi] Waiting before retry.");
    return;
  }

  // Wait 10 seconds between attempts.
  if (now - lastWifiAttempt < 10000) {
    return;
  }

  Serial.print("[WiFi] Retrying connection to: ");
  Serial.println(WIFI_SSID);

  wifiConnecting = true;
  wifiConnectStarted = now;
  lastWifiAttempt = now;

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

// =====================================================
// NTP TIME SYNCHRONIZATION
// =====================================================
void syncTime() {
  if (timeSynced || WiFi.status() != WL_CONNECTED) return;

  if (lastNtpAttempt != 0 &&
      millis() - lastNtpAttempt < 30000) {
    return;
  }

  lastNtpAttempt = millis();

  Serial.println("[NTP] Synchronizing time...");

  configTime(0, 0, "pool.ntp.org", "time.nist.gov");

  unsigned long start = millis();
  time_t now = time(nullptr);

  while (now < 24 * 3600 &&
         millis() - start < 10000) {
    delay(250);
    now = time(nullptr);
  }

  timeSynced = (now >= 24 * 3600);

  if (timeSynced) {
    Serial.print("[NTP] Time synchronized. Epoch: ");
    Serial.println((long)now);
  } else {
    Serial.println("[NTP] Sync failed; retrying later.");
  }
}

// =====================================================
// AWS TLS SETUP
// =====================================================
void setupAWS() {
  Serial.println();
  Serial.println("===== AWS TLS CONFIGURATION =====");

  secureClient.setCACert(AWS_ROOT_CA);
  Serial.println("[TLS] Root CA configured.");

  secureClient.setCertificate(DEVICE_CERT);
  Serial.println("[TLS] Device certificate configured.");

  secureClient.setPrivateKey(PRIVATE_KEY);
  Serial.println("[TLS] Private key configured.");

  awsMqtt.setServer(AWS_IOT_ENDPOINT, AWS_PORT);
  awsMqtt.setBufferSize(512);
  awsMqtt.setKeepAlive(60);
  awsMqtt.setSocketTimeout(5);

  Serial.print("[AWS] Endpoint: ");
  Serial.println(AWS_IOT_ENDPOINT);

  Serial.print("[AWS] Port: ");
  Serial.println(AWS_PORT);

  Serial.print("[AWS] Topic: ");
  Serial.println(MQTT_TOPIC);

  Serial.println("[AWS] MQTT client configured.");
  Serial.println("=================================");
}

// =====================================================
// AWS MQTT CONNECTION
// =====================================================
void maintainAWS() {
  if (awsMqtt.connected()) return;

  if (WiFi.status() != WL_CONNECTED) {
    return;
  }

  if (!timeSynced) {
    Serial.println("[AWS DEBUG] Waiting for NTP time sync.");
    return;
  }

  if (lastAwsAttempt != 0 &&
      millis() - lastAwsAttempt < 5000) {
    return;
  }

  lastAwsAttempt = millis();

  Serial.println();
  Serial.println("[AWS] Connecting to AWS IoT Core...");
  Serial.print("[AWS] Client ID: ");
  Serial.println(AWS_CLIENT_ID);
  Serial.print("[AWS] Endpoint: ");
  Serial.println(AWS_IOT_ENDPOINT);

  if (awsMqtt.connect(AWS_CLIENT_ID)) {
    Serial.println("[AWS] MQTT CONNECTED.");
  } else {
    Serial.print("[AWS] MQTT connection FAILED. State code: ");
    Serial.println(awsMqtt.state());

    char errorBuffer[200] = {0};

    int errorCode = secureClient.lastError(
      errorBuffer,
      sizeof(errorBuffer)
    );

    Serial.print("[AWS] TLS/socket error code: ");
    Serial.println(errorCode);

    Serial.print("[AWS] TLS/socket details: ");
    Serial.println(errorBuffer);

    Serial.println(
      "[AWS] Check PEM format, matching certificate/key, "
      "certificate status, NTP and endpoint."
    );
  }
}

// =====================================================
// LOCAL MQTT SETUP
// =====================================================
void setupLocal() {
  localMqtt.setServer(LOCAL_BROKER, LOCAL_PORT);
  localMqtt.setBufferSize(512);
  localMqtt.setKeepAlive(60);
  localMqtt.setSocketTimeout(5);

  Serial.println("[LOCAL MQTT] Client configured.");
}

// =====================================================
// LOCAL MQTT CONNECTION
// =====================================================
void maintainLocal() {
  if (localMqtt.connected()) return;
  if (WiFi.status() != WL_CONNECTED) return;

  if (lastLocalAttempt != 0 &&
      millis() - lastLocalAttempt < 5000) {
    return;
  }

  lastLocalAttempt = millis();

  Serial.println("[LOCAL MQTT] Connecting...");

  String clientId = "ESP32-S01-LOCAL-";
  clientId += String(random(0xffff), HEX);

  if (localMqtt.connect(
        clientId.c_str(),
        LOCAL_USERNAME,
        LOCAL_PASSWORD)) {
    Serial.println("[LOCAL MQTT] CONNECTED.");
  } else {
    Serial.print("[LOCAL MQTT] Connection FAILED. State: ");
    Serial.println(localMqtt.state());
  }
}

// =====================================================
// ULTRASONIC SENSOR
// =====================================================
float readDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(3);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);

  digitalWrite(TRIG_PIN, LOW);

  unsigned long duration = pulseIn(ECHO_PIN, HIGH, 30000UL);

  if (duration == 0) {
    Serial.println("[DEBUG] No ECHO pulse received.");
    return -1.0;
  }

  float distance = duration * 0.0343f / 2.0f;

  Serial.print("[DEBUG] Raw distance: ");
  Serial.print(distance, 2);
  Serial.println(" cm");

  if (distance <= 0 || distance > SENSOR_MAX_CM) {
    Serial.println("[DEBUG] Distance outside sensor range.");
    return -1.0;
  }

  return distance;
}

// =====================================================
// MEDIAN FILTER
// =====================================================
float readDistanceMedian() {
  const int N = 7;
  float samples[N];
  int count = 0;

  for (int i = 0; i < N; i++) {
    float d = readDistance();

    if (d > 0 && d <= SENSOR_MAX_CM) {
      samples[count++] = d;
    }

    delay(60);
  }

  if (count < 3) {
    Serial.println("[DEBUG] Not enough valid distance samples.");
    return -1.0;
  }

  for (int i = 1; i < count; i++) {
    float key = samples[i];
    int j = i - 1;

    while (j >= 0 && samples[j] > key) {
      samples[j + 1] = samples[j];
      j--;
    }

    samples[j + 1] = key;
  }

  float median = samples[count / 2];

  Serial.print("[DEBUG] Median distance: ");
  Serial.print(median, 2);
  Serial.println(" cm");

  return median;
}

// =====================================================
// CALIBRATION
// =====================================================
void updateMaxLevel() {
  maxLevelCm = sensorToBottomCm - SENSOR_MIN_CM;
  if (maxLevelCm < 0) maxLevelCm = 0;
}

void saveCalibration(float bottomCm) {
  sensorToBottomCm = bottomCm;
  preferences.putFloat("bottom_v3", sensorToBottomCm);

  updateMaxLevel();

  lastValidDistance = sensorToBottomCm;
  lastValidWaterLevel = 0.0;

  Serial.println();
  Serial.println("===== CALIBRATION SAVED =====");

  Serial.print("Sensor-to-bottom: ");
  Serial.print(sensorToBottomCm, 2);
  Serial.println(" cm");

  Serial.print("Maximum measurable water level: ");
  Serial.print(maxLevelCm, 2);
  Serial.println(" cm");

  Serial.println("=============================");
}

bool calibrateEmptyBucket() {
  Serial.println();
  Serial.println("[CAL] Ensure the bucket is EMPTY and still.");
  Serial.println("[CAL] Collecting samples...");

  float readings[5];
  int count = 0;

  for (int i = 0; i < 5; i++) {
    float d = readDistanceMedian();

    if (d >= SENSOR_MIN_CM && d <= SENSOR_MAX_CM) {
      readings[count++] = d;
    } else {
      Serial.println("[CAL] Sample outside usable range.");
    }

    delay(100);
  }

  if (count < 3) {
    Serial.println("[CAL] FAILED: Not enough usable samples.");
    return false;
  }

  float minimum = readings[0];
  float maximum = readings[0];
  float sum = 0.0;

  for (int i = 0; i < count; i++) {
    if (readings[i] < minimum) minimum = readings[i];
    if (readings[i] > maximum) maximum = readings[i];
    sum += readings[i];
  }

  if (maximum - minimum > CAL_STABILITY_CM) {
    Serial.println("[CAL] FAILED: Readings are unstable.");
    return false;
  }

  saveCalibration(sum / count);
  return true;
}

void showCalibration() {
  Serial.print("[CAL] Bottom distance: ");
  Serial.print(sensorToBottomCm, 2);

  Serial.print(" cm | Maximum level: ");
  Serial.print(maxLevelCm, 2);
  Serial.println(" cm");
}

// =====================================================
// CALIBRATION BUTTON AND SERIAL COMMANDS
// =====================================================
void checkCalButton() {
  if (digitalRead(CAL_BUTTON_PIN) != LOW) return;

  unsigned long pressStart = millis();

  while (digitalRead(CAL_BUTTON_PIN) == LOW) {
    updateFlowMeasurements();

    if (millis() - pressStart >= 3000) {
      Serial.println("[CAL] Release button to calibrate.");

      while (digitalRead(CAL_BUTTON_PIN) == LOW) {
        updateFlowMeasurements();
        delay(10);
      }

      calibrateEmptyBucket();
      return;
    }

    delay(10);
  }
}

void handleSerialCommands() {
  if (!Serial.available()) return;

  String cmd = Serial.readStringUntil('\n');
  cmd.trim();
  cmd.toUpperCase();

  if (cmd == "CAL") {
    calibrateEmptyBucket();
  } else if (cmd == "SHOW") {
    showCalibration();
  } else if (cmd.length() > 0) {
    Serial.println("Commands: CAL or SHOW");
  }
}

void smartDelay(unsigned long ms) {
  unsigned long start = millis();

  while (millis() - start < ms) {
    updateFlowMeasurements();
    checkCalButton();
    handleSerialCommands();
    delay(20);
  }
}

// =====================================================
// RAIN SENSOR
// =====================================================
String getRainStatusFromAO(int rainAO) {
  if (RAIN_WET_VALUE_IS_LOW) {
    if (rainAO < RAIN_WET_THRESHOLD) return "WET";
    if (rainAO < RAIN_LIGHT_THRESHOLD) return "LIGHT";
    return "DRY";
  } else {
    if (rainAO > RAIN_WET_THRESHOLD) return "WET";
    if (rainAO > RAIN_LIGHT_THRESHOLD) return "LIGHT";
    return "DRY";
  }
}

// =====================================================
// WATER LEVEL MEASUREMENT
// =====================================================
void measureWaterLevel(
  float &waterLevel,
  float &distanceToSend,
  bool &distanceValid
) {
  float distance = readDistanceMedian();

  distanceValid = false;
  distanceToSend = -1.0;
  waterLevel = lastValidWaterLevel;

  if (distance < 0) {
    Serial.println("[LEVEL] No valid echo; holding last reading.");
    return;
  }

  if (distance >= SENSOR_MIN_CM &&
      distance <= sensorToBottomCm + CAL_STABILITY_CM) {

    float calculatedLevel = sensorToBottomCm - distance;

    if (calculatedLevel < 0) calculatedLevel = 0;
    if (calculatedLevel > maxLevelCm) calculatedLevel = maxLevelCm;

    waterLevel = calculatedLevel;
    lastValidDistance = distance;
    lastValidWaterLevel = waterLevel;

    distanceToSend = distance;
    distanceValid = true;
    return;
  }

  if (distance > 0 && distance < SENSOR_MIN_CM) {
    Serial.println("[LEVEL] Surface closer than configured minimum.");

    waterLevel = maxLevelCm;
    lastValidWaterLevel = waterLevel;

    distanceToSend = distance;
    distanceValid = true;
    return;
  }

  Serial.print("[LEVEL] Echo outside calibrated bucket range. ");
  Serial.print("Measured: ");
  Serial.print(distance, 2);
  Serial.print(" cm; bottom: ");
  Serial.print(sensorToBottomCm, 2);
  Serial.println(" cm. Holding last reading.");
}

void printWaterDiagnostics(
  float distance,
  bool distanceValid,
  float waterLevel,
  float levelPct
) {
  Serial.print("[LEVEL] Distance: ");

  if (distanceValid) {
    Serial.print(distance, 2);
    Serial.print(" cm");
  } else {
    Serial.print("INVALID");
  }

  Serial.print(" | Bottom: ");
  Serial.print(sensorToBottomCm, 2);

  Serial.print(" cm | Water: ");
  Serial.print(waterLevel, 2);

  Serial.print(" / ");
  Serial.print(maxLevelCm, 2);

  Serial.print(" cm (");
  Serial.print(levelPct, 0);
  Serial.println("%)");
}

// =====================================================
// SETUP
// =====================================================
void setup() {
  Serial.begin(115200);
  Serial.setTimeout(100);
  delay(1500);

  Serial.println();
  Serial.println("==================================");
  Serial.println("FLOOD STATION S01 - INITIALIZING");
  Serial.println("==================================");

  pinMode(TRIG_PIN, OUTPUT);
  digitalWrite(TRIG_PIN, LOW);

  pinMode(ECHO_PIN, INPUT);
  pinMode(RAIN_AO_PIN, INPUT);
  pinMode(CAL_BUTTON_PIN, INPUT_PULLUP);

  pinMode(FLOW_SENSOR_PIN, INPUT_PULLUP);

  attachInterrupt(
    digitalPinToInterrupt(FLOW_SENSOR_PIN),
    flowPulseISR,
    FALLING
  );

  Serial.println("[FLOW] ZJ-S201 enabled on GPIO 27.");

  analogReadResolution(12);
  analogSetPinAttenuation(RAIN_AO_PIN, ADC_11db);

  // LoRa
  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_SS);
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);

  if (!LoRa.begin(433E6)) {
    Serial.println("[ERROR] LoRa initialization failed!");
    while (true) delay(1000);
  }

  Serial.println("[LoRa] READY.");

  // Load stored calibration.
  preferences.begin("flood", false);
  sensorToBottomCm = preferences.getFloat("bottom_v3", 0.0);

  if (sensorToBottomCm <= SENSOR_MIN_CM ||
      sensorToBottomCm > SENSOR_MAX_CM) {
    Serial.println("[CAL] No valid calibration found.");
    Serial.println("[CAL] Calibrate with an EMPTY bucket.");

    if (!calibrateEmptyBucket()) {
      Serial.println("[CAL] Failed. Send CAL after checking setup.");
    }
  } else {
    updateMaxLevel();
    lastValidDistance = sensorToBottomCm;
    lastValidWaterLevel = 0.0;

    Serial.println("[CAL] Stored calibration loaded.");
    showCalibration();
  }

  Serial.println("[CAL] Commands: CAL or SHOW.");

  // Start Wi-Fi without blocking the rest of setup.
  connectWiFi();

  setupAWS();
  setupLocal();

  // MQTT functions will connect after Wi-Fi and NTP are ready.
  maintainAWS();
  maintainLocal();

  lastFlowCalcMs = millis();
  lastFlowPulseSnapshot = getFlowPulseSnapshot();
  lastFlowPulseSeenMs = lastFlowCalcMs;
  flowRateLMin = 0.0f;

  Serial.println();
  Serial.println("SYSTEM READY");
  Serial.println("[FLOW] Pulse counting is active.");
}

// =====================================================
// MAIN LOOP
// =====================================================
void loop() {
  checkCalButton();
  handleSerialCommands();

  updateFlowMeasurements();

  if (sensorToBottomCm <= SENSOR_MIN_CM ||
      sensorToBottomCm > SENSOR_MAX_CM) {
    printFlowDiagnostics();
    Serial.println("[LEVEL] Waiting for valid calibration.");
    smartDelay(2000);
    return;
  }

  maintainWiFi();
  syncTime();

  maintainAWS();
  maintainLocal();

  awsMqtt.loop();
  localMqtt.loop();

  // Rain sensor.
  int rainAO = analogRead(RAIN_AO_PIN);
  String rainStatus = getRainStatusFromAO(rainAO);

  Serial.print("[RAIN] AO: ");
  Serial.print(rainAO);
  Serial.print(" | Status: ");
  Serial.println(rainStatus);

  // Water level.
  float waterLevel = 0.0;
  float distanceToSend = -1.0;
  bool distanceValid = false;

  measureWaterLevel(
    waterLevel,
    distanceToSend,
    distanceValid
  );

  float levelPct = 0.0;

  if (maxLevelCm > 0.0) {
    levelPct = (waterLevel / maxLevelCm) * 100.0;
  }

  if (levelPct < 0) levelPct = 0;
  if (levelPct > 100) levelPct = 100;

  printWaterDiagnostics(
    distanceToSend,
    distanceValid,
    waterLevel,
    levelPct
  );

  updateFlowMeasurements();

  uint32_t flowPulses = getFlowPulseSnapshot();
  float flowRate = flowRateLMin;
  float totalLiters = flowTotalLiters;

  printFlowDiagnostics();

  packetNumber++;

  char jsonBuffer[448];

  int written = snprintf(
    jsonBuffer,
    sizeof(jsonBuffer),
    "{\"station_id\":\"S01\",\"packet\":%lu,"
    "\"water_level_cm\":%.2f,\"distance_cm\":%.2f,"
    "\"max_level_cm\":%.2f,\"level_pct\":%.0f,"
    "\"rain_raw\":%d,\"rain_status\":\"%s\","
    "\"flow_pulses\":%lu,"
    "\"flow_rate_l_min\":%.3f,"
    "\"flow_total_l\":%.3f}",
    packetNumber,
    waterLevel,
    distanceToSend,
    maxLevelCm,
    levelPct,
    rainAO,
    rainStatus.c_str(),
    (unsigned long)flowPulses,
    flowRate,
    totalLiters
  );

  if (written < 0 || written >= (int)sizeof(jsonBuffer)) {
    Serial.println("[ERROR] JSON buffer too small.");
    smartDelay(3000);
    return;
  }

  // LoRa transmission.
  LoRa.beginPacket();
  LoRa.print(jsonBuffer);
  int loraResult = LoRa.endPacket();

  Serial.print("LoRa SENT: ");
  Serial.println(jsonBuffer);

  if (loraResult == 0) {
    Serial.println("[WARNING] LoRa transmission failed.");
  }

  // AWS MQTT.
  Serial.print("AWS MQTT SENT: ");

  if (awsMqtt.connected()) {
    bool ok = awsMqtt.publish(MQTT_TOPIC, jsonBuffer);
    Serial.println(ok ? "SUCCESS" : "FAILED");

    if (!ok) {
      Serial.print("[AWS] Publish failed. MQTT state: ");
      Serial.println(awsMqtt.state());
    }
  } else {
    Serial.println("SKIPPED (not connected)");
  }

  // Local MQTT.
  Serial.print("LOCAL MQTT SENT: ");

  if (localMqtt.connected()) {
    bool ok = localMqtt.publish(MQTT_TOPIC, jsonBuffer);
    Serial.println(ok ? "SUCCESS" : "FAILED");
  } else {
    Serial.println("SKIPPED (not connected)");
  }

  Serial.println("--------------------------------");

  smartDelay(3000);
}
