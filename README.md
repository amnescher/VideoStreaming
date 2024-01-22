
<p align="center">
  <img src="Diagram_task.svg" alt="Alternative Text" width="700"/>
</p>

# Video Processing Pipeline Deployed on Ray/KubeRay Cluster

The diagram above provides an overview of the designed pipeline, along with corresponding MLOps technologies. This pipeline is defined for a smart surveillance system and comprises four main components: producer, Kafka server, consumer, and model composition (Ray cluster). The following explains each component.

There are up to 150 cameras transmitting HD-quality videos to the producer. The producer's role is to receive video frames and store them in a memory bucket, shared among different components in the pipeline. It extracts the name, path to the bucket, and camera ID for each frame, then sends this information as messages to topics in the Kafka server. There is a topic on the Kafka server for each camera, named from camera_1 to camera_150.

To effectively handle the substantial volume of frames received from the cameras, the producer employs parallel processing using ray actors. Each actor is dedicated to processing video frames from a single camera. The efficiency and parallelization of the producer are further augmented by utilizing the async/wait functionality of Python. This approach allows for non-blocking communication with Kafka, ensuring that the rest of the code continues to execute uninterrupted. Each actor is capable of independently executing asynchronous operations. With multiple actors (one for each camera) running concurrently, each operates its own event loop, enabling simultaneous processing of multiple video streams. The process involves:

1: Each actor retrieves frames from its respective camera.

2: Frames are processed and prepared for transmission (e.g., storing in the bucket).

3: Frame paths are sent to Kafka asynchronously.

As these operations within each actor are asynchronous, there is no idle time while waiting for Kafka's I/O operations to finish.
 
The Kafka server, used as a distributed event streaming platform, runs as a Docker image. There is a separate topic for each camera to manage them individually.

The consumer mirrors the design of the producer, utilizing multiple parallel-running actors. Each actor within the consumer is linked to a specific Kafka topic corresponding to a camera. Similar to the producer, communication with the Kafka server in each actor is asynchronous. This design prevents any delay in receiving subsequent messages, thereby enhancing the consumer's efficiency. Each message received by the consumer includes the path to video frames (stored in the shared memory bucket) and the camera ID. Messages received by each actor are then formatted into HTTP requests and dispatched to a ray cluster. This setup ensures efficient handling of the data stream from each camera, maintaining the system's overall performance and responsiveness.

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
Install Docker with GPU support as per your system's requirements [here]('https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/index.html').

Create a Python virtual environment and activate it.
```
virtualenv dev
source dev/bin/activate
```
Install the required Python packages (ensure that you have a requirements.txt file in your project).
```
pip install -r requirements.txt
```
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

**Note**: The creation of 150 topics may take several seconds.

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
python ray_cluster.py
```

Once the cluster is runing, you can run the event producer to feed the kafka server with event and  the will be processed you the conseumer and consequently by my services. 

**Note:**  Multiple cameras are needed to feed video frames to the producer. To simplify the system for testing, two video clips are used to simulate the incoming video from cameras. These videos are sampled at 30fps to mimic a real camera scenario. Only minimal modifications to the producer are required to enable it to read videos from cameras instead of clips.
```
python ray_producer.py
```

Certainly! Improving the readability and clarity of your README file is essential for effective communication with users. Here's a revised version of the provided section:

---

## Cluster Configuration

### `config.yaml` File

This file contains the configuration settings for your Ray cluster. It allows you to define the specifications of your cluster, including node types and resources. Additionally, it includes policies for the cluster's autoscaling behavior. By fine-tuning these configurations, you can optimize the cluster's performance to suit your specific needs.



#### Factors Influencing the Processing Rate

The processing rate of AI models in this pipeline is influenced by several key factors:

1. **GPU Capacity**: The ability of the GPU to accommodate the maximum number of AI model replicas.
2. **Cluster Configuration**: The configuration of your cluster including, initial replica, max replica, and so on 
2. **Batch Sizes**: The size of dynamic batches processed by the AI models.
3. **Request Queue**: The number of ongoing requests per queue.

By adjusting these parameters, you can significantly impact the frame rate per second achieved by your AI models.

#### To measure the processing rate:

1. Ensure your cluster is configured according to your requirements.
2. Run the `send_request.py` script. This script sends concurrent requests to your cluster, simulating a real-world load.

The script will log the processing rate, measured in responses per second, into the `responsetime.log` file. This log provides insights into the performance of your cluster under different configurations and workloads.

With a 15 GB GPU memory and after experimenting with several configurations, I achieved a processing rate of 230 frames per second using the ray_cluster, which operates two image classifiers (ResNet18) in parallel. Higher FPS can be achieved by utilizing a high-performance infrastructure and optimal configuration of the cluster.

## To Do:
Packaging and Containerization of Ray Producer and Service Deployment.

Improve time to deployment using Ray model store. 
## The following video demonstrates a test of the pipeline's autoscaling capabilities when the producer component sends a large number of requests.


https://github.com/amnescher/VideoStreaming/assets/112868804/e2f94b86-f254-4d45-85aa-3b0ca54f03d9

