import serial
import time
import datetime
import csv
import os
import serial.tools.list_ports  # Ensure this is properly imported
import pandas as pd


def initiate_communication():
    """
    Establishes a serial connection with the Arduino, sends a signal to start 
    logging data, and records the incoming data for 20 seconds. The data is 
    logged to a text file and printed to the console.

    The function connects to the specified serial port, sends the start command 
    ('s'), and begins recording the data sent from the Arduino. After 20 seconds, 
    it stops the logging process by sending another signal to the Arduino.

    The recorded data is saved to 'arduino_log.txt' in the same directory.

    Raises:
        KeyboardInterrupt: If the user interrupts the process, the function 
        stops logging and closes the serial connection.
    """
    ser = serial.Serial('/dev/tty.usbmodem14201', 9600, timeout=1)
    time.sleep(2)  # Give some time for the connection to establish
    
    # Send command to start recording
    ser.write(b's')  # Send 's' to start logging
    print("Sent start signal to Arduino.")
    
    # Record the start time
    start_time = time.time()

    # Open a text file to save the log
    with open('arduino_log.txt', 'w') as log_file:
        try:
            while True:
                # Read the line from Arduino
                line = ser.readline().decode('utf-8').strip()
                
                # Check if there is any data to log
                if line:
                    print(line)  # Print the data to console
                    log_file.write(line + '\n')  # Write the data to file
                
                # Check if 20 seconds have passed
                if time.time() - start_time >= 20:
                    ser.write(b's')  # Send 's' to stop logging
                    print("20 seconds elapsed. Sent stop signal to Arduino.")
                    break
                
        except KeyboardInterrupt:
            # Stop recording if the script is interrupted
            ser.write(b's')  # Send 's' to stop logging
            print("Sent stop signal to Arduino.")
        
    # Close the serial connection
    ser.close()


def record_arduino_data(link, folder_path, header=None, duration=20):
    """
    Records data from the Arduino over a specified duration and logs it into a CSV file using pandas.

    Args:
        link (serial.Serial): The established serial connection to the Arduino.
        folder_path (str): The path to the folder where the CSV file will be saved.
        header (list): A list of column headers to use for the CSV file.
        duration (int): The duration (in seconds) for which data should be recorded.
    """
    csv_file_path = os.path.join(folder_path, 'data.csv')

    # Initialize a list to hold all the data
    data_list = []

    start_time = time.time()
    
    while True:
        if link.in_waiting > 0:
            raw_line = link.readline()
            #print(raw_line)  # Debugging: print the raw data received
            line = raw_line.decode('utf-8', errors='replace').strip()

            # Split the line into parts
            parts = line.split()

            # Create a dictionary to store the current line's data
            data_dict = {}
            for i, column_name in enumerate(header):
                data_dict[column_name] = parts[i] if i < len(parts) else ''  # Fill missing values with empty strings

            # Append the data_dict to the list
            data_list.append(data_dict)

        # Stop recording after the specified duration
        if time.time() - start_time >= duration:
            break

    # Convert the list of dictionaries to a DataFrame
    data_frame = pd.DataFrame(data_list, columns=header)

    # Write the DataFrame to a CSV file
    data_frame.to_csv(csv_file_path, index=False)
    print(f"Data saved to {csv_file_path}")


def send_signal(link, signal,delay=0.1):
    """
    Sends a specified signal over an established serial link to the Arduino.

    This function is used to send a command or data string to the Arduino via 
    the provided serial connection.

    Args:
        link (serial.Serial): The established serial connection to the Arduino.
        signal (str): The signal or command to send (e.g., a single character 
        or a full string).

    Raises:
        serial.SerialException: If there's an issue with sending the signal 
        over the serial connection.
    """

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')  # Get current date and time
    
    try:
        link.write(signal.encode())  # Send the signal to the Arduino
        #print(f"Sent signal: {signal}")
    except serial.SerialException as e:
        print(f"Failed to send signal: {e}")

    time.sleep(delay)
    return timestamp

def list_serial_ports(print_ports=True):
    """
    Lists all available serial ports on the system.

    This function scans and returns a list of available serial ports. Optionally, 
    it can print the list of ports to the console.

    Args:
        print_ports (bool): If True, prints the available ports to the console. 
        Default is True.

    Returns:
        list: A list of available serial port names (e.g., ['/dev/ttyUSB0', 'COM3']).
    """
    ports = serial.tools.list_ports.comports()
    port_names = [port.device for port in ports]

    # Print out the port names if print_ports is True
    if print_ports:
        if port_names:
            print("Available serial ports:")
            for name in port_names:
                print(name)
        else:
            print("No serial ports found.")

    return port_names

def connect_to_arduino(port_name=None, baud_rate=9600):
    """
    Establishes a serial connection to the Arduino.

    This function attempts to connect to an Arduino via a specified serial port 
    and baud rate. If no port is specified, it automatically selects the first 
    available port containing 'usb' in its name.

    Args:
        port_name (str, optional): The name of the serial port to connect to. 
        If not provided, the function attempts to find a suitable port automatically.
        baud_rate (int, optional): The baud rate for the serial communication. 
        Default is 9600.

    Returns:
        serial.Serial: The established serial connection to the Arduino.

    Raises:
        ValueError: If no suitable USB port is found when port_name is not provided.
        ConnectionError: If the connection to the Arduino fails.
    """
    if port_name is None:
        ports = list_serial_ports(print_ports=False)
        for port in ports:
            if 'usb' in port.lower():
                port_name = port
                break

    # If no port was found with 'usb' in the name, raise an error
    if port_name is None:
        raise ValueError("No suitable USB port found. Please specify a port name.")

    # Attempt to connect to the Arduino
    try:
        ser = serial.Serial(port_name, baud_rate)
        print(f"Connected to Arduino on port {port_name} at {baud_rate} baud.")
        ser.flushInput()
        return ser
    except serial.SerialException as e:
        raise ConnectionError(f"Failed to connect to the Arduino on port {port_name}: {e}")
    
    # Wait for Arduino to reset
    time.sleep(2)
    print('    Arduino flushed and ready for recording!')

def disconnect_arduino(link):
    """
    Stops the current serial connection between the Mac and Arduino.

    This function safely closes the active serial connection, ensuring that 
    the port is properly released.

    Args:
        link (serial.Serial): The active serial connection to be closed.

    Raises:
        serial.SerialException: If there's an issue with closing the connection.
    """
    try:
        if link.is_open:
            link.close()
            print("Connection to Arduino closed successfully.")
        else:
            print("Connection was already closed.")
    except serial.SerialException as e:
        print(f"Failed to close the connection: {e}")


# Example usage
if __name__ == "__main__":
    try:
        link = connect_to_arduino(baud_rate=9600)  # You can also pass port_name and baud_rate here
        # Now you can use link to communicate with the Arduino
        time.sleep(1)
        disconnect_arduino(link)
    except (ValueError, ConnectionError) as e:
        print(e)




    
