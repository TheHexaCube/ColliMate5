import numpy as np
import dearpygui.dearpygui as dpg
from skimage.draw import line
from utils.logger import Logger, set_global_log_level_by_name
from core.processing_workers import process_frame
import threading
import time
import cv2
from line_profiler import profile
import multiprocessing
from queue import Full

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
    def __init__(self, frame_buffer, num_workers=4):
        self.num_workers = num_workers

        self.frame_buffer = frame_buffer

        self.processed_frame_buffer = frame_buffer.raw_queue
        self.raw_frame_buffer = frame_buffer.processed_queue
       
        self.raw_frame_ctr = frame_buffer.raw_frame_ctr
        self.processed_frame_ctr = frame_buffer.processed_frame_ctr


        self.worker_processes = []
        self.stop_event = multiprocessing.Event()


    def start(self):
        for i in range(self.num_workers):
            worker = multiprocessing.Process(target=process_frame, args=(self.processed_frame_buffer, self.raw_frame_buffer, self.processed_frame_ctr, self.stop_event))
            worker.start()
            self.worker_processes.append(worker)
            logger.info(f"Started worker process {i}")

        

    def stop(self):
        for worker in self.worker_processes:
            worker.terminate()
            worker.join()
        logger.info("Stopped worker processes")



