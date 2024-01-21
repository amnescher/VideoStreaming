import asyncio
from aiokafka import AIOKafkaConsumer
import logging
import requests 
# Configure logging to write to a file
log_file = 'kafka_consumer.log'
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s:%(message)s',
                    filename=log_file,
                    filemode='a')
logging.getLogger('aiokafka').setLevel(logging.WARNING)
class RayConsumer:
    def __init__(self, topic, inference_engine):
        self.inference_engine = inference_engine
        self.loop = asyncio.get_event_loop()
        self.topic = topic

        self.consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers='localhost:29092',
            group_id="ray-group",
            loop=self.loop)
        self.healthy = True

    async def consume(self):
        try:
            await self.consumer.start()
            logging.info("Successfully connected to Kafka server")
        except Exception as e:
            logging.error(f"Failed to connect to Kafka server: {e}")
            self.healthy = False
            return

        try:
            async for msg in self.consumer:
                # Change this to DEBUG or INFO as per your preference
                logging.info(f"Consumed: {msg.topic}, {msg.partition}, {msg.offset}, {msg.key}, {msg.value}, {msg.timestamp}")
                result = self.inference_engine(msg.value,self.topic)
                logging.debug(f"Model output: {result}")
        except Exception as e:
            logging.error(f"Error in message consumption: {e}")
            self.healthy = False
        finally:
            await self.consumer.stop()
            self.healthy = False
            logging.info("Kafka Consumer stopped")

def request_engine(image_path, camera_id):
    url = "http://localhost:8000/inference"
    payload = {"img_path": image_path, "camera_id": camera_id}
    response = requests.post(url, json=payload)
    return response.json()
    

async def main():
    topic = "camera_1"
    consumer = RayConsumer(topic, request_engine)
    await consumer.consume()

if __name__ == "__main__":
    asyncio.run(main())