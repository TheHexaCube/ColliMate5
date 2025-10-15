import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pypylon import pylon
import threading
import numpy as np
from utils.logger import Logger, set_global_log_level_by_name
import cv2
import time

logger = Logger(__name__)
set_global_log_level_by_name("INFO")

''' CamManager class 
    This class is used to manage/connect to Basler Cameras
''' 
class CamManager:
    def __init__(self):
        self.tl_factory = pylon.TlFactory.GetInstance()
        self.devices = self.tl_factory.EnumerateDevices()
        self.current_cam = None
        self._capture_thread = None
        self._stop_event = threading.Event()
        self._frame_count = 0

        self._raw_frame = None
        self._processed_frame = None

        self._width = None
        self._height = None

        self._frame_lock = threading.Lock()  # Thread safety for frame access
        self._is_new_frame = False
        self._frame_ready_event = threading.Event()
       

    def list_cameras(self):
        # return a list of available cameras (index, model_name, serial_no)
        self.devices = self.tl_factory.EnumerateDevices()
        
        return [(index, device.GetModelName(), device.GetSerialNumber()) for index, device in enumerate(self.devices)]

    def connect(self, index: int):
        if self.list_cameras() is None:            
            raise ValueError("No cameras found")
        if index < 0 or index >= len(self.devices):            
            raise ValueError(f"Invalid camera index: {index}")


        if self.current_cam and self.current_cam.IsOpen():
            self.current_cam.Close()

        self.current_cam = pylon.InstantCamera(self.tl_factory.CreateDevice(self.devices[index]))
        self.current_cam.Open()
        logger.info(f"Connected to camera: {self.current_cam.GetDeviceInfo().GetModelName()}")  
        

    def disconnect(self):
        '''
        Disconnect from the camera
        '''
        # Stop capture first if it's running
        if self.is_capturing():
            self.stop_capture()
        
        # Clear all callbacks
        #self.clear_all_callbacks()
        
        # Close camera
        if self.current_cam and self.current_cam.IsOpen():
            self.current_cam.Close()
        self.current_cam = None
        logger.info("Disconnected from camera")

    def start_capture(self):
        if not self.current_cam or not self.current_cam.IsOpen():
            raise RuntimeError("Camera is not connected")
        if self.current_cam.IsGrabbing():
            raise RuntimeError("Camera is already capturing")

        self.set_exposure_time(100)
        self.set_gain(0)
        self.current_cam.PixelFormat.Value = "BayerRG12"
       
        self.current_cam.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        logger.info(f"Grab started successfully. Camera grabbing: {self.current_cam.IsGrabbing()}")
        
        self._stop_event.clear()
        self._frame_count = 0
        self._capture_thread = threading.Thread(target=self._callback_thread)
        self._capture_thread.start()
        logger.info("Started capturing")

    def stop_capture(self):
        '''
        Stop capturing
        '''
        if self._capture_thread and self._capture_thread.is_alive():
            self._stop_event.set()
            self._frame_ready_event.set()  # Wake up any waiting threads
            self._capture_thread.join()
            self._capture_thread = None
            logger.info("Stopped capturing")

    def _callback_thread(self):
        '''
        Thread to handle the callback from the camera
        '''
      
        while not self._stop_event.is_set():

            grabResult = self.current_cam.RetrieveResult(5000)
            if grabResult.GrabSucceeded():
                
                # Thread-safe frame processing
                with self._frame_lock:
                    self._raw_frame = grabResult.GetArray()
                    self._raw_frame = cv2.cvtColor(self._raw_frame, cv2.COLOR_BAYER_RG2RGB)
                    # flip rows with columns
                    

                    self._processed_frame = self._raw_frame.astype('float32') 
                    # normalize from 12bit to float 0-1
                    self._processed_frame = self._processed_frame / 4095.0
                    self._processed_frame = self._processed_frame.flatten()
                    self._is_new_frame = True
                    
                
                # Signal that a new frame is ready
                time.sleep(0.25)
                self._frame_ready_event.set()

                self._frame_count += 1                
            else:
                logger.error("Error: Could not grab image")
                break
            
            grabResult.Release()
 
       

    # ---- camera settings ----

    def set_exposure_time(self, exposure_time: int):
        '''
        Set the exposure time of the camera
        '''
        self.current_cam.ExposureTime.SetValue(exposure_time)
        logger.info(f"Exposure time set to {exposure_time}")
        
    def get_exposure_time(self):
        '''
        Get the exposure time of the camera
        '''
        return self.current_cam.ExposureTime.GetValue()

    def set_gain(self, gain: int):
        '''
        Set the gain of the camera
        '''
        self.current_cam.Gain.SetValue(gain)
        logger.info(f"Gain set to {gain}")
        
    def get_gain(self):
        '''
        Get the gain of the camera
        '''
        return self.current_cam.Gain.GetValue()
        
    # ---- camera/state info ---- 
    def is_connected(self):
        '''
        Check if the camera is connected
        '''
        return self.current_cam is not None and self.current_cam.IsOpen()
    
    def is_capturing(self):
        '''
        Check if the camera is capturing
        '''
        return self._capture_thread is not None and self._capture_thread.is_alive()
    
    def get_raw_frame(self):
        '''
        Get the raw frame from the camera (thread-safe)
        '''
        with self._frame_lock:            
                if self._raw_frame is not None:
                    self._is_new_frame = False
                    return self._raw_frame.copy()
                else:
                    return None
        
    def get_processed_frame(self):
        '''
        Get the processed frame from the camera (thread-safe)
        '''
        with self._frame_lock:            
            if self._processed_frame is not None:
                self._is_new_frame = False
                self._frame_ready_event.clear()  # Reset for next frame
                return self._processed_frame.copy()
            else:
                return None
  
    
    def get_resolution(self):
        '''
        Get the resolution of the camera
        '''
        if self.current_cam.IsOpen():
            self._width = self.current_cam.Width.GetValue()
            self._height = self.current_cam.Height.GetValue()
            return self._width, self._height
        else:
            raise RuntimeError("Camera is not connected")
        
    
    def __del__(self):
        self.disconnect()
