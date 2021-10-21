# ecc_zcashd_exporter

`pip3 install -r requirements.txt`

Docker

time docker build -t ecc_z_exporter .

real    0m16.119s
user    0m2.458s
sys     0m0.300s

docker image ls ecc_z_exporter:latest

REPOSITORY       TAG       IMAGE ID       CREATED              SIZE
ecc_z_exporter   latest    3271c08cb24c   About a minute ago   51.5MB

docker run -it --rm ecc_z_exporter:latest

docker-compose up -d

docker-compose stop

docker-compose ps

docker logs -f <image-name>

docker rm <image-name>

To rebuild this image you must use `docker-compose build` or `docker-compose up --build`.