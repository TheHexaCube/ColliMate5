from core.cam_manager import CamManager
from utils.logger import Logger, set_global_log_level_by_name
import time

set_global_log_level_by_name("INFO")


logger = Logger(__name__)

cam = CamManager()
print(cam.list_cameras())

cam.connect(0)
cam.start_capture()

time.sleep(2)
cam.stop_capture()