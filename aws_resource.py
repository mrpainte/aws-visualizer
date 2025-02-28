import boto3
import networkx as nx
import time

# Global AWS clients
ec2_client = None
elb_client = None
elbv2_client = None
asg_client = None

def set_clients(ec2, elb, elbv2, asg):
    """Initialize global AWS clients."""
    global ec2_client, elb_client, elbv2_client, asg_client
    ec2_client, elb_client, elbv2_client, asg_client = ec2, elb, elbv2, asg

def fetch_aws_data():
    """Periodically fetch AWS data."""
    while True:
        build_graph()
        time.sleep(120)  # Refresh every 2 minutes

def build_graph():
    """Builds the AWS connectivity graph."""
    graph = nx.Graph()
    fetch_ec2_instances(graph)
    fetch_asgs(graph)
    fetch_load_balancers(graph)
    fetch_nat_gateways(graph)
    fetch_internet_gateways(graph)
    fetch_network_acls(graph)
    save_graph(graph)

def fetch_ec2_instances(graph):
    """Fetch and add EC2 instances to the graph."""
    instances = ec2_client.describe_instances()["Reservations"]
    for res in instances:
        for inst in res["Instances"]:
            inst_id = inst["InstanceId"]
            graph.add_node(inst_id, label=f"EC2: {inst_id}", color="green")

def fetch_asgs(graph):
    """Fetch Auto Scaling Groups and link them to EC2 instances."""
    asgs = asg_client.describe_auto_scaling_groups()["AutoScalingGroups"]
    for asg in asgs:
        asg_name = asg["AutoScalingGroupName"]
        graph.add_node(asg_name, label=f"ASG: {asg_name}", color="cyan")
        for instance in asg["Instances"]:
            graph.add_edge(asg_name, instance["InstanceId"], color="gray", title="ASG Manages")

def fetch_load_balancers(graph):
    """Fetch Load Balancers and link them to EC2 instances."""
    elbs = elb_client.describe_load_balancers()["LoadBalancerDescriptions"]
    for elb in elbs:
        elb_name = elb["LoadBalancerName"]
        graph.add_node(elb_name, label=f"ELB: {elb_name}", color="orange")

        for instance in elb.get("Instances", []):
            graph.add_edge(elb_name, instance["InstanceId"], color="blue", title="ELB Directs To")

    # Fetch Application Load Balancers (ALBs) as well
    elbv2 = elbv2_client.describe_load_balancers()["LoadBalancers"]
    for alb in elbv2:
        alb_name = alb["LoadBalancerName"]
        graph.add_node(alb_name, label=f"ALB: {alb_name}", color="red")

        # Connect to target groups (simplified example)
        for target_group in alb.get("TargetGroups", []):
            graph.add_edge(alb_name, target_group["TargetGroupName"], color="purple", title="ALB Directs To")

def fetch_nat_gateways(graph):
    """Fetch NAT Gateways and link them to subnets."""
    nat_client = boto3.client("ec2")
    nat_gateways = nat_client.describe_nat_gateways()["NatGateways"]

    for ngw in nat_gateways:
        ngw_id = ngw["NatGatewayId"]
        subnet_id = ngw["SubnetId"]
        graph.add_node(ngw_id, label=f"NAT GW: {ngw_id}", color="yellow")
        graph.add_edge(ngw_id, subnet_id, color="white", title="Located In")

def fetch_internet_gateways(graph):
    """Fetch Internet Gateways and link them to VPCs."""
    igw_client = boto3.client("ec2")
    igws = igw_client.describe_internet_gateways()["InternetGateways"]

    for igw in igws:
        igw_id = igw["InternetGatewayId"]
        graph.add_node(igw_id, label=f"IGW: {igw_id}", color="lightblue")

        for attachment in igw.get("Attachments", []):
            vpc_id = attachment.get("VpcId")
            if vpc_id:
                graph.add_edge(igw_id, vpc_id, color="orange", title="Attached to VPC")

def fetch_network_acls(graph):
    """Fetch Network ACLs and link them to subnets."""
    nacl_client = boto3.client("ec2")
    nacls = nacl_client.describe_network_acls()["NetworkAcls"]

    for nacl in nacls:
        nacl_id = nacl["NetworkAclId"]
        graph.add_node(nacl_id, label=f"NACL: {nacl_id}", color="pink")

        for assoc in nacl["Associations"]:
            subnet_id = assoc["SubnetId"]
            graph.add_edge(nacl_id, subnet_id, color="gray", title="Applies to Subnet")

def save_graph(graph):
    """Save graph as an interactive HTML file."""
    from pyvis.network import Network
    net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white")
    net.from_nx(graph)
    net.save_graph("templates/aws_graph.html")
