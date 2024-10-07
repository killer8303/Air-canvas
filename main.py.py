import cv2
import numpy as np
import mediapipe as mp
from collections import deque

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.graphics import Color, Line
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.graphics.texture import Texture


# Kivy Widget for the drawing area
class DrawingWidget(Widget):
    def __init__(self, **kwargs):
        super(DrawingWidget, self).__init__(**kwargs)
        self.points = {
            'blue': deque(maxlen=1024),
            'green': deque(maxlen=1024),
            'red': deque(maxlen=1024),
            'yellow': deque(maxlen=1024)
        }
        self.current_color = 'blue'
        self.line_width = 2

    def on_touch_down(self, touch):
        self.add_point(touch.x, touch.y)

    def on_touch_move(self, touch):
        self.add_point(touch.x, touch.y)

    def add_point(self, x, y):
        # Add points to the deque of the selected color
        self.points[self.current_color].append((x, y))
        self.update_canvas()

    def update_canvas(self):
        self.canvas.clear()
        # Draw all the points on the canvas
        for color, pts in self.points.items():
            if color == 'blue':
                Color(0, 0, 1)
            elif color == 'green':
                Color(0, 1, 0)
            elif color == 'red':
                Color(1, 0, 0)
            elif color == 'yellow':
                Color(1, 1, 0)
            
            with self.canvas:
                for i in range(1, len(pts)):
                    Line(points=[pts[i-1], pts[i]], width=self.line_width)

    def clear_canvas(self):
        for color in self.points:
            self.points[color].clear()
        self.canvas.clear()


# Main Kivy App
class PaintApp(App):
    def build(self):
        self.camera = CameraInput()
        layout = BoxLayout(orientation='vertical')

        # The actual drawing widget
        self.drawing_widget = DrawingWidget()
        layout.add_widget(self.drawing_widget)

        # Create a horizontal layout for the buttons
        button_layout = BoxLayout(size_hint=(1, 0.1), height=50)

        # Buttons for selecting colors
        clear_btn = Button(text="CLEAR", on_press=self.clear_canvas)
        blue_btn = Button(text="BLUE", on_press=lambda x: self.set_color('blue'))
        green_btn = Button(text="GREEN", on_press=lambda x: self.set_color('green'))
        red_btn = Button(text="RED", on_press=lambda x: self.set_color('red'))
        yellow_btn = Button(text="YELLOW", on_press=lambda x: self.set_color('yellow'))

        button_layout.add_widget(clear_btn)
        button_layout.add_widget(blue_btn)
        button_layout.add_widget(green_btn)
        button_layout.add_widget(red_btn)
        button_layout.add_widget(yellow_btn)

        layout.add_widget(button_layout)

        Clock.schedule_interval(self.update_camera, 1.0 / 30.0)  # 30 FPS camera feed
        return layout

    def update_camera(self, dt):
        frame = self.camera.get_frame()

        # Process the frame using OpenCV (add hand-tracking logic)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # OpenCV result here can be used to draw onto Kivy's canvas

    def clear_canvas(self, instance):
        self.drawing_widget.clear_canvas()

    def set_color(self, color):
        self.drawing_widget.current_color = color


# Camera input class to handle the video feed
class CameraInput:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.mp_hands = mp.solutions.hands.Hands(max_num_hands=1, min_detection_confidence=0.7)

    def get_frame(self):
        ret, frame = self.cap.read()
        frame = cv2.flip(frame, 1)  # Mirror the camera frame
        return frame

    def release(self):
        self.cap.release()


if __name__ == '__main__':
    PaintApp().run()
