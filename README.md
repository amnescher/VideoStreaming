
<p align="center">
  <img src="Diagram_task.svg" alt="Alternative Text" width="700"/>
</p>

# Video Processing Pipeline Deployed on Ray/KubeRay Cluster

The diagram above provides an overview of the designed pipeline, along with corresponding MLOps technologies. This pipeline is defined for a smart surveillance system and comprises four main components: producer, Kafka server, consumer, and model composition (Ray cluster). The following explains each component.

There are up to 150 cameras transmitting HD-quality videos to the producer. The producer's role is to receive video frames and store them in a memory bucket, shared among different components in the pipeline. It extracts the name, path to the bucket, and camera ID for each frame, then sends this information as messages to topics in the Kafka server. There is a topic on the Kafka server for each camera, named from camera_1 to camera_150.

To efficiently process the large volume of frames sent from the cameras to the producer, the producer is parallelized using ray actors. Multiple actors are responsible for processing frames from each camera, and the number of actors can be scaled up or down as needed. The Kafka server, used as a distributed event streaming platform, runs as a Docker image. There is a separate topic for each camera to manage them individually.

The consumer is designed similarly to the producer, with multiple actors running in parallel. Each actor in the consumer receives messages from Kafka topics. Multiple actors may be responsible for each topic. The messages received by consumers, containing the path to video frames (stored in a bucket) and the camera ID, are sent to a ray deployment cluster in HTTP requests.

The ray cluster, which contains several models including an inference service and multiple AI models, receives these requests. The inference service downloads the image from the bucket and sends it to multiple AI models for parallel processing. Notably, all parallel processing is designed in an asynchronous manner to avoid any bottlenecks in the system. The models run predictions on the images and save the results in a log file. Each model in the ray cluster has a queue for requests, an initial number of replicas, minimum and maximum replica counts, and a policy for starting new replicas. When the number of requests in the queue of each replica exceeds a preset value, a new replica of that model is started to address requests more quickly. Additionally, dynamic batch processing is added to each model, allowing a batch of images to be processed for maximum GPU utilization.

Depending on the GPU infrastructure, the ray cluster configuration can be adjusted for maximum request handling. All producers, consumers, and the ray cluster can be executed either on a ray engine on a single-node, multiple-GPU infrastructure, or, for a multi-node, multi-GPU setup, the pipeline can be submitted (without any changes) as a job to a Kubernetes/KubeRay cluster.
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

**Note:**  Multiple cameras are needed to feed video frames to the producer. To simplify the system for testing, two video clips are used to simulate the incoming video from cameras. These videos are sampled at 30fps to mimic a real camera scenario. Only minimal modifications to the producer are required to enable it to read videos from cameras instead of clips.
```
python ray_producer.py
```

## To Do:
Packaging and Containerization of Ray Producer and Service Deployment.

## The following video demonstrates a test of the pipeline's autoscaling capabilities when the producer component sends a large number of requests.


https://github.com/amnescher/VideoStreaming/assets/112868804/e2f94b86-f254-4d45-85aa-3b0ca54f03d9

