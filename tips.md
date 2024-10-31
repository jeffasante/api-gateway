
Build the Docker image:
docker build -t api-gateway .

Run the container:
docker run -d -p 8000:8000 api-gateway