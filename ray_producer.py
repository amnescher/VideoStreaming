from aiokafka import AIOKafkaProducer
import asyncio
import cv2
import os
import time

video_file_path = 'video.mp4'  # Provide the path to your video file here

# Kafka configuration
kafka_topic = 'camera_1'
kafka_server = 'localhost:29092'

# Directory to save frames
frame_dir = 'camera1'
os.makedirs(frame_dir, exist_ok=True)

# Frame rate settings
fps = 1  # Number of frames to save per second

async def capture_and_send_frames():
    producer = AIOKafkaProducer(bootstrap_servers=kafka_server)
    await producer.start()
    try:
        cap = cv2.VideoCapture(video_file_path)
        video_fps = cap.get(cv2.CAP_PROP_FPS)  # Frame rate of the video
        frame_interval = int(video_fps / fps)  # Interval of frames to capture

        frame_count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Capture frames according to the specified fps
            if frame_count % frame_interval == 0:
                timestamp = time.time()
                frame_name = f"frame_{timestamp}.jpg"
                frame_path = os.path.join(frame_dir, frame_name)

                # Save the frame
                cv2.imwrite(frame_path, frame)

                # Send message to Kafka
                message = f"{frame_dir}/{frame_name}"
                await producer.send_and_wait(kafka_topic, message.encode())

            frame_count += 1

    finally:
        await producer.stop()
        cap.release()

asyncio.run(capture_and_send_frames())
