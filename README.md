# Video Processing Pipeline Deployed on Ray/KubeRay Cluster
#### This repository contains a video processing pipeline designed to operate on a Ray/KubeRay cluster, leveraging the power of distributed computing for efficient handling and processing of video data.

## Requirements
### Hardware
GPU: A GPU with a minimum of 10 GB memory is required to deploy the machine learning (ML) service. For scaling the application, the GPU requirement can increase up to 40 GB.
### Software
Docker for GPU: You will need to install Docker with GPU support to run containers that utilize GPU resources.
Virtual Environment: Set up a Python virtual environment and install the required packages for isolated Python package management.
## Setup and Installation
Pull the Code
Clone the repository to your local machine or download the source code.

## Install Dependencies
Install Docker with GPU support as per your system's requirements.
Create a Python virtual environment and activate it.
Install the required Python packages using pip install -r requirements.txt (ensure that you have a requirements.txt file in your project).
## Run Apache Kafka
Apache Kafka is used as a distributed event store and for stream-processing. Follow these steps to set up Kafka:

### Make the Initialization Script Executable
Run the following command to make the Kafka initialization script executable:

```
chmod +x kafka-init.sh
```

This script is responsible for generating 150 topics named 'camera_1' to 'camera_150', which are used by the event producer and consumer components of the application.

Start the Kafka Server and Topics
Use Docker Compose to start the Kafka server along with the 150 topics:

```
sudo docker compose up -d
```

You can verify the creation of the topics by accessing the Kafka broker container and listing the topics:

```
docker exec -it broker /bin/sh
```
Then, execute the following command within the broker container to list all topics:

```
kafka-topics --list --bootstrap-server localhost:9092
```

## Run Ray Cluster

The Ray cluster consists of a Kafka consumer service that receives events from the Kafka server. These events are then fed into ML microservices for processing by various image processing services.

```
service_deployment.py
```

Once the cluster is runing, you can run the event producer to feed the kafka server with event and  the will be processed you the conseumer and consequently by my services. 

```
python ray_producer.py
```

## To Do:
Packaging and contarisation of ray producer and service deployment. 