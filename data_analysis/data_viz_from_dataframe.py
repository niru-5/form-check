import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import pandas as pd
import argparse

# Define vertices and edges for the cube
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

edges = (
    (0, 1), (0, 3), (0, 4),
    (2, 1), (2, 3), (2, 7),
    (6, 3), (6, 4), (6, 7),
    (5, 1), (5, 4), (5, 7)
)

def Cube():
    glBegin(GL_LINES)
    for edge in edges:
        for vertex in edge:
            glVertex3fv(vertices[vertex])
    glEnd()

def displayCube(dataframe):
    pygame.init()
    display = (800, 600)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    gluPerspective(45, (display[0] / display[1]), 0.1, 50.0)
    glTranslatef(0.0, 0.0, -10)

    curr_roll = 0
    curr_pitch = 90
    curr_yaw = 0
    glRotatef(0 - curr_pitch, 0, 1, 0)
    glRotatef(0 - curr_yaw, 0, 0, 1)

    for index, row in dataframe.iterrows():
        roll = row['roll']
        pitch = row['pitch']
        yaw = row.get('yaw', curr_yaw)  # Use current yaw if not in DataFrame

        glRotatef(roll - curr_roll, 1, 0, 0)
        curr_roll = roll


        # glRotatef(pitch - curr_pitch, 0, 1, 0)
        # curr_pitch = pitch

        # glRotatef(yaw - curr_yaw, 0, 0, 1)
        # curr_yaw = yaw

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        Cube()
        pygame.display.flip()
        pygame.time.wait(10)

    pygame.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Display a rotating cube using roll and pitch from a CSV file.')
    parser.add_argument('csv_file', type=str, help='Path to the CSV file containing roll and pitch data.')
    args = parser.parse_args()

    # Read the CSV file into a DataFrame
    df = pd.read_csv(args.csv_file)

    # Call the displayCube function with the DataFrame
    displayCube(df) 