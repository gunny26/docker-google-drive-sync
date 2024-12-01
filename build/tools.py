#!/usr/bin/python3
import os
import hashlib
import json
import pickle
# non std-modules
import requests
# import boto3
# import yaml
# non-std modules installed by pip
# import googleapiclient
# from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from apiclient import http


def download_file(service, file_id, local_fd):
    """
    download some file from drive to local file descriptor
    :param service: google api drive service
    :param file_id: file_id of file in drive
    :param local_fd: local open file in wb
    """
    request = service.files().get_media(fileId=file_id)
    media_request = http.MediaIoBaseDownload(local_fd, request)
    while True:
        _, done = media_request.next_chunk()
        if done:
            return


def download_media(base_url: str, local_fd):
    """
    download photo from google photos
    this is not the original file
    :param baseUrl: from mediaItem Data
    :param local_fd: local open file in wb
    """
    with requests.get(base_url, stream=True) as res:
        res.raise_for_status()
        for chunk in res.iter_content(chunk_size=1024 * 1024):
            # If you have chunk encoded response uncomment if
            # and set chunk_size parameter to None.
            # if chunk:
            local_fd.write(chunk)


def get_file_sha1(local_fd) -> str:
    """
    returning sha1 checksum of file
    :param local_fd: local open file in rb
    """
    local_fd.seek(0) # goto start
    filehash = hashlib.sha1()
    blocksize = 1024 * 1024
    # Put blocks in Blockstorage
    data = local_fd.read(blocksize)
    while data:
        filehash.update(data) # running filehash until end
        data = local_fd.read(blocksize)
    filedigest = filehash.hexdigest()
    return filedigest


def get_ids(client, bucket_name: str) -> list:
    """
    get local or in s3 stored ids
    :param directory <str>: directory to search for id's
    """
    ret_data = []
    # Create a reusable Paginator
    paginator = client.get_paginator('list_objects')
    # Create a PageIterator from the Paginator
    page_iterator = paginator.paginate(Bucket=bucket_name)
    for page in page_iterator:
        for key in page["Contents"]:
            if key["Key"].endswith(".json"):
                ret_data.append(key["Key"].replace(".json", ""))
    return ret_data


def get_keys(client, bucket_name: str) -> list:
    """
    generator to get objects in s3 bucket, returning Key
    :param directory <str>: directory to search for id's
    """
    # Create a reusable Paginator
    paginator = client.get_paginator('list_objects')
    # Create a PageIterator from the Paginator
    page_iterator = paginator.paginate(Bucket=bucket_name)
    for page in page_iterator:
        for key in page["Contents"]:
            if key["Key"].endswith(".json"):
                yield key["Key"].replace(".json", "")


def get_metadata(client, bucket_name: str, item_id: str) -> dict:
    """
    return s3 object content, item_id is used to build key of object
    """
    data = client.get_object(Bucket=bucket_name, Key=item_id + ".json")
    metadata = json.loads(data["Body"].read())
    return metadata


def put_metadata(client, bucket_name: str, metadata: dict) -> None:
    """
    storing metadata as object in s3 bucket
    """
    res = client.put_object(Bucket=bucket_name, Key=metadata["id"] + ".json", Body=json.dumps(metadata).encode("utf-8"))
    print(res)


def put_filestorage(client, infile) -> str:
    """
    put content of file to filestorage, if checksum did not exist
    :param filename <str>: name of file to put to filestorage
    :return <str> checksum:
    """
    checksum = get_file_sha1(infile)
    if not client.exist(checksum):
        infile.seek(0)
        # something like this
        # {
        #   'blockchain': ['34bc60d2eceaeab4ac120163f5782ac34e7f3075'],
        #   'size': 247854,
        #   'checksum': '34bc60d2eceaeab4ac120163f5782ac34e7f3075',
        #   'mime_type': 'application/octet-stream',
        #   'filehash_exists': True,
        #   'blockhash_exists': 1
        # }
        result = client.put(infile)
        print(f"added file {result['checksum']} ({result['size']} bytes)")
        assert result["checksum"] == checksum # must be the same
    else:
        print(f"skipping checksum {checksum}, already in filestorage")
    return checksum # returning resulting checksum


def get_credentials(token_file: str, scopes: str, secrets_file: str) -> dict:
    """
    :param token_file: filename of pickled token
    :param scopes: scopes to request
    """
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    creds = None
    if os.path.exists(token_file):  # if some token file exists
        with open(token_file, "rb") as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(secrets_file, scopes)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_file, "wb") as token:
            pickle.dump(creds, token)
    return creds
