FROM python:3.9

# adding NON-ROOT user
RUN groupadd --gid 1000 newuser \
    && useradd --home-dir /usr/src/app --create-home --uid 1000 \
        --gid 1000 --shell /bin/sh --skel /dev/null appuser
USER appuser


WORKDIR /usr/src/app
RUN mkdir /usr/src/app/data
RUN mkdir /usr/src/app/.webstorage

COPY ./build/requirements.txt /usr/src/app/
COPY ./build/tools.py /usr/src/app/tools.py
COPY ./build/webstorageS3-1.2.0-py3-none-any.whl /usr/src/app/

RUN pip install --no-cache-dir ./webstorageS3-1.2.0-py3-none-any.whl
RUN pip install --no-cache-dir -r requirements.txt
RUN pip freeze

# COPY ./webstorage.yml /usr/src/app/.webstorage/
COPY ./build/drive_sync.py /usr/src/app/main.py

ENTRYPOINT ["python", "-u", "/usr/src/app/main.py"]
