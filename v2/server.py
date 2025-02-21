import numpy as np
import pyaudio
import wave
from scipy.fft import fft, fftfreq
import crcmod
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Matching parameters with encoder
SAMPLE_RATE = 44100
CHUNK = 1024
RECORD_FORMAT = pyaudio.paInt16
CHANNELS = 1
THRESHOLD = 0.1  # Noise threshold
CRC_POLY = 0x13D  # Must match encoder
TONE_DURATION = 200  # ms

# DTMF frequencies (Extended with control tones)
TONES = {
    'START': (1830, 1900),  # Unique start tone
    'END': (1770, 1830),    # Unique end tone
    '0': (941, 1336), '1': (697, 1209), '2': (697, 1336), '3': (697, 1477),
    '4': (770, 1209), '5': (770, 1336), '6': (770, 1477), '7': (852, 1209),
    '8': (852, 1336), '9': (852, 1477), 'A': (697, 1633), 'B': (770, 1633),
    'C': (852, 1633), 'D': (941, 1633), 'E': (697, 1795), 'F': (770, 1795)
}

# Reverse tone mapping
REVERSE_TONES = {v: k for k, v in TONES.items()}

def find_dominant_frequencies(signal, tolerance=0.03):
    fft_result = fft(signal)
    freqs = fftfreq(len(signal), 1/SAMPLE_RATE)
    magnitudes = np.abs(np.array(fft_result))
    
    peaks = []
    for i in np.argsort(magnitudes)[-4:]:
        if freqs[i] > 0 and magnitudes[i] > THRESHOLD * np.max(magnitudes):
            peaks.append(freqs[i])
    
    return sorted(peaks)[-2:] if len(peaks) >=2 else None

def decode_tones(audio_data):
    decoded = []
    samples_per_chunk = int(SAMPLE_RATE * TONE_DURATION / 1000)
    
    for i in range(0, len(audio_data), samples_per_chunk):
        chunk = audio_data[i:i+samples_per_chunk]
        if len(chunk) < samples_per_chunk:
            continue
            
        freqs = find_dominant_frequencies(chunk)
        if freqs:
            rounded = tuple(round(f, -2) for f in freqs)
            decoded_char = REVERSE_TONES.get(rounded, None)
            if decoded_char:
                decoded.append(decoded_char)
    
    return decoded

def validate_data(hex_str):
    try:
        if len(hex_str) < 2:
            return False, ""
        data_hex = hex_str[:-2]
        received_crc = hex_str[-2:]
        
        crc8 = crcmod.predefined.Crc(CRC_POLY, initCrc=0x00, xorOut=0x00)
        crc8.update(bytes.fromhex(data_hex).decode('utf-8', errors='replace').encode('utf-8'))
        calculated_crc = format(crc8.crc, '02X')
        
        if received_crc.upper() != calculated_crc:
            return False, data_hex
        
        return True, bytes.fromhex(data_hex).decode('utf-8', errors='replace')
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return False, ""

def record_audio(filename="recording.wav"):
    p = pyaudio.PyAudio()
    stream = p.open(format=RECORD_FORMAT,
                    channels=CHANNELS,
                    rate=SAMPLE_RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    
    logger.info("Listening for start tone...")
    audio_buffer = []
    start_detected = False
    
    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio_buffer.append(data)
            
            # Convert to numpy array
            signal = np.frombuffer(data, dtype=np.int16)
            
            # Check for start tone
            freqs = find_dominant_frequencies(signal)
            if freqs and tuple(round(f, -2) for f in freqs) == TONES['START']:
                logger.info("Start tone detected, recording...")
                start_detected = True
                audio_buffer = [b''.join(audio_buffer[-2:])]  # Keep last 2 chunks
                break
                
        # Record until end tone
        while start_detected:
            data = stream.read(CHUNK, exception_on_overflow=False)
            audio_buffer.append(data)
            
            signal = np.frombuffer(data, dtype=np.int16)
            freqs = find_dominant_frequencies(signal)
            if freqs and tuple(round(f, -2) for f in freqs) == TONES['END']:
                logger.info("End tone detected, stopping recording")
                break
                
    except KeyboardInterrupt:
        logger.info("Recording interrupted")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        # Save recording
        wf = wave.open(filename, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(RECORD_FORMAT))
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b''.join(audio_buffer))
        wf.close()
        return filename

def decode_audio(filename="recording.wav"):
    try:
        # Load audio file
        with wave.open(filename, 'rb') as wf:
            audio_data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
        
        # Decode tones
        decoded_chars = decode_tones(audio_data)
        
        # Remove control characters and validate
        data_chars = [c for c in decoded_chars if c not in ('START', 'END')]
        hex_str = ''.join(data_chars)
        valid, result = validate_data(hex_str)
        
        if valid:
            logger.info(f"Decoded successfully: {result}")
            return result
        else:
            logger.error(f"CRC mismatch or decoding error. Raw data: {hex_str}")
            return None
            
    except Exception as e:
        logger.error(f"Decoding failed: {str(e)}")
        raise

if __name__ == "__main__":
    recorded_file = record_audio()
    decode_audio(recorded_file)