import ui
import time
import csv
import threading
import os
from pathlib import Path
from rubicon.objc import ObjCClass, ObjCInstance
import ctypes

class DecibelRecorder(ui.View):
    def __init__(self):
        self.background_color = 'white'
        
        # Start Button
        self.start_button = ui.Button(title='Start')
        self.start_button.frame = (50, 50, 100, 50)
        self.start_button.action = self.start_recording
        self.add_subview(self.start_button)

        # Stop Button
        self.stop_button = ui.Button(title='Stop')
        self.stop_button.frame = (200, 50, 100, 50)
        self.stop_button.action = self.stop_recording
        self.add_subview(self.stop_button)
        
        # Label to display decibel levels
        self.label = ui.Label()
        self.label.frame = (50, 120, 300, 50)
        self.label.text_color = 'black'
        self.add_subview(self.label)

        # TextField for CSV interval input
        self.interval_field = ui.TextField()
        self.interval_field.frame = (50, 180, 100, 30)
        self.interval_field.placeholder = 'CSV Interval (s)'
        self.interval_field.text = '60'  # Default interval
        self.interval_field.action = self.interval_changed
        self.add_subview(self.interval_field)

        # Initialize variables
        self.recording = False
        self.decibel_data = []
        self.csv_interval = 60  # Default interval in seconds
        self.last_csv_time = time.time()
        
    def start_recording(self, sender):
        if not self.recording:
            self.recording = True
            self.decibel_data = []
            self.last_csv_time = time.time()
            self.update_label('Recording...')
            threading.Thread(target=self.record_decibels).start()
    
    def stop_recording(self, sender):
        if self.recording:
            self.recording = False
            self.update_label('Stopped')
            self.save_csv()
        
    def interval_changed(self, sender):
        try:
            value = float(sender.text)
            if value > 0:
                self.csv_interval = value
        except ValueError:
            pass  # Ignore invalid input

    def update_label(self, text):
        self.label.text = text

    def record_decibels(self):
        # Set up audio recorder
        AVAudioSession = ObjCClass('AVAudioSession')
        AVAudioRecorder = ObjCClass('AVAudioRecorder')
        NSDictionary = ObjCClass('NSDictionary')
        NSURL = ObjCClass('NSURL')
        NSNumber = ObjCClass('NSNumber')

        audioSession = AVAudioSession.sharedInstance()
        error_ptr = ctypes.c_void_p()
        audioSession.setCategory_error_('AVAudioSessionCategoryPlayAndRecord', error_ptr)
        audioSession.setActive_error_(True, error_ptr)

        settings = NSDictionary.dictionaryWithObjects_forKeys_(
            [
                NSNumber.numberWithInt_(1633772320),  # kAudioFormatAppleIMA4
                NSNumber.numberWithFloat_(44100.0),
                NSNumber.numberWithInt_(1),
                NSNumber.numberWithInt_(128000),
                NSNumber.numberWithInt_(16),
                NSNumber.numberWithInt_(2)  # AVAudioQualityHigh
            ],
            [
                'AVFormatIDKey',
                'AVSampleRateKey',
                'AVNumberOfChannelsKey',
                'AVEncoderBitRateKey',
                'AVLinearPCMBitDepthKey',
                'AVEncoderAudioQualityKey'
            ]
        )

        temp_dir = Path(os.path.expanduser('~/Documents'))
        audio_filename = temp_dir / 'temp.caf'
        audio_url = NSURL.fileURLWithPath_(str(audio_filename))

        recorder = AVAudioRecorder.alloc().initWithURL_settings_error_(audio_url, settings, error_ptr)
        if not recorder:
            ui.delay(lambda: self.update_label('Failed to initialize recorder'), 0)
            return
        recorder.prepareToRecord()
        recorder.setMeteringEnabled_(True)
        recorder.record()

        while self.recording:
            recorder.updateMeters()
            average_power = recorder.averagePowerForChannel_(0)
            peak_power = recorder.peakPowerForChannel_(0)
            timestamp = time.time()
            self.decibel_data.append({
                'timestamp': timestamp,
                'average_power': average_power,
                'peak_power': peak_power
            })
            ui.delay(lambda: self.update_label(f'Decibels: {average_power:.2f} dB'), 0)
            time.sleep(0.5)
            
            # Check if it's time to save CSV
            if time.time() - self.last_csv_time >= self.csv_interval:
                self.save_csv()
                self.last_csv_time = time.time()

        recorder.stop()

    def save_csv(self):
        if not self.decibel_data:
            return
        filename = time.strftime('decibel_data_%Y%m%d_%H%M%S.csv')
        filepath = os.path.join(os.path.expanduser('~/Documents'), filename)
        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = ['timestamp', 'average_power', 'peak_power']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for data in self.decibel_data:
                writer.writerow(data)
        # Clear the data after saving
        self.decibel_data = []

v = DecibelRecorder()
v.present('sheet')
