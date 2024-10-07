import os
import sqlite3
import cv2
import numpy as np
import mediapipe as mp
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.graphics.texture import Texture
from kivy.graphics import Rectangle, Line, Color
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.popup import Popup
import time  # For generating unique filenames

# Database initialization
db_file = 'users.db'
if not os.path.exists(db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE users (username TEXT PRIMARY KEY, password TEXT)''')
    conn.commit()
    conn.close()

# User Management Functions
def create_user(username, password):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def validate_user(username, password):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
    result = cursor.fetchone()
    conn.close()
    return result is not None

# Login Screen
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super(LoginScreen, self).__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Username and Password inputs
        self.username_input = TextInput(hint_text='Username', multiline=False)
        self.password_input = TextInput(hint_text='Password', multiline=False, password=True)

        # Buttons
        login_button = Button(text='Login', size_hint=(1, 0.2))
        register_button = Button(text='Register', size_hint=(1, 0.2))

        login_button.bind(on_press=self.login)
        register_button.bind(on_press=self.register)

        layout.add_widget(Label(text='Login', font_size=32))
        layout.add_widget(self.username_input)
        layout.add_widget(self.password_input)
        layout.add_widget(login_button)
        layout.add_widget(register_button)

        self.add_widget(layout)

    def login(self, instance):
        username = self.username_input.text
        password = self.password_input.text
        if validate_user(username, password):
            self.manager.current = 'drawing'  # Switch to drawing screen
        else:
            self.show_popup('Login Failed', 'Invalid username or password')

    def register(self, instance):
        username = self.username_input.text
        password = self.password_input.text
        if create_user(username, password):
            self.show_popup('Registration Success', 'User created successfully')
        else:
            self.show_popup('Registration Failed', 'Username already exists')

    def show_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(None, None), size=(400, 200))
        popup.open()

# Drawing Screen
class PaintApp(Widget):
    def __init__(self, **kwargs):
        super(PaintApp, self).__init__(**kwargs)

        # Ensure the drawings directory exists
        self.ensure_drawings_directory()

        # Initialize OpenCV and Mediapipe
        self.cap = cv2.VideoCapture(0)
        self.hands = mp.solutions.hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
        self.mpDraw = mp.solutions.drawing_utils

        # Drawing properties
        self.colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0)]  # Red, Green, Blue, Yellow
        self.colorIndex = 0
        self.points = [[] for _ in self.colors]  # Store lines for each color
        self.line_width = 2

        # Schedule updates
        Clock.schedule_interval(self.update, 1.0 / 30.0)

    def ensure_drawings_directory(self):
        # Check if the drawings directory exists; if not, create it
        if not os.path.exists('drawings'):
            os.makedirs('drawings')
            print("Created drawings directory.")

    def update(self, dt):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            framergb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            result = self.hands.process(framergb)
            if result.multi_hand_landmarks:
                landmarks = []
                for handlms in result.multi_hand_landmarks:
                    for lm in handlms.landmark:
                        lmx = int(lm.x * frame.shape[1])
                        lmy = int(lm.y * frame.shape[0])
                        landmarks.append([lmx, lmy])
                    self.mpDraw.draw_landmarks(frame, handlms, mp.solutions.hands.HAND_CONNECTIONS)

                fore_finger = (landmarks[8][0], landmarks[8][1])
                thumb = (landmarks[4][0], landmarks[4][1])

                if (thumb[1] - fore_finger[1]) < 30:
                    if len(self.points[self.colorIndex]) == 0 or len(self.points[self.colorIndex][-1]) > 0:
                        self.points[self.colorIndex].append([])  # Start a new line
                else:
                    if len(self.points[self.colorIndex]) > 0:
                        self.points[self.colorIndex][-1].append(fore_finger)

            buf = cv2.flip(frame, 0).tobytes()
            texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='rgb')
            texture.blit_buffer(buf, colorfmt='rgb', bufferfmt='ubyte')

            self.canvas.clear()
            with self.canvas:
                Rectangle(texture=texture, pos=(0, 0), size=Window.size)

                for i, color in enumerate(self.colors):
                    Color(*color)
                    for line in self.points[i]:
                        if len(line) > 1:
                            Line(points=[coord for point in line for coord in point], width=self.line_width)

    def on_touch_down(self, touch):
        self.colorIndex = (self.colorIndex + 1) % len(self.colors)

    def save_drawing(self):
        # Save to 'drawings/' directory with a unique filename
        timestamp = int(time.time())
        filename = os.path.join('drawings', f'drawing_{timestamp}.png')

        # Create a blank image to draw on
        img = np.ones((Window.height, Window.width, 3), dtype=np.uint8) * 255
        for i, color in enumerate(self.colors):
            bgr_color = (int(color[2] * 255), int(color[1] * 255), int(color[0] * 255))
            for line in self.points[i]:
                for j in range(len(line) - 1):
                    cv2.line(img, line[j], line[j + 1], bgr_color, self.line_width)

        cv2.imwrite(filename, img)
        print(f"Saved drawing as {filename}")

class DrawingScreen(Screen):
    def __init__(self, **kwargs):
        super(DrawingScreen, self).__init__(**kwargs)
        layout = BoxLayout(orientation='vertical')

        self.paint_widget = PaintApp()
        layout.add_widget(self.paint_widget)

        save_button = Button(text="Save Drawing", size_hint=(1, 0.1))
        save_button.bind(on_press=self.save_drawing)

        layout.add_widget(save_button)
        self.add_widget(layout)

    def save_drawing(self, instance):
        self.paint_widget.save_drawing()

# Screen Manager to switch between screens
class DrawingApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(DrawingScreen(name='drawing'))
        return sm

if __name__ == "__main__":
    DrawingApp().run()
