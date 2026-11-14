import json
import os
import urllib.parse

import boto3
import urllib3

s3 = boto3.client("s3")
rekognition = boto3.client("rekognition")
http = urllib3.PoolManager()

OS_ENDPOINT = os.environ["OS_ENDPOINT"].rstrip("/")
OS_USER = os.environ["OS_USER"]
OS_PASS = os.environ["OS_PASS"]
INDEX = "photos"


def lambda_handler(event, context):
    print("Received event:", json.dumps(event))

    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])

        # 1. Detect labels with Rekognition
        rek = rekognition.detect_labels(
            Image={"S3Object": {"Bucket": bucket, "Name": key}},
            MaxLabels=20,
            MinConfidence=70,
        )
        rek_labels = [label["Name"].lower() for label in rek["Labels"]]
        print("Rekognition labels:", rek_labels)

        # 2. Read custom labels from S3 metadata
        #    (S3 lowercases metadata keys: x-amz-meta-customLabels -> "customlabels")
        head = s3.head_object(Bucket=bucket, Key=key)
        raw_custom = head.get("Metadata", {}).get("customlabels", "")
        custom_labels = [c.strip().lower() for c in raw_custom.split(",") if c.strip()]
        print("Custom labels:", custom_labels)

        # 3. Combine (custom first, no duplicates)
        all_labels = list(dict.fromkeys(custom_labels + rek_labels))

        doc = {
            "objectKey": key,
            "bucket": bucket,
            "createdTimestamp": head["LastModified"].strftime("%Y-%m-%dT%H:%M:%S"),
            "labels": all_labels,
        }

        # 4. Index into OpenSearch (object key as doc id, so re-uploads overwrite)
        doc_id = urllib.parse.quote(key, safe="")
        url = f"{OS_ENDPOINT}/{INDEX}/_doc/{doc_id}"
        headers = urllib3.make_headers(basic_auth=f"{OS_USER}:{OS_PASS}")
        headers["Content-Type"] = "application/json"

        resp = http.request("PUT", url, body=json.dumps(doc), headers=headers)
        print("OpenSearch response:", resp.status, resp.data.decode())

    return {"statusCode": 200, "body": json.dumps("Indexed successfully")}
