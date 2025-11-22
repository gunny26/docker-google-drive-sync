# FROM --platform=linux/arm/v7 arm32v7/ubuntu:20.04
# FROM --platform=linux/arm64/v8 ubuntu:22.04
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Vienna
RUN apt update && apt -y --no-install-recommends upgrade
RUN apt install --no-install-recommends -y \
    tzdata \
    python3-setuptools \
    python3-pip \
    python3-requests \
    python3-yaml \
    python3-boto3 \
    python3-dateutil
WORKDIR /usr/src/app
COPY ./build/requirements.txt /usr/src/app/
COPY ./build/webstorageS3-1.2.1-py3-none-any.whl /usr/src/app/

# webtorage configuration
RUN mkdir /usr/src/app/.webstorage
# COPY ./secret/webstorage.yml /home/ubuntu/.webstorage/webstorage.yml
# some secrets, not the best way, but ...
# COPY ./secret/credentials.json /usr/src/app/credentials.json
# COPY ./secret/token.auth.drive.pickle /usr/src/app/token.auth.drive.pickle
# temporary data
RUN mkdir /usr/src/app/data
# make all available for user ubuntu
RUN chown -R ubuntu /usr/src/app

# install python modules
RUN pip3 install --break-system-packages --disable-pip-version-check --no-cache-dir ./webstorageS3-1.2.1-py3-none-any.whl
RUN pip3 install --break-system-packages --disable-pip-version-check --no-cache-dir -r requirements.txt
RUN pip3 freeze


# cleanup
# starting at 471MB
# with updates 473MB
# down to 227MB
RUN apt -y purge python3-pip python3-setuptools; \
    apt -y autoremove; \
    apt -y clean; rm /usr/src/app/webstorageS3-1.2.1-py3-none-any.whl

# adding NON-ROOT user
# RUN groupadd --gid 1000 newuser && \
#     useradd \
#       --home-dir /usr/src/app \
#       --uid 1000 \
#       --gid 1000 \
#       --shell /bin/sh \
#       --no-create-home \
#       appuser


# the main programs, the most frequent modfied part at least to improve image build speed
COPY ./build/tools.py /usr/src/app/tools.py
COPY ./build/main.py /usr/src/app/main.py

# EXPOSE 9100
USER ubuntu
CMD ["python3", "-u", "/usr/src/app/main.py"]
