import requests
from fastapi import FastAPI
from ray import serve
import logging
import torch
from torchvision import models, transforms
from PIL import Image
from typing import Optional, List
from pydantic import BaseModel
from ray.serve.handle import DeploymentHandle
import ray
import yaml
import asyncio
from aiokafka import AIOKafkaConsumer
import logging
import requests
import ray
# Define the Input class
class Config:
    def __init__(self, **entries):
        self.__dict__.update(entries)

with open("config.yaml", 'r') as file:
    config = yaml.safe_load(file)
    config = Config(**config)
class Input(BaseModel):
    img_path: str
    camera_id: Optional[str]



# Configure logging
log_file = 'kafka_consumer.log'
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s', filename=log_file, filemode='a')
logging.getLogger('aiokafka').setLevel(logging.WARNING)


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
    topics = ["camera_1", "camera_2"]  # Add more topics as needed
    inference_engine_url = "http://localhost:8000/inference"
    tasks = [run_consumer(topic, inference_engine_url) for topic in topics]
    await asyncio.gather(*tasks)


# Define a FastAPI app and wrap it in a deployment with a route handler.
app = FastAPI()

# Define the Inference class
@serve.deployment(autoscaling_config={
        "min_replicas": config.inference["min_replicas"],
        "initial_replicas": config.inference["initial_replicas"],
        "max_replicas": config.inference["max_replicas"],
        "target_num_ongoing_requests_per_replica": config.inference["target_num_ongoing_requests_per_replica"],
        "graceful_shutdown_timeout_s": config.inference["graceful_shutdown_timeout_s"]}, route_prefix="/")
@serve.ingress(app)
class Inference:
    def __init__(self, Classifier1: DeploymentHandle, Classifier2: DeploymentHandle,):
        self.fastapi_deployment =  Classifier1
        self.Classifier2 = Classifier2
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            filename="ray_cluster.log",  # specify the file name if you want logging to be stored in a file
            filemode="a",  # append to the log file if it exists
        )
        self.logger = logging.getLogger(__name__)
        self.logger.propagate = True
    # FastAPI will automatically parse the HTTP request for us.
    @app.post("/inference")
    async def base(self, request: Input):
        try:
            # returns a ray object that needs to be converted 
            result1 = await self.fastapi_deployment.remote(request)
            result2 = await self.Classifier2.remote(request)
            return "success"
        except Exception as e:
            logging.error(f"Error in Inference service: {e}")
            return {"error": str(e)}
    



@serve.deployment(ray_actor_options={"num_gpus": config.classifier1["num_gpus"]},autoscaling_config={
        "min_replicas": config.classifier1["min_replicas"],
        "initial_replicas": config.classifier1["initial_replicas"],
        "max_replicas": config.classifier1["max_replicas"],
        "target_num_ongoing_requests_per_replica": config.classifier1["target_num_ongoing_requests_per_replica"],
        "graceful_shutdown_timeout_s": config.classifier1["graceful_shutdown_timeout_s"],})

class Classifier1:
    def __init__(self):
        # Configure logging to write to a file
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            filename="ray_cluster.log",  # specify the file name if you want logging to be stored in a file
            filemode="a",  # append to the log file if it exists
        )
        self.logger = logging.getLogger(__name__)
        self.logger.propagate = True
        self.logger.info("Initializing model 1 ...")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger.info(f"Using device: {self.device}")
        self.model = models.resnet18(pretrained=True)
        self.model.eval()
        self.model.to(self.device)
        self.transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        
        self.logger.info("Model 1 initialized")
    @serve.batch(max_batch_size=config.classifier1["max_batch_size"],batch_wait_timeout_s=config.classifier1["batch_wait_timeout_s"]) 
    async def handle_batch(self, requests: List[Input]):
        inputs = []
        camera_ids = []
        for request in requests:
            try:
                image = Image.open(request.img_path)
                transformed_image = self.transform(image)
                inputs.append(transformed_image.to(self.device))  # Move tensor to the same device as model
                camera_ids.append(request.camera_id)  # Store camera_id for logging
            except Exception as e:
                self.logger.error(f"Error processing image at path {request.img_path}: {e}")
                inputs.append(torch.zeros([3, 224, 224], device=self.device))  # Placeholder for failed images
                camera_ids.append(request.camera_id)  # Store camera_id for logging

        inputs = torch.stack(inputs)
        try:
            with torch.no_grad():
                predictions = self.model(inputs)
                _, predicted = torch.max(predictions, 1)
            # Log predictions with corresponding camera_ids
            for camera_id, prediction in zip(camera_ids, predicted):
                self.logger.info(f"Camera ID: {camera_id}, Prediction classifier 1: {prediction.item()}")
            return [prediction.item() for prediction in predicted]
        except Exception as e:
            self.logger.error(f"Error during model prediction: {e}")
            return ["Error" for _ in requests]

    async def __call__(self, request: Input):
        try:
            return await self.handle_batch(request)
        except Exception as e:
            self.logger.error(f"Error in base endpoint: {e}")
            return {"error": str(e)}
        
@serve.deployment(ray_actor_options={"num_gpus": config.classifier2["num_gpus"]},autoscaling_config={
        "min_replicas": config.classifier2["min_replicas"],
        "initial_replicas": config.classifier2["initial_replicas"],
        "max_replicas": config.classifier2["max_replicas"],
        "target_num_ongoing_requests_per_replica": config.classifier2["target_num_ongoing_requests_per_replica"],
        "graceful_shutdown_timeout_s": config.classifier2["graceful_shutdown_timeout_s"],})
class Classifier2:
    def __init__(self):
        # Configure logging to write to a file
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            filename="ray_cluster.log",  # specify the file name if you want logging to be stored in a file
            filemode="a",  # append to the log file if it exists
        )
        self.logger = logging.getLogger(__name__)
        self.logger.propagate = True
        self.logger.info("Initializing model 2...")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger.info(f"Using device: {self.device}")
        self.model = models.resnet18(pretrained=True)
        self.model.eval()
        self.model.to(self.device)
        self.transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        
        self.logger.info("Model 2 initialized")
    @serve.batch(max_batch_size=config.classifier2["max_batch_size"],batch_wait_timeout_s=config.classifier2["batch_wait_timeout_s"])
    async def handle_batch(self, requests: List[Input]):
        inputs = []
        camera_ids = []
        for request in requests:
            try:
                image = Image.open(request.img_path)
                transformed_image = self.transform(image)
                inputs.append(transformed_image.to(self.device))  # Move tensor to the same device as model
                camera_ids.append(request.camera_id)  # Store camera_id for logging
            except Exception as e:
                self.logger.error(f"Error processing image at path {request.img_path}: {e}")
                inputs.append(torch.zeros([3, 224, 224], device=self.device))  # Placeholder for failed images
                camera_ids.append(request.camera_id)  # Store camera_id for logging

        inputs = torch.stack(inputs)
        try:
            with torch.no_grad():
                predictions = self.model(inputs)
                _, predicted = torch.max(predictions, 1)
            # Log predictions with corresponding camera_ids
            for camera_id, prediction in zip(camera_ids, predicted):
                self.logger.info(f"Camera ID: {camera_id}, Prediction classifier 2: {prediction.item()}")
            return [prediction.item() for prediction in predicted]
        except Exception as e:
            self.logger.error(f"Error during model prediction: {e}")
            return ["Error" for _ in requests]

    async def __call__(self, request: Input):
        try:
            
            return await self.handle_batch(request)
        except Exception as e:
            self.logger.error(f"Error in base endpoint: {e}")
            return {"error": str(e)}

# Initialize Ray and Serve
# Deploy the deployment   
ray.init() 
serve.start()
serve.run(Inference.bind(Classifier1.bind(),Classifier2.bind()),name = "Inference")
asyncio.run(main())