import numpy as np
import pyaudio
from scipy.signal import find_peaks

# Constants
SAMPLE_RATE = 44100
DURATION = 0.5
FREQUENCY_0 = 1000   # Frequency for bit '00'
FREQUENCY_1 = 1500   # Frequency for bit '01'
FREQUENCY_2 = 2000   # Frequency for bit '10'
FREQUENCY_3 = 2500   # Frequency for bit '11'
SYNC_TONE = 3000     # Sync tone for start/stop
TOLERANCE = 100  # Hz tolerance to match frequencies

# Function to detect the frequency from the audio signal
def detect_frequency(data, sample_rate=SAMPLE_RATE):
    # Perform FFT (Fast Fourier Transform) on the audio data to find frequencies
    n = len(data)
    freqs = np.fft.fftfreq(n, d=1/sample_rate)
    fft_vals = np.fft.fft(data)
    fft_abs = np.abs(fft_vals)
    
    # Find peaks in the FFT
    peaks, _ = find_peaks(fft_abs, height=np.max(fft_abs) / 2)
    
    # Get the dominant frequency (highest peak)
    dominant_freq = abs(freqs[peaks[np.argmax(fft_abs[peaks])]])
    return dominant_freq

# Function to decode the audio signal into binary data
def decode_audio():
    p = pyaudio.PyAudio()
    
    # Open a stream to capture audio
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=SAMPLE_RATE, input=True, frames_per_buffer=1024)

    print("Listening for incoming data...")

    # Initialize buffers
    audio_data_buffer = []
    receiving_data = False
    decoded_data = []

    # Capture the audio in chunks
    while True:
        audio_data = np.frombuffer(stream.read(1024), dtype=np.int16)
        audio_data_buffer.append(audio_data)
        
        # Detect the frequency in the audio signal
        frequency = detect_frequency(audio_data)
        
        # Check for the sync tone (3000 Hz) to signal start/stop of data transmission
        if abs(frequency - SYNC_TONE) < TOLERANCE:
            if not receiving_data:
                print("Start of transmission detected!")
                receiving_data = True  # Start receiving data
                audio_data_buffer.clear()  # Clear buffer
            else:
                print("End of transmission detected!")
                break  # End the transmission and process the data
        
    # Process the recorded audio data after it ends
    combined_data = np.concatenate(audio_data_buffer)
    
    print("Processing the recorded audio data...")

    # Decode the captured audio
    for i in range(0, len(combined_data), SAMPLE_RATE // 2):  # Look for every 0.5 seconds (DURATION)
        chunk = combined_data[i:i + SAMPLE_RATE // 2]
        frequency = detect_frequency(chunk)
        
        # Decode the frequencies into pairs of bits
        if abs(frequency - FREQUENCY_0) < TOLERANCE:
            decoded_data.append('00')
        elif abs(frequency - FREQUENCY_1) < TOLERANCE:
            decoded_data.append('01')
        elif abs(frequency - FREQUENCY_2) < TOLERANCE:
            decoded_data.append('10')
        elif abs(frequency - FREQUENCY_3) < TOLERANCE:
            decoded_data.append('11')
        else:
            print(f"Unrecognized frequency: {frequency} Hz")
            continue

    # Join the decoded bits and process
    print("Decoded Data:", ''.join(decoded_data))
    
    # Close the stream
    stream.stop_stream()
    stream.close()
    p.terminate()

# Server Example Usage
if __name__ == "__main__":
    decode_audio()
