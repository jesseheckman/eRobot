# Import modules

from src.python import analog_data_collector as adc
from src.python import datastructure_lib as dsl

import os


if __name__ == "__main__":
    print("Running Experiment:\n")

    # Build Experimentation path
    recording_path = dsl.create_recording_structure()
    fullpath       = os.path.join(recording_path,"data.csv")
    print(f"Final recording folder path: {recording_path}")

    # Connect to arduino
    collector = adc.ArduinoDataCollector(port="/dev/cu.usbmodemF412FA762D9C2", buffer_size=100)
    collector.connect()
    collector.await_handshake()
    collector.process_format_message()

    # Use a fixed duration or wait for STOP-COM
    try:
        collector.read_sensor_data(duration=60, visualize=True)  # Record for 60 seconds
    except Exception as e:
        print(f"Error during data collection: {e}")



    collector.store_data(fullpath)
    collector.close_connection()





