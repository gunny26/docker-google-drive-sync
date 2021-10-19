#!/usr/bin/python3
"""
program to sync google drive data to webstorage and storing
metadata information in local json file
"""
import json
import logging
import os
# non std-modules
import boto3
import googleapiclient
from googleapiclient.discovery import build
# own modules
from webstorageS3 import FileStorageClient
from tools import get_credentials, get_ids, get_metadata, download_file, put_metadata, put_filestorage


SCOPES = os.environ["SCOPES"]  # scopes
TOKEN_FILE = os.environ["TOKEN_FILE"]  # pickled token
SECRETS_FILE = os.environ["SECRETS_FILE"]  # google credentials
TMP_FILENAME = os.environ["TMP_FILENAME"]  # name of temporary file
BUCKET_NAME = os.environ["BUCKET_NAME"]
AWS_ACCESS_KEY_ID = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
ENDPOINT_URL = os.environ["ENDPOINT_URL"]


# setting Logging
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
if LOG_LEVEL == "INFO":
    logging.getLogger().setLevel(logging.INFO)

if LOG_LEVEL == "ERROR":
    logging.getLogger().setLevel(logging.ERROR)

if LOG_LEVEL == "DEBUG":
    logging.getLogger().setLevel(logging.DEBUG)


def main():
    stats = {
        "analyzed": 0,
        "copied": 0,
        "skipped": 0,
        "error": 0,
        "empty": 0
    }
    fields = "nextPageToken, files(id, name, md5Checksum, size, kind, driveId, parents, mimeType)"  # fields to fetch from file
    creds = get_credentials(TOKEN_FILE, SCOPES, SECRETS_FILE)
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
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            endpoint_url=ENDPOINT_URL
        )
        local_ids = get_ids(client, BUCKET_NAME)  # fetch previously stored ids
        logging.info(f"found {len(local_ids)} stored ids")
        while results.get("nextPageToken"):  # as long as there are more pages
            for item in items:
                stats["analyzed"] += 1
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
                    metadata = get_metadata(client, BUCKET_NAME, item["id"])
                    if metadata["md5Checksum"] != item["md5Checksum"]:  # is id the same content
                        logging.info(f"file {item['name']} was modified")
                    else:
                        logging.debug(f"skipping {item['name']} it is already stored")
                        stats["skipped"] += 1
                        continue
                if item.get('md5Checksum') and item.get("size") != "0":  # only files with content, and size
                    logging.info(f"{item['id']} - {item['md5Checksum']} - {item['size']} - {item['name']}")
                    with open(TMP_FILENAME, "wb") as outfile:
                        try:
                            download_file(service, item["id"], outfile)
                            logging.info(f"sucessfully downloaded item['name']")
                        except googleapiclient.errors.HttpError as exc:
                            logging.exception(exc)
                            logging.error(f"something went wrong skipping file {item['name']}")
                            os.unlink(TMP_FILENAME)  # delete the file if something went wrong
                            stats["error"] += 1
                            continue
                    with open(TMP_FILENAME, "rb") as infile:
                        checksum = put_filestorage(fs, infile)
                        logging.debug(f"put item {item['name']} with checksum {checksum} on filestorage")
                    put_metadata(client, BUCKET_NAME, item)
                else:
                    stats["empty"] += 1
            logging.debug("Getting next page")
            results = service.files().list(pageToken=results.get("nextPageToken"), fields=fields).execute()
            items = results.get("files", [])
    if os.path.isfile(TMP_FILENAME):
        os.unlink(TMP_FILENAME)  # delete any left-overs
    logging.info(json.dumps(stats, indent=4))


if __name__ == '__main__':
    main()
