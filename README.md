Access the Kafka Broker Container
```
docker exec -it broker /bin/sh

```
```
kafka-topics --create --topic camera_1 --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
```

Verify Topic Creation

```
kafka-topics --list --bootstrap-server localhost:9092
```
Send message

```
kafka-console-producer --topic camera_1 --bootstrap-server localhost:9092

```