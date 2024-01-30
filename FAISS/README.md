This repository contains a minimal prototype for running a text similarity search using FAISS within a Docker container.

## To build the container.
```
docker build -t faiss-text-search .
```
## TO run the container. 
```
docker run -p 4000:80 -v .:/usr/src/app/data faiss-text-search
```