from aiokafka import AIOKafkaProducer
import asyncio
import cv2
import os
import time
import ray

ray.init()

@ray.remote
class VideoProcessor:
    def __init__(self, video_file_path, frame_dir, kafka_topic, kafka_server):
        self.video_file_path = video_file_path
        self.frame_dir = frame_dir
        self.kafka_topic = kafka_topic
        self.kafka_server = kafka_server

    async def capture_and_send_frames(self):
        producer = AIOKafkaProducer(bootstrap_servers=self.kafka_server)
        await producer.start()
        try:
            cap = cv2.VideoCapture(self.video_file_path)
            video_fps = cap.get(cv2.CAP_PROP_FPS)
            frame_interval = int(video_fps / fps)

            frame_count = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_count % frame_interval == 0:
                    timestamp = time.time()
                    frame_name = f"frame_{timestamp}.jpg"
                    frame_path = os.path.join(self.frame_dir, frame_name)

                    cv2.imwrite(frame_path, frame)

                    message = f"{self.frame_dir}/{frame_name}"
                    await producer.send_and_wait(self.kafka_topic, message.encode())

                frame_count += 1
        finally:
            await producer.stop()
            cap.release()

# Example usage
video_files = [
    {'path': 'video1.mp4', 'dir': 'frames/camera1', 'topic': 'camera_1'},
     {'path': 'video2.mp4', 'dir': 'frames/camera2', 'topic': 'camera_2'},
    # Add more videos here
]

# Frame rate settings
fps = 1
kafka_server = 'localhost:29092'

async def run_ray_task(task):
    # Wrapper function for Ray tasks
    return ray.get(task)

async def main():
    tasks = []
    for video in video_files:
        os.makedirs(video['dir'], exist_ok=True)
        processor = VideoProcessor.remote(video['path'], video['dir'], video['topic'], kafka_server)
        task = run_ray_task(processor.capture_and_send_frames.remote())
        tasks.append(task)

    await asyncio.gather(*tasks)

# Running the main coroutine
asyncio.run(main())

