
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import pandas as pd
import argparse
import os
import sys
import os
sys.path.append("/hdd/side_projects/imu_project/MetaWear-SDK-Python")

from mbientlab.metawear import MetaWear, libmetawear, parse_value
from mbientlab.metawear.cbindings import *
import yaml
from threading import Event, Thread
from queue import Queue
import numpy as np
from time import sleep, strftime
from datetime import datetime
# from utils import convert_millis_to_datetime
from imusensor.filters.kalman import Kalman
from datetime import datetime
from collections import deque
import pandas as pd


vertices = (
    (1, -2, -1),  # 0
    (1, 2, -1),   # 1
    (-1, 2, -1),  # 2
    (-1, -2, -1), # 3
    (1, -2, 1),   # 4
    (1, 2, 1),    # 5
    (-1, -2, 1),  # 6
    (-1, 2, 1)    # 7
)

# Define edges for the wireframe
edges = (
    (0, 1), (0, 3), (0, 4),  # Edges from vertex 0
    (2, 1), (2, 3), (2, 7),  # Edges from vertex 2
    (6, 3), (6, 4), (6, 7),  # Edges from vertex 6
    (5, 1), (5, 4), (5, 7)   # Edges from vertex 5
)

# Define the faces of the cube (each face is defined by 4 vertices)
faces = (
    (0, 1, 2, 3),  # Back face
    (4, 5, 6, 7),  # Front face
    (0, 1, 5, 4),  # Right face
    (2, 3, 6, 7),  # Left face
    (1, 2, 7, 5),  # Top face
    (0, 3, 6, 4)   # Bottom face
)

# Define colors for each face (RGBA)
colors = (
    (1, 0, 0, 0.5),  # Red (Back)
    (0, 1, 0, 0.5),  # Green (Front)
    (0, 0, 1, 0.5),  # Blue (Right)
    (1, 1, 0, 0.5),  # Yellow (Left)
    (1, 0, 1, 0.5),  # Magenta (Top)
    (0, 1, 1, 0.5)   # Cyan (Bottom)
)


def draw_text(x, y, text_string, font, color=(255, 255, 255)):
    text_surface = font.render(text_string, True, color)
    # text_surface = pygame.transform.flip(text_surface, False, True)
    text_data = pygame.image.tostring(text_surface, "RGBA", True)
    width, height = text_surface.get_size()

    glEnable(GL_TEXTURE_2D)
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, text_data)

    glColor4f(1, 1, 1, 1)
    glBegin(GL_QUADS)
    glTexCoord2f(0, 1); glVertex2f(x, y)
    glTexCoord2f(1, 1); glVertex2f(x + width, y)
    glTexCoord2f(1, 0); glVertex2f(x + width, y + height)
    glTexCoord2f(0, 0); glVertex2f(x, y + height)
    glEnd()

    glDeleteTextures([tex_id])
    glDisable(GL_TEXTURE_2D)

def draw_cube():
    """Draw the cube using OpenGL with colored faces and black edges"""
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    
    # Draw filled faces
    glBegin(GL_QUADS)
    for i, face in enumerate(faces):
        glColor4fv(colors[i])  # Set color for this face
        for vertex in face:
            glVertex3fv(vertices[vertex])
    glEnd()
    
    # Draw edges in black with thicker lines
    glLineWidth(2.0)
    glColor4f(0, 0, 0, 1.0)  # Black color for edges
    glBegin(GL_LINES)
    for edge in edges:
        for vertex in edge:
            glVertex3fv(vertices[vertex])
    glEnd()
    glLineWidth(1.0)  # Reset line width


class CubeVisualizer:
    def __init__(self, viewport_rect, label="", value=""):
        self.viewport_rect = viewport_rect
        self.label = label
        self.value = value
        self.roll = 0
        self.pitch = 0
        self.yaw = 0

    def update_orientation(self, roll, pitch, yaw):
        self.roll = roll
        self.pitch = pitch
        self.yaw = yaw

    def update_text(self, label, value):
        self.label = label
        self.value = value

    def draw(self, font):
        x, y, w, h = self.viewport_rect
        glViewport(x, y, w, h)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, (w / h), 0.1, 50.0)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glTranslatef(0, 0, -10)

        glRotatef(self.roll, 1, 0, 0)
        glRotatef(self.pitch, 0, 1, 0)
        glRotatef(self.yaw, 0, 0, 1)

        draw_cube()

        # --- Draw text labels in orthographic mode ---
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, w, h, 0, -1, 1)

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        # Draw label and value
        draw_text(10, 30, self.label, font, color=(255, 255, 255))
        draw_text(10, 60, self.value, font, color=(180, 255, 180))

        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

def calculate_iqr(df, index, column='roll', window=100):
    start_idx = max(0, index - window)
    window_data = df[column].iloc[start_idx:index + 1]
    return window_data.quantile(0.75) - window_data.quantile(0.25)


def main():
    df_high = pd.read_csv("./high_speed.csv")
    df_low = pd.read_csv("./low_speed.csv")
    df_medium = pd.read_csv("./med_speed.csv")
    
    
    pygame.init()
    display_width, display_height = 1200, 800
    pygame.display.set_mode((display_width, display_height), DOUBLEBUF | OPENGL)
    # gluPerspective(45, (display_width / display_height), 0.1, 50.0)
    glTranslatef(0.0, 0.0, -10)
    font = pygame.font.SysFont("Arial", 24)
    
    cube1 = CubeVisualizer((0, 0, 400, 600), label ="Low Speed", value =  "0"  )     # Left third
    cube2 = CubeVisualizer((400, 0, 400, 600), label ="Medium Speed", value = "0")   # Middle third
    cube3 = CubeVisualizer((800, 0, 400, 600), label ="High Speed", value = "0")   # Right third
    
    common_yaw = 0
    common_roll = 0
    common_pitch = 0
    for index, row in df_high.iterrows():
        if index < 100:
            continue
        if index >= len(df_low) or index >= len(df_medium):
            break
        roll_high =  common_roll  #row['roll']
        pitch_high = common_pitch # row['pitch']
        yaw_high = row['roll']
        
        
        roll_low = common_roll # df_low.iloc[index]['roll'] + 90
        pitch_low = common_pitch # df_low.iloc[index]['pitch'] + 90
        yaw_low = df_low.iloc[index]['roll']
        
        roll_medium = common_roll # df_medium.iloc[index]['roll'] + 90
        pitch_medium = common_pitch # df_medium.iloc[index]['pitch'] + 90
        yaw_medium = df_medium.iloc[index]['roll']
        
        
        iqr_high = calculate_iqr(df_high, index, 'roll')
        iqr_low = calculate_iqr(df_low, index, 'roll')
        iqr_medium = calculate_iqr(df_medium, index, 'roll')
        

        cube1.update_orientation(roll_low, pitch_low, yaw_low)
        cube2.update_orientation(roll_medium, pitch_medium, yaw_medium)
        cube3.update_orientation(roll_high, pitch_high, yaw_high)
        
        cube1.update_text("Low Speed", f"Angle of Deviation: {iqr_low:.2f}")
        cube2.update_text("Medium Speed", f"Angle of Deviation: {iqr_medium:.2f}")
        cube3.update_text("High Speed", f"Angle of Deviation: {iqr_high:.2f}")

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        cube1.draw(font)
        cube2.draw(font)
        cube3.draw(font)

        pygame.display.flip()
        pygame.time.wait(10)
    
if __name__ == "__main__":
    main()