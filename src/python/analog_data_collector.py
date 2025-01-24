import serial
import serial.tools.list_ports
import pandas as pd
import time

class ArduinoDataCollector:
    """
    A class to manage serial communication with an Arduino device for 
    collecting and storing sensor data.
    """

    def __init__(self, port=None, baudrate=115200, timeout=1, buffer_size=100):
        """
        Initialize the ArduinoDataCollector instance.

        Parameters:
        - port (str): The serial port to connect to.
        - baudrate (int): The baud rate for serial communication (default: 115200).
        - timeout (int): Timeout for the serial connection in seconds (default: 1).
        - buffer_size (int): Maximum size of the buffer before flushing to DataFrame.
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.buffer_size = buffer_size
        self.connection = None
        self.data = None  # DataFrame will be initialized after receiving format message
        self.buffer = []  # Buffer for temporarily storing data
        self.columns = []  # Columns for the DataFrame

    @staticmethod
    def list_available_ports():
        """
        List all available serial ports on the system.

        Returns:
        - list: A list of available serial port names.
        """
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    def print_available_ports(self):
        """
        Print all available serial ports to the console.
        """
        ports = self.list_available_ports()
        for port in ports:
            print(port)

    def connect(self):
        """
        Establish a serial connection with the Arduino.

        Raises:
        - Exception: If the connection fails.
        """
        try:
            self.connection = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            print(f"Connected to Arduino on {self.port}")
        except Exception as e:
            print(f"Failed to connect: {e}")
            raise

    def await_handshake(self, timeout=10):
        """
        Wait for a handshake signal ('INIT-COM') from the Arduino.

        Parameters:
        - timeout (int): Time in seconds to wait for the handshake before timing out.

        Raises:
        - TimeoutError: If the handshake is not received within the timeout period.
        """
        start_time = time.time()
        while True:
            if self.connection.in_waiting > 0:
                message = self.connection.readline().decode('utf-8').strip()
                if message.startswith("INIT-COM"):
                    print("Handshake received from Arduino")
                    self.connection.write(b"READY\n")  # Send acknowledgment
                    print("Sent READY signal to Arduino")
                    return
            if time.time() - start_time > timeout:
                print("Handshake timed out")
                raise TimeoutError("Failed to receive handshake from Arduino")

    def process_format_message(self):
        """
        Process the format message ('Format: ...') from the Arduino to define
        the data structure for the DataFrame.

        This method listens for a message starting with 'Format:' and uses it
        to initialize the columns of the DataFrame.
        """
        while True:
            if self.connection.in_waiting > 0:
                format_message = self.connection.readline().decode('utf-8').strip()
                if format_message.startswith("Format:"):
                    print(f"Received format message: {format_message}")
                    self.columns = format_message.replace("Format: ", "").split(",")
                    self.data = pd.DataFrame(columns=self.columns)
                    return

    def read_sensor_data(self, duration=None):
        """
        Read sensor data from the Arduino. The recording stops after the given
        duration or when a 'STOP-COM' signal is received.

        Parameters:
        - duration (int): Duration in seconds to record data (optional). 
                          If not provided, recording stops on 'STOP-COM'.
        """
        start_time = time.time()
        try:
            while True:
                # Stop if the fixed duration has elapsed
                if duration and (time.time() - start_time) >= duration:
                    print(f"Recording stopped after {duration} seconds")
                    break

                if self.connection.in_waiting > 0:
                    raw_data = self.connection.readline().decode('utf-8').strip()

                    # Check for stop signal
                    if raw_data == "STOP-COM":
                        print("STOP-COM signal received. Stopping data collection.")
                        break

                    # Process sensor data
                    parts = raw_data.split(",")
                    if len(parts) == len(self.columns):  # Ensure correct data format
                        # Create a dictionary with the received data
                        row = {col: float(value) for col, value in zip(self.columns, parts)}
                        self.buffer.append(row)

                        # Check if the buffer exceeds the size limit
                        if len(self.buffer) >= self.buffer_size:
                            self.flush_buffer_to_dataframe()

        except KeyboardInterrupt:
            print("Data collection stopped manually")
        finally:
            # Ensure data in buffer is saved
            self.flush_buffer_to_dataframe()
            self.close_connection()

    def flush_buffer_to_dataframe(self):
        """
        Flush the buffer into the DataFrame. This method moves all data
        from the buffer into the main DataFrame and clears the buffer.
        """
        if self.buffer:
            buffer_df = pd.DataFrame(self.buffer)
            if self.data is None or self.data.empty:
                # If self.data is None or empty, directly assign buffer_df
                self.data = buffer_df
            else:
                # Concatenate only if self.data has existing data
                self.data = pd.concat([self.data, buffer_df], ignore_index=True)
            self.buffer = []  # Clear the buffer

    def store_data(self, filename):
        """
        Save the collected data to a CSV file.

        Parameters:
        - filename (str): The name of the CSV file to save the data to.

        Prints a message indicating success or if no data is available to save.
        """
        if self.data is not None and not self.data.empty:
            self.data.to_csv(filename, index=False)
            print(f"Data saved to {filename}")
        else:
            print("No data to save.")

    def close_connection(self):
        """
        Close the serial connection with the Arduino.
        """
        if self.connection and self.connection.is_open:
            self.connection.close()
            print("Serial connection closed")

# Example usage
if __name__ == "__main__":
    print("Available serial ports:")
    collector = ArduinoDataCollector()
    collector.print_available_ports()
    
    # Update this port based on your system
    collector = ArduinoDataCollector(port="/dev/cu.usbmodemF412FA762D9C2", buffer_size=100)
    collector.connect()
    collector.await_handshake()
    collector.process_format_message()

    # Use a fixed duration or wait for STOP-COM
    try:
        collector.read_sensor_data(duration=30)  # Record for 30 seconds
    except Exception as e:
        print(f"Error during data collection: {e}")

    # Store data to file
    collector.store_data("sensor_data.csv")
    collector.close_connection()
