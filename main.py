from flask import Flask
import boto3
import threading
import aws_resource
import website
from argparse import ArgumentParser, HelpFormatter
from botocore.exceptions import ClientError, ProfileNotFound
import logging

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO, format='%(message)s')


# parse arguments
formatter = lambda prog: HelpFormatter(prog, max_help_position=52)
parser = ArgumentParser(formatter_class=formatter)

parser.add_argument("-v", "--vpc", required=True, help="The VPC to describe")
parser.add_argument("-r", "--region", default="us-west-2", help="AWS region that the VPC resides in")
parser.add_argument("-p", '--profile', default='default', help="AWS profile")
args = parser.parse_args()

try:
    # session = boto3.Session(profile_name=args.profile) # Gives Error: You are not authorized to perform this operation.
    session = boto3.Session(region_name=args.region) # This Works!
except ProfileNotFound as e:
    logger.warning(f"{e}, please provide a valid AWS profile name")
    exit(-1)

# Initialize Flask app
app = Flask(__name__)

# AWS Clients
ec2_client = boto3.client("ec2")
elb_client = boto3.client("elb")
elbv2_client = boto3.client("elbv2")
asg_client = boto3.client("autoscaling")

# Pass AWS clients to AWS functions
aws_resource.set_clients(ec2_client, elb_client, elbv2_client, asg_client)

# Register website routes
website.init_app(app)

def start_data_fetcher():
    """Background thread to periodically update AWS data."""
    aws_resource.fetch_aws_data()

# Start periodic AWS data fetching
threading.Thread(target=start_data_fetcher, daemon=True).start()

if __name__ == "__main__":
    app.run(debug=True)
