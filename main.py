"""
Pest Repeller Frequency Controller App
Enhanced with frequency safety warnings and actual frequency generation
"""

from kivy.lang import Builder
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.clock import Clock
from kivy.utils import get_color_from_hex
from kivy.metrics import dp
from kivy.animation import Animation
from kivy.app import App
from kivy.core.audio import SoundLoader
import numpy as np
import tempfile
import os
import wave
import math

from kivymd.app import MDApp
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDRectangleFlatButton, MDIconButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.slider import MDSlider
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.card import MDSeparator
from kivy.properties import StringProperty, NumericProperty, BooleanProperty, ListProperty, DictProperty

# Simple notification function to replace Snackbar
def show_notification(message, duration=1.5):
    """Show a simple notification using a dialog for now"""
    dialog = MDDialog(
        text=message,
        size_hint=(0.8, None),
        height=dp(100),
        buttons=[
            MDFlatButton(
                text="OK",
                on_release=lambda x: dialog.dismiss()
            )
        ]
    )
    Clock.schedule_once(lambda dt: dialog.dismiss(), duration)
    dialog.open()

# Tone generator class
class ToneGenerator:
    def __init__(self):
        self.sounds = {}
        self.temp_files = []
    
    def generate_tone(self, frequency_khz, duration=1.0):
        """Generate a tone at specified frequency in kHz"""
        frequency = frequency_khz * 1000  # Convert to Hz
        sample_rate = 44100
        samples = int(sample_rate * duration)
        
        # Generate sine wave
        t = np.linspace(0, duration, samples, False)
        wave_data = 0.5 * np.sin(2 * np.pi * frequency * t)
        
        # Convert to 16-bit integers
        wave_data = (wave_data * 32767).astype(np.int16)
        
        # Create temporary WAV file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_file.close()
        
        # Write WAV file
        with wave.open(temp_file.name, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)   # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(wave_data.tobytes())
        
        self.temp_files.append(temp_file.name)
        return temp_file.name
    
    def play_tone(self, frequency_khz, duration=1.0):
        """Play a tone at specified frequency"""
        if frequency_khz in self.sounds:
            if self.sounds[frequency_khz].state == 'play':
                self.sounds[frequency_khz].stop()
        
        filename = self.generate_tone(frequency_khz, duration)
        sound = SoundLoader.load(filename)
        if sound:
            sound.volume = 0.5
            sound.play()
            self.sounds[frequency_khz] = sound
            return True
        return False
    
    def stop_tone(self, frequency_khz=None):
        """Stop playing tone(s)"""
        if frequency_khz and frequency_khz in self.sounds:
            self.sounds[frequency_khz].stop()
        else:
            for sound in self.sounds.values():
                sound.stop()
    
    def cleanup(self):
        """Clean up temporary files"""
        for sound in self.sounds.values():
            sound.stop()
        for temp_file in self.temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass


class FrequencyControlCard(MDCard):
    pest_name = StringProperty()
    icon = StringProperty()
    min_freq = NumericProperty()
    max_freq = NumericProperty()
    optimal_freq = NumericProperty()
    current_freq = NumericProperty()
    is_active = BooleanProperty(False)
    audible_threshold = NumericProperty(23)
    safe_threshold = NumericProperty(25)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
    
    def get_card_color(self):
        if self.in_audible_range() and self.app.show_warnings:
            return get_color_from_hex('#FFE5E5')
        elif self.current_freq > self.safe_threshold:
            return get_color_from_hex('#E8F5E9')
        return get_color_from_hex('#FFFFFF')
    
    def in_audible_range(self):
        return self.current_freq <= self.audible_threshold
    
    def get_warning_color(self):
        if self.in_audible_range():
            return get_color_from_hex('#FF5252')
        elif self.current_freq <= self.safe_threshold:
            return get_color_from_hex('#FFB74D')
        return get_color_from_hex('#4CAF50')
    
    def get_warning_opacity(self):
        if self.in_audible_range() and self.app.show_warnings:
            return 1
        elif self.current_freq <= self.safe_threshold and self.app.show_warnings:
            return 0.7
        return 0
    
    def get_warning_text(self):
        if self.in_audible_range():
            return "⚠️ May be audible to humans (especially children)"
        elif self.current_freq <= self.safe_threshold:
            return "⚠️ Borderline range - some people may hear this"
        return "✓ Ultrasonic - Safe for human ears"
    
    def get_slider_color(self):
        if self.in_audible_range():
            return get_color_from_hex('#FF5252')
        elif self.current_freq <= self.safe_threshold:
            return get_color_from_hex('#FFB74D')
        return get_color_from_hex('#4CAF50')
    
    def get_intensity_color(self):
        intensity = self.calculate_intensity()
        if intensity > 80:
            return [1, 0, 0, 1]
        elif intensity > 50:
            return [1, 0.65, 0, 1]
        return [0, 0.8, 0, 1]
    
    def get_safety_color(self):
        safety = self.calculate_safety_score()
        if safety > 80:
            return [0, 0.8, 0, 1]
        elif safety > 50:
            return [1, 0.65, 0, 1]
        return [1, 0, 0, 1]
    
    def calculate_safety_score(self):
        if self.current_freq >= self.safe_threshold:
            return 100
        elif self.current_freq <= self.audible_threshold:
            return max(0, (self.current_freq / self.audible_threshold) * 50)
        else:
            range_size = self.safe_threshold - self.audible_threshold
            position = self.current_freq - self.audible_threshold
            return 50 + (position / range_size) * 50
    
    def get_frequency_info(self):
        info = f"{self.pest_name} Frequency Information:\n"
        info += f"Range: {self.min_freq}-{self.max_freq} kHz\n"
        info += f"Optimal: {self.optimal_freq} kHz\n\n"
        
        if self.min_freq < 20:
            info += "⚠️ Some frequencies in this range are audible to humans.\n"
        elif self.min_freq < 25:
            info += "⚠️ Lower end of this range may be audible to young people.\n"
        else:
            info += "✓ This pest uses ultrasonic frequencies (safe for humans).\n"
        
        info += "\nHuman hearing range: 20 Hz - 20,000 Hz (20 kHz)"
        return info
    
    def show_frequency_info(self):
        if not self.app.show_tooltips:
            return
            
        dialog = MDDialog(
            title=f"{self.pest_name} Frequency Guide",
            text=self.get_frequency_info(),
            buttons=[
                MDFlatButton(
                    text="GOT IT",
                    on_release=lambda x: dialog.dismiss()
                )
            ]
        )
        dialog.open()
    
    def has_safe_mode(self):
        return self.max_freq > self.safe_threshold
    
    def reset_to_optimal(self):
        self.current_freq = self.optimal_freq
        self.ids.slider.value = self.current_freq
        self.update_bars()
        
        safety_note = " (may be audible)" if self.in_audible_range() else " (ultrasonic)"
        self.show_notification(f"Reset {self.pest_name} to optimal frequency{safety_note}")
    
    def reset_to_safe(self):
        if self.max_freq > self.safe_threshold:
            self.current_freq = max(self.safe_threshold + 2, self.min_freq)
            self.ids.slider.value = self.current_freq
            self.update_bars()
            self.show_notification(f"Set {self.pest_name} to safe ultrasonic frequency")
    
    def on_checkbox_active(self, checkbox, value):
        self.is_active = value
        self.update_bars()
        
        # Update the app's active_pests dictionary
        self.app.active_pests[self.pest_name] = value
        
        if value:
            safety_msg = " (audible range!)" if self.in_audible_range() else ""
            self.show_notification(f"{self.pest_name} repeller activated{safety_msg}")
        else:
            self.show_notification(f"{self.pest_name} repeller deactivated")
    
    def on_freq_change(self, slider, value):
        self.current_freq = int(value)
        self.update_bars()
        
        if self.app.show_warnings and self.in_audible_range():
            anim = Animation(opacity=0.8, duration=0.5) + Animation(opacity=1, duration=0.5)
            anim.repeat = True
            anim.start(self)
    
    def update_bars(self):
        self.ids.intensity_bar.value = self.calculate_intensity()
        self.ids.safety_bar.value = self.calculate_safety_score()
    
    def calculate_intensity(self):
        range_size = self.max_freq - self.min_freq
        if range_size == 0:
            return 100
        position = (self.current_freq - self.min_freq) / range_size
        optimal_pos = (self.optimal_freq - self.min_freq) / range_size
        intensity = 100 * math.exp(-((position - optimal_pos) * 5) ** 2)
        return int(intensity)
    
    def test_frequency(self):
        if self.is_active:
            intensity = self.calculate_intensity()
            safety = self.calculate_safety_score()
            
            message = (f"Testing {self.pest_name} at {int(self.current_freq)} kHz\n"
                      f"Effectiveness: {intensity}%\n"
                      f"Human Safety: {safety}%")
            
            if self.in_audible_range():
                message += "\n⚠️ WARNING: This frequency may be audible!"
            
            dialog = MDDialog(
                title="Frequency Test",
                text=message,
                buttons=[
                    MDFlatButton(
                        text="OK",
                        on_release=lambda x: dialog.dismiss()
                    )
                ]
            )
            dialog.open()
            
            if self.app.sound_enabled:
                self.app.play_frequency(self.current_freq)
        else:
            self.show_notification(f"Activate {self.pest_name} repeller first")
    
    def show_notification(self, message):
        show_notification(message)


class MainScreen(Screen):
    def on_enter(self):
        app = App.get_running_app()
        app.update_pest_list()


class SettingsScreen(Screen):
    pass


class EducationScreen(Screen):
    pass


class PestRepellerApp(MDApp):
    master_volume = NumericProperty(0.5)
    sound_enabled = BooleanProperty(True)
    show_warnings = BooleanProperty(True)
    show_tooltips = BooleanProperty(True)
    operation_mode = StringProperty("Simulation")
    is_repelling = BooleanProperty(False)
    
    pest_data = ListProperty([
        {
            'name': 'Mosquitoes',
            'icon': 'bug',
            'min_freq': 38,
            'max_freq': 44,
            'optimal': 42,
        },
        {
            'name': 'Rats',
            'icon': 'rat',
            'min_freq': 20,
            'max_freq': 35,
            'optimal': 28,
        },
        {
            'name': 'Cockroaches',
            'icon': 'bug',
            'min_freq': 25,
            'max_freq': 45,
            'optimal': 35,
        },
        {
            'name': 'Spiders',
            'icon': 'spider-web',
            'min_freq': 30,
            'max_freq': 60,
            'optimal': 45,
        },
        {
            'name': 'Ants',
            'icon': 'bug',
            'min_freq': 40,
            'max_freq': 70,
            'optimal': 55,
        },
        {
            'name': 'Flies',
            'icon': 'bug',
            'min_freq': 45,
            'max_freq': 65,
            'optimal': 55,
        }
    ])
    
    active_pests = DictProperty({})
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tone_generator = ToneGenerator()
        self.repelling_event = None
    
    def build(self):
        self.theme_cls.primary_palette = "Teal"
        self.theme_cls.theme_style = "Light"
        
        for pest in self.pest_data:
            self.active_pests[pest['name']] = False
        
        return Builder.load_string(KV)
    
    def on_start(self):
        self.update_pest_list()
    
    def on_stop(self):
        self.stop_repelling()
        self.tone_generator.cleanup()
    
    def update_pest_list(self):
        if hasattr(self.root, 'get_screen'):
            main_screen = self.root.get_screen('main')
            container = main_screen.ids.pests_container
            container.clear_widgets()
            
            for pest in self.pest_data:
                card = FrequencyControlCard(
                    pest_name=pest['name'],
                    icon=pest['icon'],
                    min_freq=pest['min_freq'],
                    max_freq=pest['max_freq'],
                    optimal_freq=pest['optimal'],
                    current_freq=pest['optimal'],
                    is_active=self.active_pests.get(pest['name'], False)
                )
                container.add_widget(card)
    
    def toggle_all_pests(self, activate):
        for pest in self.pest_data:
            self.active_pests[pest['name']] = activate
        
        main_screen = self.root.get_screen('main')
        for child in main_screen.ids.pests_container.children:
            if isinstance(child, FrequencyControlCard):
                child.is_active = activate
                child.ids.checkbox.active = activate
        
        status = "activated" if activate else "deactivated"
        show_notification(f"All repellers {status}")
    
    def start_repelling(self):
        if self.is_repelling:
            return
        
        # First, update active_pests dictionary from current checkbox states
        main_screen = self.root.get_screen('main')
        active_frequencies = []
        audible_count = 0
        
        for child in main_screen.ids.pests_container.children:
            if isinstance(child, FrequencyControlCard):
                # Update the active_pests dictionary with current checkbox state
                self.active_pests[child.pest_name] = child.is_active
                
                if child.is_active:
                    if child.in_audible_range():
                        audible_count += 1
                    active_frequencies.append(child.current_freq)
        
        active_count = len(active_frequencies)
        
        if active_count > 0:
            self.is_repelling = True
            
            message = f"Repelling started for {active_count} pest type(s)"
            if audible_count > 0 and self.show_warnings:
                message += f"\n⚠️ {audible_count} active repeller(s) may be audible to humans"
            
            dialog = MDDialog(
                title="Repelling Started",
                text=message,
                buttons=[
                    MDFlatButton(
                        text="OK",
                        on_release=lambda x: dialog.dismiss()
                    )
                ]
            )
            dialog.open()
            
            if self.sound_enabled and active_frequencies:
                self.repelling_event = Clock.schedule_interval(
                    lambda dt: self.play_next_frequency(active_frequencies), 
                    2.0
                )
        else:
            show_notification("No pests selected for repelling")
    
    def play_next_frequency(self, frequencies):
        if not self.is_repelling:
            return False
            
        import random
        freq = random.choice(frequencies)
        self.play_frequency(freq, duration=1.5)
        return True
    
    def stop_repelling(self):
        self.is_repelling = False
        if self.repelling_event:
            self.repelling_event.cancel()
            self.repelling_event = None
        self.tone_generator.stop_tone()
        show_notification("Repelling stopped")
    
    def play_frequency(self, frequency_khz, duration=1.0):
        if self.sound_enabled:
            self.tone_generator.play_tone(frequency_khz, duration)
    
    def play_test_sound(self):
        if self.sound_enabled:
            self.play_frequency(25, 0.5)
    
    def open_drawer(self):
        self.dialog = MDDialog(
            title="Menu",
            text="Select an option:",
            buttons=[
                MDFlatButton(
                    text="Home",
                    on_release=lambda x: self.close_dialog_and_do("home")
                ),
                MDFlatButton(
                    text="Frequency Guide",
                    on_release=lambda x: self.close_dialog_and_do("guide")
                ),
                MDFlatButton(
                    text="Close",
                    on_release=lambda x: self.dialog.dismiss()
                )
            ]
        )
        self.dialog.open()
    
    def close_dialog_and_do(self, action):
        if hasattr(self, 'dialog'):
            self.dialog.dismiss()
        
        if action == "guide":
            self.open_education()
        elif action == "home":
            self.go_back()
    
    def open_settings(self):
        self.root.current = 'settings'
    
    def open_education(self):
        self.root.current = 'education'
    
    def go_back(self):
        self.root.current = 'main'
    
    def show_info(self):
        self.dialog = MDDialog(
            title="About Pest Repeller",
            text="This app simulates controlling ultrasonic frequencies "
                 "to repel various pests. Select the pests you want to repel "
                 "and adjust frequencies for optimal effectiveness.\n\n"
                 "⚠️ Important Safety Note:\n"
                 "Frequencies below 23 kHz may be audible to humans, "
                 "especially children and young adults. The app provides "
                 "warnings when frequencies enter the potentially audible range.\n\n"
                 "Note: This app can generate actual ultrasonic frequencies. "
                 "Use with caution and be aware of your surroundings.",
            buttons=[
                MDFlatButton(
                    text="GOT IT",
                    on_release=lambda x: self.dialog.dismiss()
                )
            ]
        )
        self.dialog.open()
    
    def set_volume(self, value):
        self.master_volume = value
    
    def toggle_sound(self, enabled):
        self.sound_enabled = enabled
        if not enabled:
            self.stop_repelling()
    
    def toggle_warnings(self, enabled):
        self.show_warnings = enabled
        self.update_pest_list()
    
    def toggle_tooltips(self, enabled):
        self.show_tooltips = enabled
    
    def change_mode(self, mode_text):
        self.operation_mode = mode_text
        show_notification(f"Mode changed to: {mode_text}")
    
    def dismiss_dialog(self):
        if hasattr(self, 'dialog'):
            self.dialog.dismiss()


KV = '''
<FrequencyControlCard>:
    orientation: 'vertical'
    padding: dp(16)
    spacing: dp(8)
    size_hint_y: None
    height: dp(280)
    elevation: 2
    radius: [dp(15)]
    md_bg_color: self.get_card_color()
    
    MDBoxLayout:
        size_hint_y: 0.15
        pos_hint: {"top": 1}
        
        MDIcon:
            icon: root.icon
            size_hint_x: 0.15
            pos_hint: {"center_y": 0.5}
            
        MDLabel:
            text: root.pest_name
            font_style: "H6"
            size_hint_x: 0.6
            halign: 'left'
            
        MDBoxLayout:
            size_hint_x: 0.25
            spacing: dp(4)
            pos_hint: {"center_y": 0.5}
            
            MDIconButton:
                icon: "information-outline"
                on_release: root.show_frequency_info()
                theme_text_color: "Hint"
                
            MDCheckbox:
                id: checkbox
                size_hint_x: 0.5
                active: root.is_active
                on_active: root.on_checkbox_active(*args)
    
    MDCard:
        size_hint_y: 0.1
        md_bg_color: root.get_warning_color()
        padding: dp(8)
        radius: [dp(8)]
        opacity: root.get_warning_opacity()
        
        MDBoxLayout:
            MDIcon:
                icon: "ear-hearing"
                size_hint_x: 0.15
                theme_text_color: "Custom"
                text_color: 1, 1, 1, 1 if root.in_audible_range() else 0
                
            MDLabel:
                text: root.get_warning_text()
                font_style: "Caption"
                theme_text_color: "Custom"
                text_color: 1, 1, 1, 1
                halign: 'center'
    
    MDBoxLayout:
        size_hint_y: 0.15
        pos_hint: {"center_y": 0.5}
        
        MDIcon:
            icon: "wave"
            size_hint_x: 0.15
            
        MDBoxLayout:
            orientation: 'vertical'
            size_hint_x: 0.85
            
            MDBoxLayout:
                MDLabel:
                    text: f"Current: {int(root.current_freq)} kHz"
                    font_style: "Subtitle2"
                    
                MDLabel:
                    text: f"Range: {root.min_freq}-{root.max_freq} kHz"
                    font_style: "Caption"
                    theme_text_color: "Hint"
                    halign: 'right'
            
            MDBoxLayout:
                MDLabel:
                    text: f"Optimal: {root.optimal_freq} kHz"
                    font_style: "Caption"
                    theme_text_color: "Secondary"
    
    MDSlider:
        id: slider
        min: root.min_freq
        max: root.max_freq
        value: root.current_freq
        step: 1
        size_hint_y: 0.15
        on_value: root.on_freq_change(*args)
        color: root.get_slider_color()
    
    MDBoxLayout:
        size_hint_y: 0.2
        spacing: dp(8)
        
        MDBoxLayout:
            orientation: 'vertical'
            size_hint_x: 0.5
            
            MDLabel:
                text: "Effectiveness"
                font_style: "Caption"
                halign: 'center'
                
            MDProgressBar:
                id: intensity_bar
                value: root.calculate_intensity()
                max: 100
                color: root.get_intensity_color()
        
        MDBoxLayout:
            orientation: 'vertical'
            size_hint_x: 0.5
            
            MDLabel:
                text: "Safety Level"
                font_style: "Caption"
                halign: 'center'
                
            MDProgressBar:
                id: safety_bar
                value: root.calculate_safety_score()
                max: 100
                color: root.get_safety_color()
    
    MDBoxLayout:
        size_hint_y: 0.15
        spacing: dp(8)
        
        MDRaisedButton:
            text: "Test"
            on_release: root.test_frequency()
            md_bg_color: app.theme_cls.primary_color
            size_hint_x: 0.5
            
        MDRectangleFlatButton:
            text: "Optimal"
            on_release: root.reset_to_optimal()
            size_hint_x: 0.25
            
        MDRectangleFlatButton:
            text: "Safe"
            on_release: root.reset_to_safe()
            size_hint_x: 0.25
            disabled: not root.has_safe_mode()

<MainScreen>:
    name: 'main'
    
    BoxLayout:
        orientation: 'vertical'
        spacing: dp(8)
        padding: dp(16)
        
        MDTopAppBar:
            title: "Pest Repeller Controller"
            elevation: 4
            pos_hint: {"top": 1}
            left_action_items: [["menu", lambda x: app.open_drawer()]]
            right_action_items: [["cog", lambda x: app.open_settings()], ["school", lambda x: app.open_education()], ["information", lambda x: app.show_info()]]
        
        MDScrollView:
            MDGridLayout:
                id: pests_container
                cols: 1
                spacing: dp(16)
                padding: dp(8)
                size_hint_y: None
                height: self.minimum_height
                adaptive_height: True
        
        MDBoxLayout:
            size_hint_y: 0.15
            spacing: dp(8)
            padding: [dp(8), dp(8)]
            adaptive_height: False
            height: dp(60)
            pos_hint: {"bottom": 1}
            
            MDRaisedButton:
                text: "ACTIVATE ALL"
                on_release: app.toggle_all_pests(True)
                icon: "power"
                size_hint_x: 0.25
                
            MDRaisedButton:
                text: "DEACTIVATE ALL"
                on_release: app.toggle_all_pests(False)
                icon: "power-off"
                size_hint_x: 0.25
                
            MDRaisedButton:
                text: "START"
                on_release: app.start_repelling()
                md_bg_color: 0.2, 0.7, 0.3, 1
                icon: "play"
                size_hint_x: 0.25
                
            MDRaisedButton:
                text: "STOP"
                on_release: app.stop_repelling()
                md_bg_color: 0.9, 0.2, 0.2, 1
                icon: "stop"
                size_hint_x: 0.25

<SettingsScreen>:
    name: 'settings'
    
    BoxLayout:
        orientation: 'vertical'
        
        MDTopAppBar:
            title: "Settings"
            elevation: 4
            left_action_items: [["arrow-left", lambda x: app.go_back()]]
        
        MDScrollView:
            MDGridLayout:
                cols: 1
                spacing: dp(8)
                padding: dp(16)
                size_hint_y: None
                height: self.minimum_height
                adaptive_height: True
                
                MDCard:
                    orientation: 'vertical'
                    padding: dp(16)
                    size_hint_y: None
                    height: dp(280)
                    
                    MDLabel:
                        text: "Sound Settings"
                        font_style: "H6"
                    
                    MDBoxLayout:
                        size_hint_y: None
                        height: dp(48)
                        
                        MDIcon:
                            icon: "volume-high"
                        MDLabel:
                            text: "Master Volume"
                        MDSlider:
                            id: volume_slider
                            min: 0
                            max: 100
                            value: app.master_volume * 100
                            on_value: app.set_volume(args[1]/100)
                    
                    MDBoxLayout:
                        size_hint_y: None
                        height: dp(48)
                        
                        MDCheckbox:
                            id: sound_check
                            active: app.sound_enabled
                            on_active: app.toggle_sound(args[1])
                        MDLabel:
                            text: "Enable Sound Effects"
                    
                    MDSeparator:
                        height: dp(1)
                    
                    MDLabel:
                        text: "Safety Warnings"
                        font_style: "Subtitle1"
                    
                    MDBoxLayout:
                        size_hint_y: None
                        height: dp(48)
                        
                        MDCheckbox:
                            id: warning_check
                            active: app.show_warnings
                            on_active: app.toggle_warnings(args[1])
                        MDLabel:
                            text: "Show audible frequency warnings"
                    
                    MDBoxLayout:
                        size_hint_y: None
                        height: dp(48)
                        
                        MDCheckbox:
                            id: tooltip_check
                            active: app.show_tooltips
                            on_active: app.toggle_tooltips(args[1])
                        MDLabel:
                            text: "Show educational tooltips"
                
                MDCard:
                    orientation: 'vertical'
                    padding: dp(16)
                    size_hint_y: None
                    height: dp(180)
                    
                    MDLabel:
                        text: "Operation Mode"
                        font_style: "H6"
                    
                    MDRaisedButton:
                        text: "Simulation"
                        on_release: app.change_mode("Simulation")
                        size_hint_x: 0.9
                        pos_hint: {"center_x": 0.5}
                        md_bg_color: app.theme_cls.primary_color if app.operation_mode == "Simulation" else [0.5, 0.5, 0.5, 0.5]
                    
                    MDRaisedButton:
                        text: "Real Device"
                        on_release: app.change_mode("Real Device")
                        size_hint_x: 0.9
                        pos_hint: {"center_x": 0.5}
                        md_bg_color: app.theme_cls.primary_color if app.operation_mode == "Real Device" else [0.5, 0.5, 0.5, 0.5]
                    
                    MDRaisedButton:
                        text: "Demo"
                        on_release: app.change_mode("Demo")
                        size_hint_x: 0.9
                        pos_hint: {"center_x": 0.5}
                        md_bg_color: app.theme_cls.primary_color if app.operation_mode == "Demo" else [0.5, 0.5, 0.5, 0.5]
                
                MDCard:
                    orientation: 'vertical'
                    padding: dp(16)
                    size_hint_y: None
                    height: dp(200)
                    
                    MDLabel:
                        text: "Frequency Safety Guide"
                        font_style: "H6"
                    
                    MDLabel:
                        text: "• 20-23 kHz: May be audible to young people"
                        font_style: "Body2"
                    
                    MDLabel:
                        text: "• 23-25 kHz: Borderline, some may hear"
                        font_style: "Body2"
                    
                    MDLabel:
                        text: "• 25+ kHz: Ultrasonic (inaudible to humans)"
                        font_style: "Body2"
                    
                    MDLabel:
                        text: "• 20 kHz is the limit of human hearing"
                        font_style: "Body2"
                    
                    MDRaisedButton:
                        text: "Learn More"
                        on_release: app.open_education()
                        size_hint_x: 0.5
                        pos_hint: {"center_x": 0.5}

<EducationScreen>:
    name: 'education'
    
    BoxLayout:
        orientation: 'vertical'
        
        MDTopAppBar:
            title: "Frequency Education"
            elevation: 4
            left_action_items: [["arrow-left", lambda x: app.go_back()]]
        
        ScrollView:
            MDGridLayout:
                cols: 1
                spacing: dp(16)
                padding: dp(24)
                size_hint_y: None
                height: self.minimum_height
                adaptive_height: True
                
                MDCard:
                    orientation: 'vertical'
                    padding: dp(24)
                    spacing: dp(16)
                    
                    MDLabel:
                        text: "Understanding Ultrasonic Frequencies"
                        font_style: "H5"
                        halign: 'center'
                    
                    MDLabel:
                        text: "Human Hearing Range: 20 Hz - 20,000 Hz (20 kHz)"
                        font_style: "Subtitle1"
                        theme_text_color: "Secondary"
                        halign: 'center'
                    
                    MDLabel:
                        text: "[b]Frequency Scale Visualization[/b]"
                        markup: True
                        font_style: "Body1"
                        halign: 'center'
                    
                    MDLabel:
                        text: "0 kHz [color=#2196F3]██████[/color] 20 kHz [color=#FF9800]████[/color] 25 kHz [color=#4CAF50]████████[/color] 70 kHz"
                        markup: True
                        font_style: "Body2"
                        halign: 'center'
                    
                    MDSeparator:
                        height: dp(1)
                    
                    MDLabel:
                        text: "Frequency Zones:"
                        font_style: "H6"
                    
                    MDBoxLayout:
                        spacing: dp(8)
                        
                        MDIcon:
                            icon: "circle"
                            theme_text_color: "Custom"
                            text_color: 0, 0.7, 0.9, 1
                        
                        MDLabel:
                            text: "0-20 kHz: Audible to humans"
                            font_style: "Body1"
                    
                    MDBoxLayout:
                        spacing: dp(8)
                        
                        MDIcon:
                            icon: "circle"
                            theme_text_color: "Custom"
                            text_color: 1, 0.5, 0, 1
                        
                        MDLabel:
                            text: "20-25 kHz: Borderline (audible to some)"
                            font_style: "Body1"
                    
                    MDBoxLayout:
                        spacing: dp(8)
                        
                        MDIcon:
                            icon: "circle"
                            theme_text_color: "Custom"
                            text_color: 0, 0.8, 0, 1
                        
                        MDLabel:
                            text: "25+ kHz: Ultrasonic (inaudible to humans)"
                            font_style: "Body1"
                    
                    MDSeparator:
                        height: dp(1)
                    
                    MDLabel:
                        text: "Pest-Specific Information"
                        font_style: "H6"
                    
                    MDGridLayout:
                        cols: 2
                        spacing: dp(16)
                        adaptive_height: True
                        
                        MDCard:
                            orientation: 'vertical'
                            padding: dp(8)
                            size_hint_y: None
                            height: dp(120)
                            
                            MDLabel:
                                text: "Mosquitoes"
                                font_style: "Subtitle2"
                            MDLabel:
                                text: "38-44 kHz"
                                font_style: "Caption"
                            MDLabel:
                                text: "✓ Ultrasonic range"
                                font_style: "Caption"
                                theme_text_color: "Primary"
                        
                        MDCard:
                            orientation: 'vertical'
                            padding: dp(8)
                            size_hint_y: None
                            height: dp(120)
                            
                            MDLabel:
                                text: "Rats"
                                font_style: "Subtitle2"
                            MDLabel:
                                text: "20-35 kHz"
                                font_style: "Caption"
                            MDLabel:
                                text: "⚠️ Lower range audible"
                                font_style: "Caption"
                                theme_text_color: "Error"
                        
                        MDCard:
                            orientation: 'vertical'
                            padding: dp(8)
                            size_hint_y: None
                            height: dp(120)
                            
                            MDLabel:
                                text: "Cockroaches"
                                font_style: "Subtitle2"
                            MDLabel:
                                text: "25-45 kHz"
                                font_style: "Caption"
                            MDLabel:
                                text: "✓ Mostly ultrasonic"
                                font_style: "Caption"
                                theme_text_color: "Primary"
                        
                        MDCard:
                            orientation: 'vertical'
                            padding: dp(8)
                            size_hint_y: None
                            height: dp(120)
                            
                            MDLabel:
                                text: "Spiders"
                                font_style: "Subtitle2"
                            MDLabel:
                                text: "30-60 kHz"
                                font_style: "Caption"
                            MDLabel:
                                text: "✓ Ultrasonic range"
                                font_style: "Caption"
                                theme_text_color: "Primary"

ScreenManager:
    MainScreen:
    SettingsScreen:
    EducationScreen:
'''


if __name__ == '__main__':
    PestRepellerApp().run()
