# Photo Album: Natural-Language Photo Search on AWS

**Cloud Computing & Big Data, NYU Tandon, Fall 2026, Assignment 3**
**Student:** Khushi Agarwal (NetID: ka2653), solo submission

A photo album web app where users upload photos (with optional custom labels) and search them using natural language, e.g. "trees", "show me cats and dogs", or a custom label like "Sam".

**Live demo:** http://khushi-photos-frontend-b1.s3-website-us-east-1.amazonaws.com

## Architecture
| Component | AWS service | Details |
|---|---|---|
| Frontend (B1) | S3 static website hosting | `front-end/`, uses the API Gateway generated JS SDK |
| Photo storage (B2) | S3 | `khushi-photos-b2`, PUT events trigger LF1 |
| Index photos (LF1) | Lambda `index-photos` | Rekognition `detect_labels` + `x-amz-meta-customLabels` metadata, indexed into OpenSearch |
| Search photos (LF2) | Lambda `search-photos` | Lex V2 extracts keywords, plural to singular, OpenSearch query |
| Search index | Amazon OpenSearch Service | domain `photos`, index `photos` |
| NLU | Amazon Lex V2 | `PhotoSearchBot`, `SearchIntent` with `keywordOne` / `keywordTwo` slots |
| API | API Gateway (REST) | `GET /search?q=` to LF2; `PUT /photos/{object}` to S3 proxy; API key + usage plan |
| CI/CD | CodePipeline + CodeBuild | P1 deploys both Lambdas, P2 deploys the frontend to B1, on every push to `main` |
| IaC | CloudFormation | `other-scripts/cloudformation-T1.yml` provisions LF1, LF2, API Gateway, B1, B2 |

## Repository layout
~~~
front-end/          index.html, app.js, apiGateway-js-sdk/
lambda-functions/   index-photos/ (LF1), search-photos/ (LF2)
other-scripts/      buildspec-lambda.yml (P1), buildspec-frontend.yml (P2), cloudformation-T1.yml (T1)
~~~

## Indexed document format
~~~json
{ "objectKey": "my-photo.jpg", "bucket": "khushi-photos-b2",
  "createdTimestamp": "2026-11-14T23:02:00", "labels": ["sam", "sally", "dog", "pet"] }
~~~

## Deploying with CloudFormation
Upload `other-scripts/cloudformation-T1.yml` in the CloudFormation console with a lowercase stack name, enter the OpenSearch password parameter, and acknowledge IAM capabilities. Outputs include the website URL and API invoke URL.
