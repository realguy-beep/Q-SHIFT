// Q-SHIFT exhibition firmware E2.0.0.
// Target profile is an ESP32-WROOM-32 DevKit V1. Verify the physical board
// matches before building, wiring, powering, or flashing this firmware.
#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include <ArduinoJson.h>
#include <cstring>
#include <cstdio>
#include <esp_system.h>

#if !defined(QSHIFT_BOARD_PROFILE_CLASSIC_ESP32_DEVKIT_V1)
#error "Select and review a supported Q-SHIFT ESP32 board profile before building."
#endif

namespace {
constexpr char kFirmwareVersion[] = "2.0.0";
constexpr uint8_t kProtocolVersion = 1;
constexpr size_t kPixelCount = 17;
constexpr size_t kDataCount = 9;
constexpr size_t kCheckCount = 8;
constexpr size_t kFrameCount = 6;
constexpr size_t kMaxLine = 4096;
constexpr uint8_t kPixelBrightness = 48;  // 48/255; power supply still sized for full-white current.

// Classic ESP32-WROOM-32 DevKit V1 profile; GPIO 0/2/5/12/15, flash pins 6-11,
// and USB-UART pins 1/3 are deliberately not used.
constexpr int kPixelsPin = 18;
constexpr int kInjectButtonPin = 25;
constexpr int kDecodeButtonPin = 26;
constexpr int kResetButtonPin = 27;
constexpr int kConnectedLedPin = 22;
constexpr int kDisconnectedLedPin = 23;

constexpr uint32_t kDebounceMs = 50;
constexpr uint32_t kAckRetryMs = 800;
constexpr uint32_t kOfflineRetryMs = 2500;
constexpr uint32_t kHeartbeatMs = 2000;
constexpr uint32_t kConnectionTimeoutMs = 5500;
constexpr uint32_t kStateResponseTimeoutMs = 2500;
constexpr uint32_t kErrorPulseMs = 1800;
constexpr uint32_t kDecodeFlashMs = 420;

// E1 row-major data indicators: Stim qubits 1,3,5 / 8,10,12 / 15,17,19.
constexpr uint8_t kDataStimQubits[kDataCount] = {1, 3, 5, 8, 10, 12, 15, 17, 19};
// Check pixels 9..16 follow E1 check_sites order: 2,9,11,13,14,16,18,25.
constexpr uint8_t kCheckStimQubits[kCheckCount] = {2, 9, 11, 13, 14, 16, 18, 25};

struct ButtonInput {
  int pin;
  const char* name;
  bool rawHigh;
  bool stableHigh;
  uint32_t rawChangedAt;
};

struct CheckFrame {
  bool valid[kCheckCount]{};
  bool events[kCheckCount]{};
};

enum class PendingKind : uint8_t { None, Hello, Button };
enum class ButtonAction : uint8_t { Inject, Decode, Reset };

Adafruit_NeoPixel pixels(kPixelCount, kPixelsPin, NEO_GRB + NEO_KHZ800);
ButtonInput buttons[3] = {
    {kInjectButtonPin, "inject_error", true, true, 0},
    {kDecodeButtonPin, "decode", true, true, 0},
    {kResetButtonPin, "reset", true, true, 0},
};

char sessionId[48]{};
char pendingLine[512]{};
size_t pendingLength = 0;
uint32_t pendingSeq = 0;
uint32_t nextSeq = 0;
uint32_t pendingSentAt = 0;
uint32_t awaitingStateSince = 0;
uint8_t pendingAttempts = 0;
PendingKind pendingKind = PendingKind::None;
bool pendingAwaitingState = false;
bool connected = false;
bool haveState = false;
bool haveFrames = false;
bool haveFault = false;
bool lastDecoded = false;
uint8_t faultDataIndex = 0;
uint8_t displaySliceIndex = 0;
String phase = "idle";
CheckFrame frames[kFrameCount]{};
uint32_t lastValidRxAt = 0;
uint32_t nextHelloAt = 0;
uint32_t protocolErrors = 0;
uint32_t retransmissions = 0;
uint32_t reconnects = 0;
uint32_t droppedButtons = 0;
uint32_t txWouldBlock = 0;
uint32_t errorPulseUntil = 0;
uint32_t decodeFlashUntil = 0;

ButtonAction buttonQueue[4]{};
uint8_t queueHead = 0;
uint8_t queueSize = 0;
char inputLine[kMaxLine + 1]{};
size_t inputLength = 0;
bool discardUntilNewline = false;
uint32_t renderedFrameKey = 0xFFFFFFFF;

uint32_t color(uint8_t r, uint8_t g, uint8_t b) {
  return pixels.Color(r, g, b);
}

void sendPending(uint32_t now, bool retry);

bool elapsed(uint32_t now, uint32_t then, uint32_t interval) {
  return static_cast<uint32_t>(now - then) >= interval;
}

bool queueButton(ButtonAction action) {
  if (queueSize >= 4) {
    ++droppedButtons;
    return false;
  }
  const uint8_t index = static_cast<uint8_t>((queueHead + queueSize) % 4);
  buttonQueue[index] = action;
  ++queueSize;
  return true;
}

bool popButton(ButtonAction& action) {
  if (queueSize == 0) return false;
  action = buttonQueue[queueHead];
  queueHead = static_cast<uint8_t>((queueHead + 1) % 4);
  --queueSize;
  return true;
}

void dropQueuedButtons() {
  droppedButtons += queueSize;
  queueHead = 0;
  queueSize = 0;
}

const char* buttonName(ButtonAction action) {
  switch (action) {
    case ButtonAction::Inject: return "inject_error";
    case ButtonAction::Decode: return "decode";
    case ButtonAction::Reset: return "reset";
  }
  return "reset";
}

void createSessionId() {
  const uint64_t mac = ESP.getEfuseMac();
  const uint32_t bootNonce = esp_random();
  snprintf(sessionId, sizeof(sessionId), "e2-%08lx%04lx-%08lx",
           static_cast<unsigned long>((mac >> 16) & 0xFFFFFFFFULL),
           static_cast<unsigned long>(mac & 0xFFFFULL),
           static_cast<unsigned long>(bootNonce));
}

bool transmitLine(const char* line, size_t length) {
  if (Serial.availableForWrite() < static_cast<int>(length + 1)) {
    ++txWouldBlock;
    return false;
  }
  Serial.write(reinterpret_cast<const uint8_t*>(line), length);
  Serial.write(static_cast<uint8_t>('\n'));
  return true;
}

void setPending(JsonDocument& document, PendingKind kind, uint32_t seq, uint32_t now) {
  pendingLength = serializeJson(document, pendingLine, sizeof(pendingLine) - 1);
  if (pendingLength == 0 || pendingLength >= sizeof(pendingLine) - 1) {
    ++protocolErrors;
    errorPulseUntil = now + kErrorPulseMs;
    return;
  }
  pendingLine[pendingLength] = '\0';
  pendingSeq = seq;
  pendingKind = kind;
  pendingAttempts = 0;
  pendingAwaitingState = false;
  sendPending(now, false);
}

void sendPending(uint32_t now, bool retry) {
  if (pendingKind == PendingKind::None || pendingLength == 0) return;
  if (!transmitLine(pendingLine, pendingLength)) {
    pendingSentAt = now;  // Rate-limit local UART backpressure retries too.
    return;
  }
  pendingSentAt = now;
  if (pendingAttempts < 255) ++pendingAttempts;
  if (retry) ++retransmissions;
}

uint32_t reserveSeq() {
  // Start a new per-boot identity instead of wrapping an unsigned sequence.
  if (nextSeq >= 0xFFFFFF00UL) {
    ++protocolErrors;
    connected = false;
    return 0xFFFFFFFFUL;
  }
  return nextSeq++;
}

void sendHello(uint32_t now) {
  const uint32_t seq = reserveSeq();
  if (seq == 0xFFFFFFFFUL) return;
  JsonDocument document;
  document["v"] = kProtocolVersion;
  document["type"] = "hello";
  document["session_id"] = sessionId;
  document["seq"] = seq;
  JsonObject diag = document["diag"].to<JsonObject>();
  diag["fw"] = kFirmwareVersion;
  diag["retry"] = retransmissions;
  diag["bad_rx"] = protocolErrors;
  diag["reconnects"] = reconnects;
  diag["button_drops"] = droppedButtons;
  diag["tx_blocked"] = txWouldBlock;
  setPending(document, PendingKind::Hello, seq, now);
}

void sendButton(ButtonAction action, uint32_t now) {
  const uint32_t seq = reserveSeq();
  if (seq == 0xFFFFFFFFUL) return;
  JsonDocument document;
  document["v"] = kProtocolVersion;
  document["type"] = "button";
  document["session_id"] = sessionId;
  document["seq"] = seq;
  document["button"] = buttonName(action);
  setPending(document, PendingKind::Button, seq, now);
}

void triggerErrorPulse(uint32_t now) {
  errorPulseUntil = now + kErrorPulseMs;
}

bool parseState(JsonVariantConst state, uint32_t now) {
  if (!state.is<JsonObjectConst>()) return false;
  const char* newPhase = state["phase"].as<const char*>();
  if (newPhase == nullptr) return false;
  uint8_t newSlice = 0;
  if (state["display_slice_index"].is<uint8_t>()) {
    newSlice = state["display_slice_index"].as<uint8_t>();
  }
  if (newSlice >= kFrameCount) return false;

  bool newHaveFault = false;
  uint8_t newFaultIndex = 0;
  JsonVariantConst fault = state["fault_input"];
  if (!fault.isNull()) {
    if (!fault.is<JsonObjectConst>() || !fault["data_index"].is<uint8_t>()) return false;
    newFaultIndex = fault["data_index"].as<uint8_t>();
    if (newFaultIndex >= kDataCount) return false;
    newHaveFault = true;
  }

  CheckFrame newFrames[kFrameCount]{};
  bool newHaveFrames = false;
  JsonVariantConst frameValue = state["detector_frames"];
  if (!frameValue.isNull()) {
    if (!frameValue.is<JsonArrayConst>()) return false;
    JsonArrayConst frameArray = frameValue.as<JsonArrayConst>();
    if (frameArray.size() != kFrameCount) return false;
    for (JsonVariantConst item : frameArray) {
      if (!item.is<JsonObjectConst>() || !item["time_index"].is<uint8_t>()) return false;
      const uint8_t index = item["time_index"].as<uint8_t>();
      if (index >= kFrameCount || !item["valid"].is<JsonArrayConst>() ||
          !item["events"].is<JsonArrayConst>()) return false;
      JsonArrayConst valid = item["valid"].as<JsonArrayConst>();
      JsonArrayConst events = item["events"].as<JsonArrayConst>();
      if (valid.size() != kCheckCount || events.size() != kCheckCount) return false;
      for (uint8_t check = 0; check < kCheckCount; ++check) {
        if (!valid[check].is<bool>() || !events[check].is<bool>()) return false;
        newFrames[index].valid[check] = valid[check].as<bool>();
        newFrames[index].events[check] = events[check].as<bool>();
      }
    }
    newHaveFrames = true;
  }

  const bool decodedNow = (String(newPhase) == "decoded");
  if (decodedNow && !lastDecoded) decodeFlashUntil = now + kDecodeFlashMs;
  if (String(newPhase) == "idle") lastDecoded = false;
  else lastDecoded = decodedNow;
  phase = newPhase;
  displaySliceIndex = newSlice;
  haveFault = newHaveFault;
  faultDataIndex = newFaultIndex;
  haveFrames = newHaveFrames;
  if (newHaveFrames) memcpy(frames, newFrames, sizeof(frames));
  haveState = true;
  return true;
}

void processHostLine(const char* line, uint32_t now) {
  JsonDocument document;
  const DeserializationError error = deserializeJson(document, line);
  if (error) {
    ++protocolErrors;
    triggerErrorPulse(now);
    return;
  }
  if (document["v"] != kProtocolVersion || !document["type"].is<const char*>()) {
    ++protocolErrors;
    triggerErrorPulse(now);
    return;
  }
  const char* type = document["type"].as<const char*>();
  if (strcmp(type, "ack") == 0) {
    const char* reason = document["error"].as<const char*>();
    const bool sessionMatches = document["session_id"].isNull() ||
        (document["session_id"].is<const char*>() &&
         strcmp(document["session_id"].as<const char*>(), sessionId) == 0);
    if (!sessionMatches || !document["seq"].is<uint32_t>()) return;
    const uint32_t seq = document["seq"].as<uint32_t>();
    if (document["session_id"].isNull() &&
        !(pendingKind == PendingKind::Button && seq == pendingSeq && reason != nullptr &&
          strcmp(reason, "hello_required") == 0)) return;
    if (pendingKind != PendingKind::None && seq == pendingSeq) {
      const bool accepted = document["accepted"].as<bool>();
      if (!accepted) {
        ++protocolErrors;
        triggerErrorPulse(now);
        if (reason != nullptr && strcmp(reason, "hello_required") == 0 &&
            pendingKind == PendingKind::Button) {
          // A server restart cleared its in-memory session. Do not replay a
          // button into an unknown state; clear it, then perform a fresh hello.
          pendingKind = PendingKind::None;
          pendingLength = 0;
          pendingAwaitingState = false;
          connected = false;
          dropQueuedButtons();
          nextHelloAt = now;
          return;
        }
      }
      pendingKind = PendingKind::None;
      pendingLength = 0;
      pendingAwaitingState = true;
      awaitingStateSince = now;
    }
    lastValidRxAt = now;
    return;
  }
  if (strcmp(type, "state") == 0) {
    const char* responseSession = document["session_id"].as<const char*>();
    if (responseSession == nullptr || strcmp(responseSession, sessionId) != 0) {
      connected = false;
      pendingAwaitingState = false;
      dropQueuedButtons();
      nextHelloAt = now;
      return;
    }
    if (!parseState(document["state"], now)) {
      ++protocolErrors;
      triggerErrorPulse(now);
      connected = false;
      pendingAwaitingState = false;
      dropQueuedButtons();
      nextHelloAt = now;
      return;
    }
    const bool wasConnected = connected;
    connected = true;
    if (!wasConnected) ++reconnects;
    lastValidRxAt = now;
    pendingAwaitingState = false;
    renderedFrameKey = 0xFFFFFFFF;
    return;
  }
  ++protocolErrors;
  triggerErrorPulse(now);
}

void readHostSerial(uint32_t now) {
  while (Serial.available() > 0) {
    const int value = Serial.read();
    if (value < 0) break;
    const char byte = static_cast<char>(value);
    if (byte == '\n') {
      if (!discardUntilNewline && inputLength > 0) {
        inputLine[inputLength] = '\0';
        processHostLine(inputLine, now);
      } else if (discardUntilNewline) {
        ++protocolErrors;
        triggerErrorPulse(now);
      }
      inputLength = 0;
      discardUntilNewline = false;
    } else if (!discardUntilNewline && byte != '\r') {
      if (inputLength < kMaxLine) inputLine[inputLength++] = byte;
      else {
        inputLength = 0;
        discardUntilNewline = true;
      }
    }
  }
}

void sampleButtons(uint32_t now) {
  for (ButtonInput& button : buttons) {
    const bool rawHigh = digitalRead(button.pin) == HIGH;
    if (rawHigh != button.rawHigh) {
      button.rawHigh = rawHigh;
      button.rawChangedAt = now;
    }
    if (button.stableHigh != button.rawHigh && elapsed(now, button.rawChangedAt, kDebounceMs)) {
      button.stableHigh = button.rawHigh;
      if (!button.stableHigh) {
        if (!connected) {
          ++droppedButtons;  // Never replay a disconnected physical press later.
          triggerErrorPulse(now);
          continue;
        }
        const ButtonAction action = button.pin == kInjectButtonPin ? ButtonAction::Inject :
            button.pin == kDecodeButtonPin ? ButtonAction::Decode : ButtonAction::Reset;
        if (!queueButton(action)) triggerErrorPulse(now);
      }
    }
  }
}

void serviceLink(uint32_t now) {
  if (connected && elapsed(now, lastValidRxAt, kConnectionTimeoutMs)) {
    connected = false;
    dropQueuedButtons();
  }
  if (pendingAwaitingState && elapsed(now, awaitingStateSince, kStateResponseTimeoutMs)) {
    pendingAwaitingState = false;
    connected = false;
    dropQueuedButtons();
    nextHelloAt = now;
  }

  if (pendingKind != PendingKind::None) {
    const uint32_t interval = pendingAttempts >= 4 ? kOfflineRetryMs : kAckRetryMs;
    if (!pendingAwaitingState && elapsed(now, pendingSentAt, interval)) {
      if (pendingAttempts >= 4) {
        connected = false;
        dropQueuedButtons();
      }
      sendPending(now, true);  // Byte-identical payload and identical sequence.
    }
    return;
  }
  if (pendingAwaitingState) return;

  if (queueSize > 0 && connected) {
    ButtonAction action;
    if (popButton(action)) sendButton(action, now);
    return;
  }

  const uint32_t helloInterval = connected ? kHeartbeatMs : 1000;
  if (nextHelloAt == 0 || elapsed(now, nextHelloAt, helloInterval)) {
    sendHello(now);
    nextHelloAt = now;
  }
}

uint32_t stateHash() {
  uint32_t value = static_cast<uint32_t>(displaySliceIndex) | (haveState ? 1UL << 4 : 0);
  value |= (haveFault ? static_cast<uint32_t>(faultDataIndex + 1) : 0) << 5;
  value |= (phase == "decoded" ? 1UL << 10 : 0);
  value |= (haveFrames ? 1UL << 11 : 0);
  for (uint8_t i = 0; i < kCheckCount; ++i) {
    if (!haveFrames) break;
    if (frames[displaySliceIndex].valid[i]) value |= 1UL << (12 + i);
    if (frames[displaySliceIndex].events[i]) value |= 1UL << (20 + i);
  }
  return value;
}

void renderPixels() {
  const uint32_t key = stateHash();
  if (key == renderedFrameKey) return;
  renderedFrameKey = key;
  for (uint8_t i = 0; i < kDataCount; ++i) {
    uint32_t led = color(0, 0, 10);  // idle: dim blue
    if (haveFault && faultDataIndex == i) led = color(48, 22, 0);  // known input: amber
    pixels.setPixelColor(i, led);
  }
  for (uint8_t i = 0; i < kCheckCount; ++i) {
    uint32_t led = color(1, 1, 5);  // no trial yet
    if (haveFrames) {
      const CheckFrame& frame = frames[displaySliceIndex];
      if (!frame.valid[i]) led = color(14, 6, 0);  // unavailable boundary: dim amber
      else if (frame.events[i]) led = color(48, 0, 26);  // detector event: magenta
      else led = color(0, 11, 18);  // valid check with zero event: dim cyan
    }
    pixels.setPixelColor(kDataCount + i, led);
  }
  pixels.show();
}

void updateStatusIndicators(uint32_t now) {
  bool green = connected;
  bool red = false;
  if (!connected) red = ((now / 500) % 2) == 0;  // nonblocking 1 Hz disconnected blink
  if (errorPulseUntil != 0 && static_cast<int32_t>(errorPulseUntil - now) > 0) {
    const uint32_t age = kErrorPulseMs - (errorPulseUntil - now);
    red = ((age / 120) % 2) == 0;
  }
  if (phase == "decoded" && connected &&
      static_cast<int32_t>(decodeFlashUntil - now) > 0) {
    const uint32_t age = kDecodeFlashMs - (decodeFlashUntil - now);
    green = age < 100 || (age >= 200 && age < 300);  // two pulses, no correction-map claim
  }
  digitalWrite(kConnectedLedPin, green ? HIGH : LOW);
  digitalWrite(kDisconnectedLedPin, red ? HIGH : LOW);
}

}  // namespace

void setup() {
  pinMode(kInjectButtonPin, INPUT_PULLUP);
  pinMode(kDecodeButtonPin, INPUT_PULLUP);
  pinMode(kResetButtonPin, INPUT_PULLUP);
  pinMode(kConnectedLedPin, OUTPUT);
  pinMode(kDisconnectedLedPin, OUTPUT);
  digitalWrite(kConnectedLedPin, LOW);
  digitalWrite(kDisconnectedLedPin, LOW);
  for (ButtonInput& button : buttons) {
    button.rawHigh = digitalRead(button.pin) == HIGH;
    button.stableHigh = button.rawHigh;
    button.rawChangedAt = millis();
  }
  pixels.begin();
  pixels.setBrightness(kPixelBrightness);
  pixels.clear();
  pixels.show();
  createSessionId();
  Serial.begin(115200);
  const uint32_t now = millis();
  lastValidRxAt = now;
  nextHelloAt = 0;
}

void loop() {
  const uint32_t now = millis();
  readHostSerial(now);
  sampleButtons(now);
  serviceLink(now);
  renderPixels();
  updateStatusIndicators(now);
}
