# Yet Another Cryptocurrency Grid Bot (yacgb) - Still a work in progress

## Overview
An experiment in bot-based Crypto trading, with the goal of having it run in the cloud and having Jeff Bezos pay for running it! [^1]. The current implementation uses a standard grid trading strategy, with the ability to set several safety settings in cases that the current price of a currency goes outside of the grid. 

Built using:
- ccxt library, enabling access to just about every crypto exchange out there
- pynamodb library, enabling persistence using AWS DynamoDB

[^1]: Leveraging AWS Free-Tier, which notoriously lacks any guardrails. No gurantees it will actually cost you nothing and requires fairly regular monitoring and experience in AWS cost management practices, YMMV.

---

# Install
Prerequisites:
- Python3.x (Python 3.8 is preferred, based on AWS Lambda support)
- AWS CLI (awscli v2, although v1 may work as well)

```shell
$ git clone https://github.com/dsmorgan/yacgb.git
```
The bot can be installed in different ways in AWS, as well as can be run locally.

## Deploy in AWS, using supplied helper scripts
If not setup already, configure your awscli client. At a minimum, you'll need to set your region, access key and secret.

```shell
$ aws configure

```
Use the scripts in the aws directory to build and deploy.

```shell
$ cd yacgb/aws

```
Create bucket for storing the lambda and layers.

```shell
$ ./1-create-bucket.sh
make_bucket: yacgb-e7cccc733e0f6dac

```
Build the layers, resolve and missing dependencies before moving to the next step.

```shell
$ ./2-build-layer.sh
Collecting...

```
Edit the next script, and configure the exchanges and market symbols you plan to use. To be safe, you can avoid setting the apikey, secret and (sometimes) password in the script and instead set these through the AWS console. Additional exchange and symbols can be added as needed later.

```shell
$ ./2.5-config-sm-pss.sh 

{
    "Version": 1
...
```

Navigate to the AWS "Systems Manager", then to the "Parameter Store" under the Application Management sub menu to modify or add additional values if required.

Use the next script to setup the Cloud Formation to deploy the IAM roles and Lambda application.

```shell
$ ./3-deploy.sh  
Uploading to be3a6ef10140b918018413f1a656b614  24320563 / 24320563.0  (100.00%)
Successfully packaged artifacts and wrote output template to file aws/out.yml.
Execute the following command to deploy the packaged template
aws cloudformation deploy --template-file /home/dsm/workspace/yacgb/aws/out.yml --stack-name <YOUR STACK NAME>

Waiting for changeset to be created..
Waiting for stack create/update to complete
Successfully created/updated stack - yacgb
```
You can test the syncticker configuration and invoke it once to ensure everything is working...

```shell
./4-invoke.sh synctickers ../events/event.json
[INFO]  2021-06-22T03:43:05.393Z                CCXT version: 1.50.59
...

"OK"
```
A snippet of the log should be shown, and the "OK" indicates a successful execution. 

In order to keep the synctickers running periodically, you'll need to manually create a trigger (Event Bridge) that will execute the lambda auatomatically every configured period. 1 minute is preferred, and can be done by setting the Schedule Expression to: rate(1 minute)

You'll next need to perform backtesting and then setup a bot for running live.

### Deleting and Cleanup

Use the script in the aws directory to delete the stack and cleanup most of the functions.

```shell
$ ./5-cleanup.sh
Deleted yacgb stack.
Delete deployment artifacts and bucket (yacgb-e7cccc733e0f6dac)? (y/n)y
delete: s3://yacgb-e7cccc733e0f6dac/8fe9cf785d08943d9904b5e1c82d2c23
delete: s3://yacgb-e7cccc733e0f6dac/be3a6ef10140b918018413f1a656b614
remove_bucket: yacgb-e7cccc733e0f6dac
Delete function log group (/aws/lambda/yacgb-synctickers-772VVOXEiVVr)? (y/n)y
```

Some things that yiou may need to deleted to remove all traces of this deployment:
- Cloudwatch - remove all log groups associated with the yacgb application
- System Manager - remove all the parameter store configuration starting with "/yacgb"
- DynamoDB - delete the tables: OHLCV, Gbot, Market, and Orders (if they exist)


## Deploy in AWS, using SAM
Currently not working


## Run Locally
For test and development purposes, the bot components can be run locally as well, with the addition of:
* use pip to satisfy dependencies locally
* Download and install from AWS a local dynamodb 


**IMPORTANT:** When running locally, you need to make sure to set the environment variable to override the default location of the Dynamodb service, e.g. export DYNAMODB_HOST=http://localhost:8000. Otherwise, your awscli credentials and configuration may be used to leverage the AWS services.

---

# Backtesting
Experimentation until you are comfortable with the configuration to use in a live run.

# Running Live 
A 2 step process, liveinit sets up the grid and initial orders and is run only once. Liverun is then executed periodically to maintain the grid.

## Event.json Parameter Definitions

Sample event.json

```json
{
  "exchange": "binanceus",
  "market_symbol": "XLM/USD",
  "grid_spacing": 0.02,
  "total_quote": 1000,
  "max_ticker": 0.4443,
  "min_ticker": 0.3437,
  "reserve": 0,
  "live_balance": "True",
  "start_base": 0,
  "start_quote": 3000,
  "makerfee": 0.001,
  "takerfee": 0.001,
  "feecurrency": "USD",
  "backtest_start": "20210526 19:00",
  "backtest_end": "20210528 01:00",
  "take_profit": 0.5011
}
```



| Syntax | Description |
| ----------- | ----------- |
| exchange | (required) |
| market_symbol | (required)  |
| grid_spacing | (optional, default:0)|
| total_quote | |
| min_ticker | | 
| max_ticker | |
| reserve | |
| live_balance | |
| start_base | |
| start_quote | | 
| makerfee | |
| takerfee | |
| feecurrency | | 
| backtest_start | 20210526 19:00 |
| backtest_end  | 20210528 01:00 |
| take_profit | |
| stop_loss   | |
| profit_protect | |