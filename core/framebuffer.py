from queue import Queue, Full, Empty
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import Logger, set_global_log_level_by_name

logger = Logger(__name__)
set_global_log_level_by_name("INFO")

class FrameBuffer:
    def __init__(self):
        self.raw_queue = Queue(maxsize=10)
        self.processed_queue = Queue(maxsize=10)

        self.raw_frame = None
        self.processed_frame = None

        self.raw_drop_ctr = 0
        self.processed_drop_ctr = 0

        self.raw_consec_ctr = 0
        self.processed_consec_ctr = 0

        self.total_raw_frames = 0
        self.total_processed_frames = 0

    def put_raw_frame(self, raw_frame):
        self.total_raw_frames += 1
        try:
            self.raw_queue.put_nowait(raw_frame)           
            
        except Full:
            logger.warning(f"Forced to drop raw frame after {self.raw_consec_ctr} consecutive frames. Total dropped: {self.raw_drop_ctr}. Total frames: {self.total_raw_frames}, Dropped percentage: {self.raw_drop_ctr / self.total_raw_frames * 100}%")
            self.raw_drop_ctr += 1
            self.raw_consec_ctr = 0
            
        else:
            self.raw_consec_ctr += 1

    def put_processed_frame(self, processed_frame):
        self.total_processed_frames += 1
        try:
            self.processed_queue.put_nowait(processed_frame)            
            
        except Full:
            logger.warning(f"Forced to drop processed frame after {self.processed_consec_ctr} consecutive frames. Total dropped: {self.processed_drop_ctr}. Total frames: {self.total_processed_frames}, Dropped percentage: {self.processed_drop_ctr / self.total_processed_frames * 100}%")
            self.processed_drop_ctr += 1
            self.processed_consec_ctr = 0
        else:
            self.processed_consec_ctr += 1

    def get_raw_frame(self):
        return self.raw_queue.get()

    def get_processed_frame(self):
        return self.processed_queue.get()

    def get_raw_drop_ctr(self):
        return self.raw_drop_ctr

    def get_processed_drop_ctr(self):
        return self.processed_drop_ctr
        
        
