import requests
from fastapi import FastAPI
from ray import serve
import logging
import torch
from torchvision import models, transforms
from PIL import Image
from typing import Optional, List
from pydantic import BaseModel
from fastapi import Request
import os
from ray.serve.handle import DeploymentHandle
import ray
# Define the Input class
class Input(BaseModel):
    img_path: str
    camera_id: Optional[str]

# Define a FastAPI app and wrap it in a deployment with a route handler.
app = FastAPI()

@serve.deployment(route_prefix="/")
@serve.ingress(app)
class Inference:
    def __init__(self, Classifier1: DeploymentHandle, Classifier2: DeploymentHandle,):
        self.fastapi_deployment =  Classifier1
        self.Classifier2 = Classifier2
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            filename="app.log",  # specify the file name if you want logging to be stored in a file
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
    

@serve.deployment(num_replicas=1)
class Classifier1:
    def __init__(self):
        # Configure logging to write to a file
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            filename="app.log",  # specify the file name if you want logging to be stored in a file
            filemode="a",  # append to the log file if it exists
        )
        self.logger = logging.getLogger(__name__)
        self.logger.propagate = True
        self.logger.info("Initializing model 1 ...")
        self.model = models.resnet18(pretrained=True)
        self.model.eval()
        self.transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        
        self.logger.info("Model 1 initialized")
    @serve.batch(max_batch_size=2)
    async def handle_batch(self, requests: List[Input]):
        inputs = []
        for request in requests:
            try:
                image = Image.open(request.img_path)
                inputs.append(self.transform(image))
            except Exception as e:
                self.logger.error(f"Error processing image at path {request.img_path}: {e}")
                inputs.append(torch.zeros([3, 224, 224]))  # Placeholder for failed images
        inputs = torch.stack(inputs)
        try:
            with torch.no_grad():
                predictions = self.model(inputs)
                _, predicted = torch.max(predictions, 1)
            self.logger.info(f"Predictions classifier 1: {predicted}")
            return [predicted.item() for predicted in predicted]
        except Exception as e:
            self.logger.error(f"Error during model prediction: {e}")
            return ["Error" for _ in requests]

    async def __call__(self, request: Input):
        try:
            
            return await self.handle_batch(request)
        except Exception as e:
            self.logger.error(f"Error in base endpoint: {e}")
            return {"error": str(e)}
        
@serve.deployment(num_replicas=1)
class Classifier2:
    def __init__(self):
        # Configure logging to write to a file
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            filename="app.log",  # specify the file name if you want logging to be stored in a file
            filemode="a",  # append to the log file if it exists
        )
        self.logger = logging.getLogger(__name__)
        self.logger.propagate = True
        self.logger.info("Initializing model 2...")
        self.model = models.resnet18(pretrained=True)
        self.model.eval()
        self.transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        
        self.logger.info("Model 2 initialized")
    @serve.batch(max_batch_size=2)
    async def handle_batch(self, requests: List[Input]):
        inputs = []
        for request in requests:
            try:
                image = Image.open(request.img_path)
                inputs.append(self.transform(image))
            except Exception as e:
                self.logger.error(f"Error processing image at path {request.img_path}: {e}")
                inputs.append(torch.zeros([3, 224, 224]))  # Placeholder for failed images
        inputs = torch.stack(inputs)
        try:
            with torch.no_grad():
                predictions = self.model(inputs)
                _, predicted = torch.max(predictions, 1)
            self.logger.info(f"Predictions classifier 2: {predicted}")
            return [predicted.item() for predicted in predicted]
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
        
serve.start()
serve.run(Inference.bind(Classifier1.bind(),Classifier2.bind()),name = "Inference")
