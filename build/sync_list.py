#!/usr/bin/python3
"""
program to sync google drive data to webstorage and storing
metadata information in local json file
"""
import os
import hashlib
import json
import pickle
# nin std-modules
import boto3
import yaml
# non-std modules installed by pip
import googleapiclient
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from apiclient import http
# own modules
from webstorageS3 import FileStorageClient
from tools import *

with open("config.yml", "rt") as infile:
    CONFIG = yaml.safe_load(infile)

# If modifying these scopes, delete the file token.pickle.
# thats the scope to downlaod something
SCOPES = CONFIG["scopes"] # scopes
TOKEN_FILE = CONFIG["token_file"] # pickeld token
SECRETS_FILE = CONFIG["secrets_file"] # google credentials
TMP_FILE = CONFIG["tmp_file"] # name of temporary file
DATA_DIR = CONFIG["data_dir"] # directory to store metadata
BUCKET_NAME = CONFIG["bucket_name"]

def main():
    fs = FileStorageClient()
    client = boto3.client( # global s3 target
        "s3",
        aws_access_key_id=CONFIG["aws_access_key_id"],
        aws_secret_access_key=CONFIG["aws_secret_access_key"],
        endpoint_url=CONFIG["endpoint_url"]
    )
    for drive_id in get_ids(client, BUCKET_NAME):
        metadata = get_metadata(client, BUCKET_NAME, drive_id)
        print(f"{metadata['sha1Checksum']} {metadata['size']:10} {fs.exist(metadata['sha1Checksum'])} {metadata['name']}")
    return

if __name__ == '__main__':
    main()
