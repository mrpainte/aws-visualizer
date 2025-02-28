from flask import Flask
import boto3
import threading
import aws_resource
import website

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
