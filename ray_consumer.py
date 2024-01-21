import asyncio
from aiokafka import AIOKafkaConsumer
import logging
import requests
import ray

# Configure logging
log_file = 'kafka_consumer.log'
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s', filename=log_file, filemode='a')
logging.getLogger('aiokafka').setLevel(logging.WARNING)

ray.init()

@ray.remote
class RayConsumer:
    def __init__(self, topic, inference_engine_url):
        self.inference_engine_url = inference_engine_url
        self.topic = topic
        self.healthy = True

    async def consume(self):
        loop = asyncio.get_running_loop()

        self.consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers='localhost:29092',
            group_id="ray-group",
            loop=loop)
        
        try:
            await self.consumer.start()
            logging.info("Successfully connected to Kafka server")

            async for msg in self.consumer:
                logging.info(f"Consumed: {msg.topic}, {msg.partition}, {msg.offset}, {msg.key}, {msg.value}, {msg.timestamp}")
                payload = {"img_path": msg.value.decode('utf-8'), "camera_id": msg.topic}
                response = requests.post(self.inference_engine_url, json=payload)
                logging.debug(f"Model output: {response.json()}")

        except Exception as e:
            logging.error(f"Error in message consumption: {e}")
            self.healthy = False
        finally:
            await self.consumer.stop()
            self.healthy = False
            logging.info("Kafka Consumer stopped")


async def run_consumer(topic, url):
    consumer = RayConsumer.remote(topic, url)
    await consumer.consume.remote()

async def main():
    topics = ["camera_1"]  # Add more topics as needed
    inference_engine_url = "http://localhost:8000/inference"
    tasks = [run_consumer(topic, inference_engine_url) for topic in topics]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())

