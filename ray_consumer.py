import asyncio
import ray
from ray import serve
from aiokafka import AIOKafkaConsumer
import logging

# Configure logging to write to a file
log_file = 'kafka_consumer_ray_serve.log'
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s:%(message)s',
                    filename=log_file,
                    filemode='a')
logging.getLogger('aiokafka').setLevel(logging.WARNING)

@serve.deployment(num_replicas=1,
                  ray_actor_options={"num_cpus": 0.1, "num_gpus": 0},
                  health_check_period_s=1,
                  health_check_timeout_s=1)
class RayConsumer:
    def __init__(self, topic, model):
        self.model = model
        self.loop = asyncio.get_event_loop()  # Ray Serve manages the event loop

        self.consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers='localhost:29092',
            group_id="ray-group",
            loop=self.loop)
        self.healthy = True

        # Start the consume task
        self.loop.create_task(self.consume())

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

    async def check_health(self):
        if not self.healthy:
            raise RuntimeError("Kafka Consumer is broken")

def toy_model(text):
    return "predicted: " + text.decode("utf-8")

# Initialize Ray and Ray Serve
ray.init()
serve.start()

# Deploy the Ray Consumer
topic = "camera_1"
deployment = RayConsumer.bind(topic, toy_model)
serve.run(deployment, name="ray_kafka_consumer")
