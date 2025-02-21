# import numpy as np
from pydub import AudioSegment
from pydub.generators import Sine
import crcmod
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# DTMF frequencies (Extended with control tones)
TONES = {
    'START': (1830, 1900),  # Unique start tone
    'END': (1770, 1830),    # Unique end tone
    '0': (941, 1336), '1': (697, 1209), '2': (697, 1336), '3': (697, 1477),
    '4': (770, 1209), '5': (770, 1336), '6': (770, 1477), '7': (852, 1209),
    '8': (852, 1336), '9': (852, 1477), 'A': (697, 1633), 'B': (770, 1633),
    'C': (852, 1633), 'D': (941, 1633), 'E': (697, 1795), 'F': (770, 1795)
}

# Encoding parameters
SAMPLE_RATE = 44100
TONE_DURATION = 200  # ms
SILENCE_DURATION = 50  # ms between tones
CRC_POLY = 0x13D  # CRC-8 (DVB-S2)

def text_to_hex(text):
    return text.encode('utf-8').hex().upper()

def generate_tone(freq1, freq2, duration):
    tone = Sine(freq1).to_audio_segment(duration=duration).overlay(
        Sine(freq2).to_audio_segment(duration=duration))
    return tone

def add_synchronization(audio):
    start_tone = generate_tone(*TONES['START'], TONE_DURATION * 2)
    end_tone = generate_tone(*TONES['END'], TONE_DURATION * 2)
    return start_tone + audio + end_tone

def calculate_crc(data):
    crc8_func = crcmod.mkCrcFun(CRC_POLY, initCrc=0x00, xorOut=0x00)
    crc8 = crc8_func(data.encode('utf-8'))
    return format(crc8, '02X')

def encode_audio(text, filename="output.wav"):
    try:
        # Convert text to hex and add CRC
        hex_data = text_to_hex(text)
        crc = calculate_crc(text)
        full_data = hex_data + crc
        
        # Generate audio sequence
        audio = AudioSegment.silent(duration=100)
        for char in full_data:
            if char.upper() in TONES:
                tone = generate_tone(*TONES[char.upper()], TONE_DURATION)
                audio += tone + AudioSegment.silent(duration=SILENCE_DURATION)
        
        # Add synchronization tones
        audio = add_synchronization(audio)
        audio.export(filename, format="wav")
        logger.info(f"Encoded audio saved to {filename}")
        return filename
    except Exception as e:
        logger.error(f"Encoding failed: {str(e)}")
        raise

if __name__ == "__main__":
    text = input("Enter text to encode: ")
    encode_audio(text)