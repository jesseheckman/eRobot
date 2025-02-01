import serial
import serial.tools.list_ports
import pandas as pd
import time
import matplotlib.pyplot as plt

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
        if port is None:
            ports = self.list_available_ports()
            usbmodem_ports = [p for p in ports if 'usbmodem' in p]
            if usbmodem_ports:
                self.port = usbmodem_ports[0]
                print(f"No port specified. Using first 'usbmodem' port: {self.port}")
            else:
                raise ValueError("No 'usbmodem' ports found. Please specify a valid port.")
        else:
            self.port = port

        self.baudrate = baudrate
        self.timeout = timeout
        self.handshake_timeout = 100
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

    def await_handshake(self):
        """
        Wait for a handshake signal ('INIT-COM') from the Arduino.

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
            if time.time() - start_time > self.handshake_timeout:
                print("Handshake timed out")
                raise TimeoutError("Failed to receive handshake from Arduino")

    def process_format_message(self):
        """
        Process the format message ('Format: ...') from the Arduino to define
        the data structure for the DataFrame.
        """
        while True:
            if self.connection.in_waiting > 0:
                format_message = self.connection.readline().decode('utf-8').strip()
                if format_message.startswith("Format:"):
                    print(f"Received format message: {format_message}")
                    self.columns = format_message.replace("Format: ", "").split(",")
                    self.data = pd.DataFrame(columns=self.columns)
                    return

    def read_sensor_data(self, duration=None, visualize=True):
        """
        Read sensor data from the Arduino. The recording stops after the given
        duration or when a 'STOP-COM' signal is received.

        Parameters:
        - duration (int): Duration in seconds to record data (optional). 
                          If not provided, recording stops on 'STOP-COM'.
        - visualize (bool): Whether to display a live plot of the data.
        """

        print(duration)
        start_time = time.time()
        sample_count = 0
        try:
            if visualize:
                plt.ion()
                fig, ax = plt.subplots()
                lines = {}
                for col in self.columns[1:]:  # Skip the first column (Ts)
                    lines[col], = ax.plot([], [], label=col)
                ax.legend(loc="center left", bbox_to_anchor=(1, 0.5))  # Legend on the right
                recent_data = {col: [] for col in self.columns[1:]}

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

                        # Visualize every 50th sample
                        sample_count += 1
                        if visualize and sample_count % 50 == 0:
                            elapsed_time = (sample_count / 200)  # Convert to seconds
                            for col in self.columns[1:]:  # Skip the first column (Ts)
                                recent_data[col].append(row[col])
                                if len(recent_data[col]) > 50:  # Limit the display to the last 50 samples
                                    recent_data[col].pop(0)
                            for col, line in lines.items():
                                line.set_xdata([elapsed_time - (len(recent_data[col]) - i) * 0.25 for i in range(len(recent_data[col]))])
                                line.set_ydata(recent_data[col])
                            ax.relim()
                            ax.autoscale_view()
                            ax.set_xlabel("Time (s)")
                            plt.draw()
                            plt.pause(0.01)

                        # Check if the buffer exceeds the size limit
                        if len(self.buffer) >= self.buffer_size:
                            self.flush_buffer_to_dataframe()

        except KeyboardInterrupt:
            print("Data collection stopped manually")
        finally:
            # Ensure data in buffer is saved
            self.flush_buffer_to_dataframe()
            if visualize:
                plt.ioff()
                plt.show()
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
    
    # Automatically selects the first 'usbmodem' port if not specified
    collector.connect()
    collector.await_handshake()
    collector.process_format_message()

    # Use a fixed duration or wait for STOP-COM
    try:
        collector.read_sensor_data(duration=60, visualize=True)  # Record for 60 seconds with live visualization
    except Exception as e:
        print(f"Error during data collection: {e}")

    # Store data to file
    collector.store_data("sensor_data.csv")
    collector.close_connection()
