#Create base build layer for python libs
#FROM python:3 as builder
#ADD . /app/
#WORKDIR /app/
#RUN pip install -r requirements.txt & \
#    chmod +x ecc_zcashd_exporter.py

#Move build environment into runner layer
#FROM alpine:latest
#RUN apk --no-cache add ca-certificates
#WORKDIR /root/
#COPY --from=builder /app/ecc_zcashd_exporter.py /usr/local/bin/
#CMD [ "/bin/sh", "/usr/local/bin/ecc_zcashd_exporter.py" ]

# FROM python:alpine

# # Needed for the pycurl compilation
# ENV PYCURL_SSL_LIBRARY=openssl

# ADD . /app/
# WORKDIR /app/
# RUN apk --no-cache add ca-certificates libcurl libstdc++
# RUN apk add -u --no-cache --virtual .build-deps build-base g++ libffi-dev curl-dev
# RUN pip install --no-cache-dir -r requirements.txt \
#     && apk del --no-cache --purge .build-deps \
#     && rm -rf /var/cache/apk/*
# RUN chmod +x ecc_zcashd_exporter.py & cp ecc_zcashd_exporter.py /usr/local/bin/
# CMD ["/bin/sh", "/usr/local/bin/ecc_zcashd_exporter.py"]
#CMD 'bash'


FROM python:3.9-slim
ADD . /app/
WORKDIR /app/
RUN apt-get update && apt-get install gcc libcurl4-openssl-dev libssl-dev -y
RUN pip install --no-cache-dir -r requirements.txt
RUN chmod +x ecc_zcashd_exporter.py & cp ecc_zcashd_exporter.py /usr/local/bin/
ENTRYPOINT ["/usr/local/bin/ecc_zcashd_exporter.py"]