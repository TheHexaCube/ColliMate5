

import os
import sys  
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dearpygui.dearpygui as dpg
import cupy

from core.cam_manager import CamManager
from core.image_processing import ROILine
import time
from utils.logger import Logger, set_global_log_level_by_name
import numpy as np
import threading
from queue import Queue
from core.framebuffer import FrameBuffer
from core.image_processing import ImageProcessor

logger = Logger(__name__)




class MainWindow:
    def __init__(self):
        dpg.create_context()
        dpg.create_viewport(title='Video Test', width=900, height=720)
        dpg.setup_dearpygui()

        
        
        self.cam = CamManager(self.frame_buffer)
      


        dpg.set_viewport_vsync(False)

        # Store cameras and create list of labels for the combo
        self.cameras = self.cam.list_cameras()
        # We'll use either serial, model or index as label - here use index for clarity
        self.camera_labels = [f"{i}: {model} ({serial})" for i, model, serial in self.cameras]

        # Display configuration
        self.video_width = 2048     
        self.video_height = 1536
        self.texture_data = np.zeros((self.video_height, self.video_width, 3), dtype=np.float32)
        print(f"Frame info: ndim={self.texture_data.ndim}, shape={self.texture_data.shape}, dtype={self.texture_data.dtype}, size={self.texture_data.size}")
        
        # Threading for texture updates
        self._texture_update_thread = None
        self._stop_texture_update = threading.Event()
        self._texture_lock = threading.Lock()
        
        with dpg.texture_registry():
            # Use raw texture for highest performance
            self.texture = dpg.add_raw_texture(tag='texture',
                width=self.video_width, 
                height=self.video_height, 
                default_value=self.texture_data, 
                format=dpg.mvFormat_Float_rgb
            )

        with dpg.window(label="Video Window", tag="MainWindow"):

            # Provide the list of labels, and pass nothing for user_data (if needed, use user_data)
            dpg.add_combo(items=self.camera_labels, callback=self.camera_combo_callback)
            self.start_capture_button = dpg.add_button(label="Start Capture", callback=self.start_button_callback)
            self.stop_capture_button = dpg.add_button(label="Stop Capture", callback=self.start_button_callback)
            # generate placeholder image
            #dpg.add_image(self.texture, height=750, width=1000)
            with dpg.plot(label="Frame Rate", height=500, width=750, equal_aspects=True):
                dpg.add_plot_axis(dpg.mvXAxis, label="x")
                dpg.add_plot_axis(dpg.mvYAxis, label="y", tag="y_axis")
                

                dpg.add_image_series('texture', bounds_min=(0, 0), bounds_max=(self.video_width, self.video_height), parent='y_axis', tag='image_series')
                #line_id = dpg.draw_line([0, 0], [self.video_width, self.video_height], color=[255, 0, 0])
                self.roi_line = ROILine((50, 0), (50, self.video_height), (255, 0, 0))


        dpg.set_primary_window("MainWindow", True)

        with dpg.handler_registry():
            dpg.add_key_press_handler(callback=self.key_press_callback)

    def key_press_callback(self, sender, app_data):
        if (dpg.is_key_down(dpg.mvKey_LControl) and dpg.is_key_down(dpg.mvKey_P)):
            dpg.show_metrics()

    def drag_line_callback(self, sender, app_data):
        print(f"Drag line callback: {sender} - {app_data}")

    def camera_combo_callback(self, sender, app_data, user_data):
        # app_data is the string of the selected label; find its index
        try:
            selected_label = app_data
            selected_index = self.camera_labels.index(selected_label)
            
            # Stop current capture and disconnect if connected
            if self.cam.is_capturing():
                self.cam.stop_capture()
            if self.cam.is_connected():
                self.cam.disconnect()
            
            # Connect to new camera
            self.cam.connect(selected_index)
            logger.info(f"Connected to camera {selected_index}")
            
        except ValueError:
            logger.error("Could not retrieve camera index from combobox selection.")
        except Exception as e:
            logger.error(f"Error connecting to camera: {e}")

    def _texture_update_worker(self):      
        while not self._stop_texture_update.is_set():
            if self.frame_buffer.is_data_available():
                seq_num, processed_frame = self.frame_buffer.get_processed_frame()
                dpg.set_value(self.texture, processed_frame)
            else:
                time.sleep(0.1)
            
    def start_button_callback(self, sender, app_data):
        if sender == self.start_capture_button:
            self.cam.start_capture()
            
            logger.info("Started capture and image processing")
        elif sender == self.stop_capture_button:
            self.cam.stop_capture()
            self.image_processor.stop()
            logger.info("Stopped capture and image processing")
      
    def start_texture_update_thread(self):
        """
        Start the texture update daemon thread
        """
        if self._texture_update_thread is None or not self._texture_update_thread.is_alive():
            self._stop_texture_update.clear()
            self._texture_update_thread = threading.Thread(
                target=self._texture_update_worker, 
                daemon=True,
                name="TextureUpdateThread"
            )
            self._texture_update_thread.start()
            logger.info("Started texture update daemon thread")

    def stop_texture_update_thread(self):
        """
        Stop the texture update daemon thread
        """
        if self._texture_update_thread and self._texture_update_thread.is_alive():
            self._stop_texture_update.set()
            self._texture_update_thread.join(timeout=1.0)  # 1 second timeout
            logger.info("Stopped texture update daemon thread")

    def cleanup(self):
        """
        Cleanup resources when closing
        """
        try:
            # Stop texture update thread
            self.stop_texture_update_thread()
            # Stop image processing thread
            self.image_processor.stop()
            # Stop capture
            self.cam.stop_capture()
            # Disconnect camera
            self.cam.disconnect()
            # Destroy context
            dpg.destroy_context()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def run(self):
        dpg.show_viewport()
        
        # Start the texture update daemon thread
        self.start_texture_update_thread()
        
        while dpg.is_dearpygui_running():
            # Render the frame - texture updates are now handled in background thread
            dpg.render_dearpygui_frame()
            
        # Cleanup before destroying context
        self.cleanup()
        dpg.destroy_context()

if __name__ == "__main__":
    
    main_window = MainWindow()
    main_window.run()


    