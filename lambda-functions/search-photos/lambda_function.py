import json
import os
import urllib.parse
import uuid

import boto3
import urllib3

lex = boto3.client("lexv2-runtime")
http = urllib3.PoolManager()

OS_ENDPOINT = os.environ["OS_ENDPOINT"].rstrip("/")
OS_USER = os.environ["OS_USER"]
OS_PASS = os.environ["OS_PASS"]
BOT_ID = os.environ["BOT_ID"]
BOT_ALIAS_ID = os.environ["BOT_ALIAS_ID"]
LOCALE_ID = os.environ["LOCALE_ID"]
INDEX = "photos"

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Methods": "GET,PUT,OPTIONS",
}


def respond(results):
    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps({"results": results}),
    }


def get_query(event):
    # Works for API Gateway proxy integration and for direct test events
    params = event.get("queryStringParameters") or {}
    return (params.get("q") or event.get("q") or "").strip()


def singular_forms(word):
    """Return the word plus a likely singular form (dogs -> dog, puppies -> puppy)."""
    word = word.lower().strip()
    forms = {word}
    if len(word) > 3:
        if word.endswith("ies"):
            forms.add(word[:-3] + "y")
        elif word.endswith(("ches", "shes", "xes", "ses", "zes")):
            forms.add(word[:-2])
        elif word.endswith("s") and not word.endswith("ss"):
            forms.add(word[:-1])
    return forms


def get_keywords_from_lex(query):
    resp = lex.recognize_text(
        botId=BOT_ID,
        botAliasId=BOT_ALIAS_ID,
        localeId=LOCALE_ID,
        sessionId=str(uuid.uuid4()),
        text=query,
    )
    print("Lex response:", json.dumps(resp, default=str))

    intent = resp.get("sessionState", {}).get("intent", {})
    if intent.get("name") != "SearchIntent":
        return []

    keywords = []
    for slot in (intent.get("slots") or {}).values():
        if slot and slot.get("value"):
            value = slot["value"].get("interpretedValue") or slot["value"].get("originalValue")
            if value:
                keywords.append(value)
    return keywords


def search_opensearch(keywords):
    terms = set()
    for k in keywords:
        terms |= singular_forms(k)
    print("Search terms:", terms)

    query = {
        "size": 100,
        "query": {
            "bool": {
                "should": [{"match": {"labels": t}} for t in terms],
                "minimum_should_match": 1,
            }
        },
    }

    headers = urllib3.make_headers(basic_auth=f"{OS_USER}:{OS_PASS}")
    headers["Content-Type"] = "application/json"
    resp = http.request(
        "GET",
        f"{OS_ENDPOINT}/{INDEX}/_search",
        body=json.dumps(query),
        headers=headers,
    )
    data = json.loads(resp.data.decode())
    print("OpenSearch status:", resp.status)

    results = []
    for hit in data.get("hits", {}).get("hits", []):
        src = hit["_source"]
        url = f"https://{src['bucket']}.s3.amazonaws.com/{urllib.parse.quote(src['objectKey'])}"
        results.append({"url": url, "labels": src.get("labels", [])})
    return results


def lambda_handler(event, context):
    print("Received event:", json.dumps(event))
    query = get_query(event)
    if not query:
        return respond([])

    keywords = get_keywords_from_lex(query)
    print("Keywords from Lex:", keywords)
    if not keywords:
        return respond([])

    return respond(search_opensearch(keywords))
