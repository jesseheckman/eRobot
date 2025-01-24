#define SAMPLE_RATE 200  // Sampling rate in Hz
#define BUTTON_PIN 2    // Pin for the high/low button

unsigned long previousMillis = 0;        // Store the previous loop time
unsigned long interval = 1000 / SAMPLE_RATE; // Interval for sample rate in milliseconds

bool ledState = false;   // LED state (on/off)
bool communicationState = false; // Serial on / off

unsigned long lastDebounceTime = 0; // Last time the button state changed
unsigned long startingTime = 0;
const unsigned long debounceDelay = 50; // Debounce delay in milliseconds

int lastButtonState = HIGH; // Previous button state
int buttonState; // Current button state
int cntSerial = 0; // Tracks the current communication state

// Communication pins
const int analogPins[] = {
  A0, // SENSOR X
  A1, // SENSOR dX
  A2, // SENSOR Y
  A3, // SENSOR dY
  A4, // SENSOR Z
  A5, // SENSOR dZ
};
const int numAnalogPins = sizeof(analogPins) / sizeof(analogPins[0]);

void setup() {
  // Initialise pins
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  // Initialise analog input pins
  for (int i = 0; i < numAnalogPins; i++) {
    pinMode(analogPins[i], INPUT);
  }

  // Start serial communication
  Serial.begin(115200);
}

void loop() {
  unsigned long currentMillis = millis();

  // Check button state and toggle LED if needed
  if (checkButton()) {
    ledState = !ledState;
    digitalWrite(LED_BUILTIN, ledState ? HIGH : LOW);

    if (!communicationState) {
      // Start communication
      cntSerial = 1;
      communicationState = true;
      Serial.println("INIT-COM"); // Handshake
      listCommunicationPins();
      startingTime = millis();
    } else {
      // Stop communication
      Serial.println("STOP-COM");
      communicationState = false;
      cntSerial = 0; // Reset to allow reinitialisation
    }
  }

  // Additional logic (e.g., sampling at the specified rate)
  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;

    if (communicationState) {
      sendAnalogData();
    }
  }
}

// Function to check the button state and handle debouncing
bool checkButton() {
  unsigned long currentMillis = millis();
  int reading = digitalRead(BUTTON_PIN);

  // Check if the button state has changed
  if (reading != lastButtonState) {
    lastDebounceTime = currentMillis; // Reset the debounce timer
  }

  // If the button state is stable for debounceDelay, consider it valid
  if ((currentMillis - lastDebounceTime) > debounceDelay) {
    if (reading != buttonState) { // Button state has changed
      buttonState = reading;

      // Return true if the button is pressed (LOW)
      if (buttonState == LOW) { 
        lastButtonState = reading;
        return true;
      }
    }
  }

  lastButtonState = reading; // Save the last button state
  return false;
}

// Function will tell the ArduinoCommunicator class what data format to expect
void listCommunicationPins() {
  // Format data structure
  Serial.print("Format: Ts,");
  for (int i = 0; i < numAnalogPins; i++) {
    int pinIndex = analogPins[i] - A0;
    Serial.print("A");
    Serial.print(pinIndex);
    
    if (i < numAnalogPins - 1) {
      Serial.print(",");
    }
  }
  Serial.println();
}

void sendAnalogData() {
  // Send data
  unsigned long Ts = millis() - startingTime;
  Serial.print(Ts);

  for (int i = 0; i < numAnalogPins; i++) { 
    Serial.print(",");
    Serial.print(analogRead(analogPins[i]));
  }
  Serial.println();
}
