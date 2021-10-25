#Image layers are not split because of pycurl C dependency issues 
FROM alpine:3
WORKDIR /app
RUN apk add -u --no-cache build-base python3-dev \
    && apk add -u --no-cache --virtual .build-deps curl-dev py3-wheel py3-pip
ADD requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
ADD . .
RUN chmod +x ecc_zcashd_exporter.py
CMD [ "/app/ecc_zcashd_exporter.py" ]


##Env that might simplify debugging +- bash or python env/deploy
#FROM python:3.9-slim
#ADD . /app/
#WORKDIR /app/
#RUN apt-get update && apt-get install gcc libcurl4-openssl-dev libssl-dev -y
#RUN pip install --no-cache-dir -r requirements.txt
#RUN chmod +x ecc_zcashd_exporter.py & cp ecc_zcashd_exporter.py /usr/local/bin/
#ENTRYPOINT ["/usr/local/bin/ecc_zcashd_exporter.py"]