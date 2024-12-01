#!/usr/bin/python3
"""
program to sync google drive data to webstorage and storing
metadata information in local json file
"""
import logging
import os
import time
# non std-modules
import boto3
import googleapiclient
from googleapiclient.discovery import build
from prometheus_client import start_http_server, Gauge, Summary
# own modules
from webstorageS3 import FileStorageClient
from tools import get_credentials, get_ids, get_metadata, download_file, put_metadata, put_filestorage


# mandatory parameters
APP_SCOPES = os.environ["APP_SCOPES"]  # APP_SCOPES
APP_TOKEN_FILE = os.environ["APP_TOKEN_FILE"]  # pickled token
APP_SECRETS_FILE = os.environ["APP_SECRETS_FILE"]  # google credentials
APP_BUCKET_NAME = os.environ["APP_BUCKET_NAME"]
APP_AWS_ACCESS_KEY_ID = os.environ["APP_AWS_ACCESS_KEY_ID"]
APP_AWS_SECRET_ACCESS_KEY = os.environ["APP_AWS_SECRET_ACCESS_KEY"]
APP_ENDPOINT_URL = os.environ["APP_ENDPOINT_URL"]
# with default values
APP_TMP_FILENAME = os.environ.get("APP_TMP_FILENAME", "/usr/src/app/data/tmp.dmp")  # name of temporary file
APP_INTERVAL = int(os.environ.get("APP_INTERVAL", "86400"))  # APP_INTERVAL in seconds to do the sync
APP_LOG_LEVEL = os.environ.get("APP_LOG_LEVEL", "INFO")

# setting Logging
if APP_LOG_LEVEL == "INFO":
    logging.getLogger().setLevel(logging.INFO)

if APP_LOG_LEVEL == "ERROR":
    logging.getLogger().setLevel(logging.ERROR)

if APP_LOG_LEVEL == "DEBUG":
    logging.getLogger().setLevel(logging.DEBUG)

# some informational output
for key in os.environ:
    if key.startswith("APP_"):
        logging.info(f"{key} : {os.environ.get(key)}")


# prometheus metrics
SUMMARY = Summary('drive_sync_processing_seconds', 'Time spent processing a sync')
STATS = {
    "analyzed": Gauge('drive_sync_analyzed', 'Number of analyzed objects'),
    "copied": Gauge('drive_sync_copied', 'Number of downloaded objects'),
    "skipped": Gauge('drive_sync_skipped', 'Number of skipped objects'),
    "error": Gauge('drive_sync_error', 'Number of objects where errors occured'),
    "empty": Gauge('drive_sync_empty', 'Number empty objects, they are skipped')
}


@SUMMARY.time()
def main():
    """ doing the whole sync process """
    fields = "nextPageToken, files(id, name, md5Checksum, size, kind, driveId, parents, mimeType)"  # fields to fetch from file
    creds = get_credentials(APP_TOKEN_FILE, APP_SCOPES, APP_SECRETS_FILE)
    service = build("drive", 'v3', credentials=creds)
    results = service.files().list(pageSize=100, fields=fields).execute()
    logging.debug(results)
    items = results.get("files", [])
    if not items:
        logging.error("No files found - nothing to do")
    else:
        fs = FileStorageClient(cache=False)
        client = boto3.client(  # global s3 target
            "s3",
            aws_access_key_id=APP_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=APP_AWS_SECRET_ACCESS_KEY,
            endpoint_url=APP_ENDPOINT_URL
        )
        local_ids = get_ids(client, APP_BUCKET_NAME)  # fetch previously stored ids
        logging.info(f"found {len(local_ids)} stored ids")
        while results.get("nextPageToken"):  # as long as there are more pages
            for item in items:
                STATS["analyzed"].inc()
                logging.info(f"analyzing {item['name']}")
                logging.debug(item)
                # something like this
                # {
                #   'kind': 'drive#file',
                #   'id': '1e06fQF3_k4jlCZ-MukXwCZHloUTS0NsT',
                #   'name': 'Der Schneemann - 1. Stimme langsam.MP3',
                #   'parents': ['12RvrvIpJtQQ-iYazsgzb0RjtWQSi6i7n'],
                #   'md5Checksum': 'df068a4b69d340403473e4806348c737',
                #   'size': '1348880
                # }
                if item['id'] in local_ids:  # id is already stored, comparing
                    metadata = get_metadata(client, APP_BUCKET_NAME, item["id"])
                    if metadata["md5Checksum"] != item["md5Checksum"]:  # is id the same content
                        logging.info(f"file {item['name']} was modified")
                    else:
                        logging.debug(f"skipping {item['name']} it is already stored")
                        STATS["skipped"].inc()
                        continue
                if item.get('md5Checksum') and item.get("size") != "0":  # only files with content, and size
                    logging.info(f"{item['id']} - {item['md5Checksum']} - {item['size']} - {item['name']}")
                    with open(APP_TMP_FILENAME, "wb") as outfile:
                        try:
                            download_file(service, item["id"], outfile)
                            logging.info(f"sucessfully downloaded {item['name']}")
                            STATS["copied"].inc()
                        except googleapiclient.errors.HttpError as exc:
                            logging.exception(exc)
                            logging.error(f"something went wrong skipping file {item['name']}")
                            os.unlink(APP_TMP_FILENAME)  # delete the file if something went wrong
                            STATS["error"].inc()
                            continue
                    with open(APP_TMP_FILENAME, "rb") as infile:
                        checksum = put_filestorage(fs, infile)
                        logging.debug(f"put item {item['name']} with checksum {checksum} on filestorage")
                    put_metadata(client, APP_BUCKET_NAME, item)
                else:
                    STATS["empty"].inc()
            logging.debug("Getting next page")
            results = service.files().list(pageToken=results.get("nextPageToken"), fields=fields).execute()
            items = results.get("files", [])
    if os.path.isfile(APP_TMP_FILENAME):
        os.unlink(APP_TMP_FILENAME)  # delete any left-overs


if __name__ == '__main__':
    # Start up the server to expose the metrics.
    start_http_server(9100)  # thats hard coded
    try:
        while True:
            starttime = time.time()
            main()
            duration = time.time() - starttime
            logging.info(f"sync took {duration} seconds to finish")
            time_left = max(0, APP_INTERVAL - duration)  # amount of seconds to sleep, at least zero
            logging.info(f"sleeping {time_left} seconds before doing the next loop")
            time.sleep(time_left)
    except Exception as exc:
        logging.exception(exc)
