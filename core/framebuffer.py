from queue import Full, Empty
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import Logger, set_global_log_level_by_name

import multiprocessing
import heapq

logger = Logger(__name__)
set_global_log_level_by_name("INFO")

class FrameBuffer:
    def __init__(self):
        self.raw_queue = multiprocessing.Queue(maxsize=10)
        self.processed_queue = multiprocessing.Queue(maxsize=10)

        self.reordered_queue = []

        self.raw_frame_ctr = multiprocessing.Value('i', 0)
        self.processed_frame_ctr = multiprocessing.Value('i', 0)

  

    
    def put_processed_frame(self, processed_frame):
        try:
            self.processed_queue.put_nowait((self.processed_frame_ctr.value, processed_frame))
        except Full:
            logger.warning(f"Processed queue is full")
        else:
            self.processed_frame_ctr.value += 1

    def put_raw_frame(self, raw_frame):
        try:
            self.raw_queue.put_nowait((self.raw_frame_ctr.value, raw_frame))
        except Full:
            logger.warning(f"Raw queue is full")
        else:
            self.raw_frame_ctr.value += 1

    def get_raw_frame(self):
        return self.raw_queue.get()

    def get_processed_frame(self):
        self._drain_to_heap()
        if self.reordered_queue and self.reordered_queue[0][0] == self.next_expected_seq.value:
            idx, frame = heapq.heappop(self.reordered_queue)
            self.next_expected_seq.value += 1
            return frame
        else:
            return None

    def _drain_to_heap(self):
        while True:
            try:
                item = self.processed_queue.get_nowait()
            except Empty:
                break
            heapq.heappush(self.reordered_queue, item)

    def get_raw_drop_ctr(self):
        return self.raw_drop_ctr

    def get_processed_drop_ctr(self):
        return self.processed_drop_ctr

    def is_data_available(self):
        return not self.processed_queue.empty()
        
        
