import asyncio
from aiokafka import AIOKafkaConsumer
import logging

# Configure logging to write to a file
log_file = 'kafka_consumer.log'
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s:%(message)s',
                    filename=log_file,
                    filemode='a')
logging.getLogger('aiokafka').setLevel(logging.WARNING)
class RayConsumer:
    def __init__(self, topic, model):
        self.model = model
        self.loop = asyncio.get_event_loop()

        self.consumer = AIOKafkaConsumer(
            topic,
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
                result = self.model(msg.value)
                logging.debug(f"Model output: {result}")
        except Exception as e:
            logging.error(f"Error in message consumption: {e}")
            self.healthy = False
        finally:
            await self.consumer.stop()
            self.healthy = False
            logging.info("Kafka Consumer stopped")

def toy_model(text):
    return "predicted: " + text.decode("utf-8")

async def main():
    topic = "camera_1"
    consumer = RayConsumer(topic, toy_model)
    await consumer.consume()

if __name__ == "__main__":
    asyncio.run(main())
