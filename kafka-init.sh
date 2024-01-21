#!/bin/bash

# Start Kafka in the background
/etc/confluent/docker/run &

# Wait for Kafka to start
sleep 10

# Create topics
for i in {1..150}
do
  kafka-topics --create --topic camera_$i --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
done

# Wait for Kafka to finish setting up
wait
