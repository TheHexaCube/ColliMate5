import cv2, time
from queue import Full
from line_profiler import profile



@profile
def process_frame(processed_frame_buffer, raw_frame_buffer, processed_frame_ctr, stop_event):
    while not stop_event.is_set():
        raw_frame = raw_frame_buffer.get()
        if raw_frame is not None:
            #logger.info("Processing raw frame")
            
            rgb_frame = cv2.cvtColor(raw_frame, cv2.COLOR_BayerRG2RGB)
            rgb_frame = cv2.normalize(rgb_frame, None, 0.0, 1.0, cv2.NORM_MINMAX, dtype=cv2.CV_32F)
            #rgb_frame = rgb_frame.astype(np.float32) * (1/4096.0) # 28.8ms
            try: 
                print("Test")
                processed_frame_buffer.put_nowait((processed_frame_ctr.value, rgb_frame))
            except Full:
                #logger.warning(f"Processed frame buffer is full")
                pass
            else:
                processed_frame_ctr.value += 1
            #print(f"Processed frame: {rgb_frame.shape}")
        else:
            time.sleep(0.1)
    