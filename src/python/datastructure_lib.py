import os
from datetime import datetime
import csv
import json
import numpy as np
import pandas as pd
import time  # Import time for timing the operations

def create_recording_structure():
    current_date = datetime.now().strftime('%Y/%m/%d')
    base_dir = os.path.join('.', 'recordings', current_date)
    
    print('\nCreating datastructure:')
    
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
        print(f"    Created folder: {base_dir}")
    else:
        print(f"    Folder already exists: {base_dir}")

    recordings = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d)) and d.startswith('recording_')]
    
    if recordings:
        last_recording = sorted(recordings)[-1]
        last_number = int(last_recording.split('_')[-1])
    else:
        last_number = 0

    next_number = last_number + 1
    recording_folder = os.path.join(base_dir, f"recording_{next_number:03d}")

    if not os.path.exists(recording_folder):
        os.makedirs(recording_folder)
        print(f"    Created recording folder: {recording_folder}")
    else:
        print(f"    Recording folder already exists: {recording_folder}")

    log_file_path = os.path.join(recording_folder, 'log.json')
    if not os.path.exists(log_file_path):
        with open(log_file_path, 'w') as file:
            file.write('This is the log file for this recording.\n')
        print(f"        Created JSON file: {log_file_path}")
    else:
        print(f"        JSON file already exists: {log_file_path}")
    
    csv_file_path = os.path.join(recording_folder, 'data.csv')
    if not os.path.exists(csv_file_path):
        with open(csv_file_path, 'w') as file:
            pass  # Creates an empty file
        print(f"        Created CSV file: {csv_file_path}")
    else:
        print(f"        CSV file already exists: {csv_file_path}")

    print('\n')
    return recording_folder

def write_metafile(folder_path, ts):
    start_time = time.time()

    ts_on_str = ts[0]
    ts_off_str = ts[1]

    ts_on = datetime.strptime(ts_on_str, '%Y-%m-%d %H:%M:%S.%f')
    ts_off = datetime.strptime(ts_off_str, '%Y-%m-%d %H:%M:%S.%f')

    csv_file = os.path.join(folder_path, 'data.csv')
    log_file = os.path.join(folder_path, 'log.json')
    
    # Timer: Start reading the CSV file with pandas
    csv_read_start_time = time.time()

    try:
        # Read the CSV using pandas
        df = pd.read_csv(csv_file)
        variables = df.columns.tolist()

        # Timer: Finished reading the CSV file
        print(f"Time to read CSV with pandas: {time.time() - csv_read_start_time:.6f} seconds")

        # Timer: Start processing data
        process_start_time = time.time()

        time_list = df['time'].astype(float).tolist()
        sampling_intervals = np.diff(time_list)

        missing_points = int(sum(sampling_intervals > 1.5 * np.median(sampling_intervals)))
        duplicated_points = int(sum(sampling_intervals <= 0))

        if len(sampling_intervals) > 0:
            average_sampling_frequency = 1 / np.mean(sampling_intervals) * 1e6
            sampling_stats = {
                "mean": np.mean(sampling_intervals).item(),
                "std_dev": np.std(sampling_intervals).item(),
                "min": np.min(sampling_intervals).item(),
                "max": np.max(sampling_intervals).item()
            }
        else:
            average_sampling_frequency = 0
            sampling_stats = {
                "mean": 0,
                "std_dev": 0,
                "min": 0,
                "max": 0
            }

        run_time = (ts_off - ts_on).total_seconds()

        start_time_str = f"{ts_on.strftime('%H:%M:%S')}.{int(ts_on.microsecond / 10000):02d}"
        stop_time_str = f"{ts_off.strftime('%H:%M:%S')}.{int(ts_off.microsecond / 10000):02d}"

        metadata = {
            "recorded_data": variables,
            "date": ts_on.strftime('%Y-%m-%d'),
            "start_time": start_time_str,
            "stop_time": stop_time_str,
            "run_time_seconds": round(run_time, 2),
            "data_points_count": int(len(df)),
            "average_sampling_frequency_hz": average_sampling_frequency.item() if isinstance(average_sampling_frequency, np.generic) else average_sampling_frequency,
            "sampling_stats_micros": sampling_stats,
            "missing_data_points": missing_points,
            "duplicated_data_points": duplicated_points
        }

        # Timer: Finished processing data
        print(f"Time to process data: {time.time() - process_start_time:.6f} seconds")

        # Timer: Start writing to JSON
        json_write_start_time = time.time()

        with open(log_file, 'w') as json_file:
            json.dump(metadata, json_file, indent=4)

        # Timer: Finished writing to JSON
        print(f"Time to write metadata to JSON: {time.time() - json_write_start_time:.6f} seconds")
        print(f"Total time for write_metafile function: {time.time() - start_time:.6f} seconds")

    except KeyError as e:
        print(f"Key error: {e} - Make sure the 'count' and 'time' fields exist in the CSV header.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    final_path = create_recording_structure()
    print(f"Final recording folder path: {final_path}")
