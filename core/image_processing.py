import numpy as np
import dearpygui.dearpygui as dpg
from skimage.draw import line

class ROILine:
    def __init__(self, start_point, end_point, color, image=None):
        self.start_point = start_point
        self.end_point = end_point
        self.color = color
        self.line_id = dpg.draw_line([start_point[0], start_point[1]], [end_point[0], end_point[1]], color=color)
        self._image = None

    def set_position(self, start_point, end_point):
        self.start_point = start_point
        self.end_point = end_point
        dpg.set_value(self.line_id, [start_point[0], start_point[1], end_point[0], end_point[1]])

    def get_position(self):
        return self.start_point, self.end_point
    
    def set_image(self, image):
       
        self._image = image
    
    def get_image(self):
        return self._image

    def get_roi_values(self):
       
        rr, cc = line(self.start_point[1], self.start_point[0], self.end_point[1], self.end_point[0])
        rr = np.clip(rr, 0, self._image.shape[0]-1)
        cc = np.clip(cc, 0, self._image.shape[1]-1)
        pixels = self._image[rr, cc]
        return np.array(pixels)


