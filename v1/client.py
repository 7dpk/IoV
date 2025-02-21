import numpy as np
import pyaudio
import time

# Constants
SAMPLE_RATE = 44100  # Standard sample rate for audio
DURATION = 0.5       # Duration of each tone in seconds
FREQUENCY_0 = 1000   # Frequency for bit '00'
FREQUENCY_1 = 1500   # Frequency for bit '01'
FREQUENCY_2 = 2000   # Frequency for bit '10'
FREQUENCY_3 = 2500   # Frequency for bit '11'
SYNC_TONE = 3000     # Sync tone to start/stop transmission

# Function to generate a sine wave of a given frequency and duration
def generate_tone(frequency, duration, sample_rate=SAMPLE_RATE):
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    return np.sin(2 * np.pi * frequency * t)

# Function to send data with multiple frequencies
def send_data(data):
    p = pyaudio.PyAudio()
    
    # Open a stream to the microphone (for simplicity, we use playback here)
    stream = p.open(format=pyaudio.paFloat32, channels=1, rate=SAMPLE_RATE, output=True)
    
    # Send sync tone to signal start
    sync_tone = generate_tone(SYNC_TONE, DURATION)
    stream.write(sync_tone.astype(np.float32).tobytes())
    time.sleep(0.1)  # Pause after the sync tone
    
    # Convert the binary data into sound waves
    for i in range(0, len(data), 2):  # Process 2 bits per tone
        pair = data[i:i+2]
        
        if pair == '00':
            tone = generate_tone(FREQUENCY_0, DURATION)
        elif pair == '01':
            tone = generate_tone(FREQUENCY_1, DURATION)
        elif pair == '10':
            tone = generate_tone(FREQUENCY_2, DURATION)
        elif pair == '11':
            tone = generate_tone(FREQUENCY_3, DURATION)
        else:
            continue  # Error handling: skip invalid bits

        # Play the tone
        stream.write(tone.astype(np.float32).tobytes())
        time.sleep(0.1)  # Short pause between tones

    # Send sync tone to signal end
    stream.write(sync_tone.astype(np.float32).tobytes())
    
    # Close the stream
    stream.stop_stream()
    stream.close()
    p.terminate()

# Client Example Usage
if __name__ == "__main__":
    binary_data = "0101010101110001"  # Example binary data to send
    send_data(binary_data)
