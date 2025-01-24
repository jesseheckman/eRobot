import os
import csv
import json
import numpy as np
from scipy.io.wavfile import write as wav_write
import simpleaudio as sa

def round_to_nearest_standard_rate(sampling_rate):
    """
    Rounds the given sampling rate to the nearest accepted standard sampling rate.
    """
    standard_sample_rates = [8000, 16000, 22050, 32000, 44100, 48000]
    closest_sample_rate = min(standard_sample_rates, key=lambda x: abs(x - sampling_rate))
    return closest_sample_rate

def convert_csv_to_wav(folder_path):
    # Load the log.json file to get the sampling rate
    log_json_path = os.path.join(folder_path, 'log.json')
    with open(log_json_path, 'r') as json_file:
        log_data = json.load(json_file)
    
    # Extract the average sampling frequency from log.json
    sampling_rate = log_data.get('average_sampling_frequency_hz', 44100)  # Default to 44100 Hz if not found
    
    # Round the sampling rate to the nearest standard rate
    adjusted_sample_rate = round_to_nearest_standard_rate(sampling_rate)
    
    print(f"Original sampling rate: {sampling_rate}, Adjusted to: {adjusted_sample_rate}")

    # Load the volt data from data.csv
    csv_file_path = os.path.join(folder_path, 'data.csv')
    volts = []
    
    with open(csv_file_path, 'r') as csvfile:
        csvreader = csv.DictReader(csvfile)
        for row in csvreader:
            volt_value = row.get('volt')
            try:
                volts.append(float(volt_value))  # Handle floating-point values
            except (ValueError, TypeError):
                continue  # Skip non-numeric or missing values

    if not volts:
        raise ValueError("No valid voltage data found in CSV file.")

    # Convert volts to a numpy array
    volts = np.array(volts)
    
    # Center the data around zero
    volts -= np.mean(volts)

    # Normalize the data to fit the 16-bit PCM range (-32768 to 32767)
    max_abs_volt = np.max(np.abs(volts))
    if max_abs_volt > 0:
        volts = volts * (32767.0 / max_abs_volt)
    
    # Convert to 16-bit PCM format
    volts = volts.astype(np.int16)

    # Create the sound.wav file
    wav_file_path = os.path.join(folder_path, 'sound.wav')
    wav_write(wav_file_path, adjusted_sample_rate, volts)
    print(f"Created WAV file: {wav_file_path}")

    return wav_file_path

def playback_wav(folder_path):
    wav_file_path = os.path.join(folder_path, 'sound.wav')
    
    if os.path.exists(wav_file_path):
        # Load the WAV file
        wave_obj = sa.WaveObject.from_wave_file(wav_file_path)
        # Play the WAV file
        play_obj = wave_obj.play()
        play_obj.wait_done()  # Wait until the sound has finished playing
        print(f"Playback of {wav_file_path} completed.")
    else:
        print(f"No WAV file found at {wav_file_path}. Please check the folder path.")

if __name__ == "__main__":
    folder_path = "./recordings/2024/09/02/recording_012"
    try:
        wav_file = convert_csv_to_wav(folder_path)
        playback_wav(folder_path)
    except Exception as e:
        print(f"An error occurred: {e}")
