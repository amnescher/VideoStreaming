import asyncio
import ray
from ray import serve
import logging
import torch
from torchvision import models, transforms
from PIL import Image
import io
from ray.serve.handle import DeploymentHandle
import requests
from typing import Optional
from pydantic import BaseModel
from typing import List
from fastapi import FastAPI
from starlette.requests import Request
from fastapi import FastAPI

# Define the Input class
class Input(BaseModel):
    img_path: str
    camera_id: Optional[str]

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s:%(message)s', 
                    filename='app.log', 
                    filemode='w')

app = FastAPI()
@serve.deployment(route_prefix="/")
@serve.ingress(app)
class CrowdCounter2:
    def __init__(self):
        self.model = models.resnet18(pretrained=True)
        self.model.eval()
        self.transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    @serve.batch(max_batch_size=2)
    async def handle_batch(self, requests: List[Input]):
        inputs = []
        for request in requests:
            try:
                image = Image.open(request.img_path)
                inputs.append(self.transform(image))
            except Exception as e:
                logging.error(f"Error processing image: {e}")
                inputs.append(torch.zeros([3, 224, 224]))  # Placeholder for failed images
        inputs = torch.stack(inputs)
        with torch.no_grad():
            predictions = self.model(inputs)
            _, predicted = torch.max(predictions, 1)
        return [predicted.item() for predicted in predicted]
    app.post("/")
    async def base(self, request: Request):
        body = await request.json()
        input_data = [Input(**data) for data in body]
        return await self.handle_batch(input_data)
    app.post("/tets")
    async def test(self, request: requests):
        logging.info(f"Received request: {request}")

# Inference Deployment
# @serve.deployment(num_replicas=1, route_prefix="/inference")
# class Inference:
#     def __init__(self, crowd_counter2: DeploymentHandle):
#         self.crowd_counter2 = crowd_counter2

#     async def __call__(self, request: requests):
#         return await self.crowd_counter2.remote(request)

# Initialize Ray and Serve
serve.start()
crowd_counter2 = CrowdCounter2.bind()  
serve.run(crowd_counter2,name = "CrowdCounter2" )
# Deploy the services

