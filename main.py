from testing.video_test import MainWindow
from core.framebuffer import FrameBuffer
from core.image_processing import ImageProcessor
from multiprocessing import Process, Event
from core.processing_workers import process_frame
import multiprocessing

def main():
    frame_buffer = FrameBuffer()
    image_processor = ImageProcessor(frame_buffer)
    image_processor.start()

    main_window = MainWindow()
    main_window.run()

    image_processor.stop()






if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()