import pyaudio
import struct
import time
import threading

class WAVReader:
    def __init__(self, filename):
        self.filename = filename
        self.sample_rate = 0
        self.num_channels = 0
        self.bits_per_sample = 0
        self.audio_data = []

    def read_wav_file(self):
        with open(self.filename, 'rb') as file:
            # Read the WAV file header to extract necessary information
            riff_header = file.read(12)
            format_chunk_header = file.read(24)
            # format_chunk_header[0:4] == 'fmt '
            format_chunk_size = struct.unpack('<I', format_chunk_header[4:8])[0]
            type_of_format = struct.unpack('<H', format_chunk_header[8:10])[0]
            self.num_channels = struct.unpack('<H', format_chunk_header[10:12])[0]
            self.sample_rate = struct.unpack('<I', format_chunk_header[12:16])[0]
            self.bits_per_sample = struct.unpack('<H', format_chunk_header[22:24])[0]

            # skip 'data'
            file.read(8)

            # Read the audio data
            data = file.read()
            num_samples = len(data) // (self.bits_per_sample // 8)  # Assuming 16-bit audio

            # Unpack the audio data into a list of samples
            self.audio_data = struct.unpack('<{}h'.format(num_samples), data)

    def set_filename(self, filename):
        self.filename = filename
    
    def get_filename(self):
        return self.filename

    def get_bits_per_sample(self):
        return self.bits_per_sample

    def get_sample_rate(self):
        return self.sample_rate

    def get_num_channels(self):
        return self.num_channels

    def get_audio_data(self):
        return self.audio_data


class SoundPlayer:
    def __init__(self, wav_reader):
        self.wav_reader = wav_reader
        self.playback_speed = 1.0
        self.playing = False
        self.paused = False


    def set_playback_speed(self, speed):
        self.playback_speed = speed

    def play_sound(self):
        p = pyaudio.PyAudio()

        # Open an audio stream
        stream = p.open(format=p.get_format_from_width(self.wav_reader.get_bits_per_sample()//8), 
                        channels=self.wav_reader.get_num_channels(),
                        rate=int(self.wav_reader.get_sample_rate() * self.playback_speed),
                        output=True)

        # Play the audio data
        audio_data = self.wav_reader.get_audio_data()
        for sample in audio_data:
            stream.write(struct.pack('<h', sample))

        # Stop and close the audio stream
        stream.stop_stream()    
        stream.close()
        p.terminate()

class SoundPlayer_update:
    def __init__(self, wav_reader, playback_finished_callback=None):
        self.wav_reader = wav_reader
        self.playback_finished_callback = playback_finished_callback
        self.playing = False
        self.paused = False
        self.thread = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()  

    def play_sound(self):
        if not self.playing:
            self.playing = True
            self.paused = False
            self.stop_event.clear()
            # self.pause_event.clear()  # 删除这行
            self.thread = threading.Thread(target=self._playback)
            self.thread.start()
        elif self.paused:  
            self.paused = False  
            self.pause_event.set()  

    def _playback(self):
        p = pyaudio.PyAudio()
        stream = p.open(format=p.get_format_from_width(self.wav_reader.get_bits_per_sample() // 8),
                        channels=self.wav_reader.get_num_channels(),
                        rate=self.wav_reader.get_sample_rate(),
                        output=True)

        audio_data = self.wav_reader.get_audio_data()

        for sample in audio_data:
            if self.stop_event.is_set():
                break
            self.pause_event.wait()  
            stream.write(struct.pack('<h', sample))

        stream.stop_stream()
        stream.close()
        p.terminate()
        if self.playback_finished_callback:
            self.playback_finished_callback()

        # 播放结束后更新状态
        self.playing = False
        self.paused = False

    def pause(self):
        if not self.paused:
            self.paused = True
            self.pause_event.clear()  
        else:
            self.paused = False
            self.pause_event.set()  
