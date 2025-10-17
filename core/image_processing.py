import numpy as np
import dearpygui.dearpygui as dpg
from skimage.draw import line
from utils.logger import Logger, set_global_log_level_by_name
import threading
import time
import cv2
from line_profiler import profile

logger = Logger(__name__)
set_global_log_level_by_name("INFO")

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


class ImageProcessor:
    def __init__(self, frame_buffer):
        self.frame_buffer = frame_buffer

        self.thread = threading.Thread(target=self.process_frame)
        self.stop_event = threading.Event()

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join()

    @profile
    def process_frame(self):
        while not self.stop_event.is_set():
            raw_frame = self.frame_buffer.get_raw_frame()
            if raw_frame is not None:
                #logger.info("Processing raw frame")
                
                rgb_frame = cv2.cvtColor(raw_frame, cv2.COLOR_BayerRG2RGB)
                rgb_frame = cv2.normalize(rgb_frame, None, 0.0, 1.0, cv2.NORM_MINMAX, dtype=cv2.CV_32F)
                #rgb_frame = rgb_frame.astype(np.float32) * (1/4096.0) # 28.8ms

                self.frame_buffer.put_processed_frame(rgb_frame)
                #print(f"Processed frame: {rgb_frame.shape}")
            else:
                time.sleep(0.1)
        


