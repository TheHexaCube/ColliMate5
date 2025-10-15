

import os
import sys  
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dearpygui.dearpygui as dpg

from core.cam_manager import CamManager
from core.image_processing import ROILine
import time
from utils.logger import Logger, set_global_log_level_by_name
import numpy as np
import threading

logger = Logger(__name__)


class MainWindow:
    def __init__(self):
        dpg.create_context()
        dpg.create_viewport(title='Video Test', width=1280, height=720)
        dpg.setup_dearpygui()

        self.cam = CamManager()
        
        dpg.set_viewport_vsync(False)

        # Store cameras and create list of labels for the combo
        self.cameras = self.cam.list_cameras()
        # We'll use either serial, model or index as label - here use index for clarity
        self.camera_labels = [f"{i}: {model} ({serial})" for i, model, serial in self.cameras]

        # Display configuration
        self.video_width = 2048     
        self.video_height = 1536
        self.frame_buffer = np.zeros((self.video_height, self.video_width, 3), dtype=np.float32)
        print(f"Frame info: ndim={self.frame_buffer.ndim}, shape={self.frame_buffer.shape}, dtype={self.frame_buffer.dtype}, size={self.frame_buffer.size}")
        
        # Threading for texture updates
        self._texture_update_thread = None
        self._stop_texture_update = threading.Event()
        self._texture_lock = threading.Lock()
        
        with dpg.texture_registry(show=True):
            # Use raw texture for highest performance
            self.texture = dpg.add_raw_texture(tag='texture',
                width=self.video_width, 
                height=self.video_height, 
                default_value=self.frame_buffer, 
                format=dpg.mvFormat_Float_rgb
            )

        with dpg.window(label="Main Window", tag="MainWindow"):

            # Provide the list of labels, and pass nothing for user_data (if needed, use user_data)
            dpg.add_combo(items=self.camera_labels, callback=self.camera_combo_callback)
            dpg.add_button(label="Start Capture", callback=self.cam.start_capture)
            dpg.add_button(label="Stop Capture", callback=self.cam.stop_capture)
            # generate placeholder image
            #dpg.add_image(self.texture, height=750, width=1000)
            with dpg.plot(label="Frame Rate", height=500, width=500, equal_aspects=True):
                dpg.add_plot_axis(dpg.mvXAxis, label="x")
                dpg.add_plot_axis(dpg.mvYAxis, label="y", tag="y_axis")
                

                dpg.add_image_series('texture', bounds_min=(0, 0), bounds_max=(self.video_width, self.video_height), parent='y_axis', tag='image_series')
                #line_id = dpg.draw_line([0, 0], [self.video_width, self.video_height], color=[255, 0, 0])
                self.roi_line = ROILine((0, 0), (self.video_width, self.video_height), (255, 0, 0))

            with dpg.plot(label="ROI Line", height=500, width=500, equal_aspects=True):
                dpg.add_plot_axis(dpg.mvXAxis, label="x2")
                dpg.add_plot_axis(dpg.mvYAxis, label="y2", tag="y_axis2")

                # plot should be float lists
                dummy_x = np.arange(0, self.video_width).astype(float)
                dummy_y = np.zeros(self.video_width).astype(float)
                

                dpg.add_line_series(x=dummy_x, y=dummy_y, tag='line_series', parent='y_axis2')
                
               # self.ROI_data = dpg.add_line_series(x=np.arange(0, self.video_width), y=np.zeros(self.video_width), tag='line_series', parent='y_axis2')
                

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
        """
        Worker thread for updating texture in the background
        """
        
        while not self._stop_texture_update.is_set():
            # Wait for camera to signal new frame (with timeout to allow checking stop event)
            if self.cam._frame_ready_event.wait(timeout=0.1):
                processed_frame = self.cam.get_processed_frame()
                if processed_frame is not None:
                    # Make a thread-safe copy and update texture
                    with self._texture_lock:                        
                        self.frame_buffer = np.copy(processed_frame)
                        # get width and height of frame, check if they are the same as _video_width and _video_height and if not, update the texture size
                        width, height = self.cam.get_resolution()
                        if width != self.video_width or height != self.video_height:
                            self.video_width = width
                            self.video_height = height

                            dpg.configure_item(self.texture, width=self.video_width, height=self.video_height)
                            dpg.configure_item('image_series', bounds_min=(0, 0), bounds_max=(self.video_width, self.video_height))

                        
                        #if self.roi_line is not None:
                            #self.roi_line.set_image(self.cam.get_raw_frame())

                            #print(f"Line start/end: {self.roi_line.get_position()}")
                            #print(f"Raw Img Dimensions: {self.cam.get_raw_frame().shape}")

                            #data = self.roi_line.get_roi_values()
                            # convert data to float
                            #dpg.set_value('line_series', [np.arange(0, self.video_width).astype(float), data.astype(float)])
                            # set the roi_line values to plot

                        
                        
                        dpg.set_value(self.texture, self.frame_buffer)

                        # get the position of the roi line
            
                    
                

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
            
            # Stop capture and disconnect camera
            if self.cam.is_capturing():
                self.cam.stop_capture()
            self.cam.disconnect()
            logger.info("Cleaned up camera resources")
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


    