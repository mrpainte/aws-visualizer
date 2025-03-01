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
    instance_info = {}
    #fetch_ec2_instances(graph)
    instance_info = fetch_ec2_instances2(graph, instance_info)
    fetch_asgs(graph)
    #fetch_load_balancers(graph)
    fetch_load_balancers2(graph, instance_info)
    fetch_nat_gateways(graph)
    fetch_internet_gateways(graph)
    fetch_network_acls(graph)
    subnet_mapping = fetch_subnets(graph)
    fetch_route_tables(graph, subnet_mapping)
    save_graph(graph)

def fetch_ec2_instances(graph):
    """Fetch and add EC2 instances to the graph."""
    instances = ec2_client.describe_instances()["Reservations"]
    for res in instances:
        for inst in res["Instances"]:
            inst_id = inst["InstanceId"]
            graph.add_node(inst_id, label=f"EC2: {inst_id}", color="green")

def fetch_ec2_instances2(graph, instance_info):
    """Fetch EC2 instances, add them to the graph, and connect them to security groups."""
    instances = ec2_client.describe_instances()
    for reservation in instances["Reservations"]:
        for instance in reservation["Instances"]:
            instance_id = instance["InstanceId"]
            subnet_id = instance["SubnetId"]
            instance_info[instance_id] = instance  # Store metadata

            graph.add_node(
                instance_id,
                label=f"EC2: {instance_id}",
                color="green",
                title=f"Instance ID: {instance_id}\nSubnet: {subnet_id}\nState: {instance['State']['Name']}",
            )

            # Connect EC2 to its security groups
            for sg in instance.get("SecurityGroups", []):
                sg_id = sg["GroupId"]
                graph.add_edge(instance_id, sg_id, color="gray", title="Attached to SG")
                #graph.add_node()

            # Connect EC2 to its subnet (this is handled in fetch_subnets)
    return instance_info

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

def fetch_load_balancers2(graph, instance_info):
    """Fetch ALBs and ELBs, then link them to their EC2 instances."""
    alb_data = elbv2_client.describe_load_balancers()
    elb_data = elb_client.describe_load_balancers()

    # Application Load Balancers (ALBs)
    for alb in alb_data["LoadBalancers"]:
        alb_arn = alb["LoadBalancerArn"]
        alb_name = alb["LoadBalancerName"]
        graph.add_node(alb_arn, label=f"ALB: {alb_name}", color="orange", title=f"ALB: {alb_name}")

        tg_data = elbv2_client.describe_target_groups(LoadBalancerArn=alb_arn)
        for tg in tg_data["TargetGroups"]:
            tg_arn = tg["TargetGroupArn"]
            targets = elbv2_client.describe_target_health(TargetGroupArn=tg_arn)["TargetHealthDescriptions"]
            for target in targets:
                ec2_id = target["Target"]["Id"]
                if ec2_id in instance_info:
                    graph.add_edge(alb_arn, ec2_id, color="red", title="Routes Traffic to")

    # Classic Load Balancers (ELBs)
    for elb in elb_data["LoadBalancerDescriptions"]:
        elb_name = elb["LoadBalancerName"]
        graph.add_node(elb_name, label=f"ELB: {elb_name}", color="orange", title=f"ELB: {elb_name}")

        for instance in elb["Instances"]:
            ec2_id = instance["InstanceId"]
            if ec2_id in instance_info:
                graph.add_edge(elb_name, ec2_id, color="red", title="Routes Traffic to")

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

def fetch_subnets(graph):
    """Fetch subnets and add them to the graph."""
    subnets = ec2_client.describe_subnets()
    subnet_mapping = {}  # Store subnet-to-VPC relationships
    for subnet in subnets["Subnets"]:
        subnet_id = subnet["SubnetId"]
        vpc_id = subnet["VpcId"]
        if subnet["Tags"]:
            name_tag = next((tag["Value"] for tag in subnet["Tags"] if tag["Key"] == "Name"), subnet_id)
        graph.add_node(subnet_id, label=f"Subnet: {name_tag}", color="purple", title=f"Subnet in VPC {vpc_id}")
       
        subnet_mapping[subnet_id] = vpc_id
    return subnet_mapping

def fetch_route_tables(graph, subnet_mapping):
    """Fetch route tables and determine subnet-to-subnet connectivity."""
    route_tables = ec2_client.describe_route_tables()
    subnet_links = set()
    
    for rt in route_tables["RouteTables"]:
        for assoc in rt.get("Associations", []):
            subnet_id = assoc.get("SubnetId")
            if not subnet_id:
                continue  # Skip non-explicit subnet associations
            
            for route in rt["Routes"]:
                if "DestinationCidrBlock" in route and "VpcPeeringConnectionId" in route:
                    # Peered VPCs - assume full communication
                    for other_subnet, vpc in subnet_mapping.items():
                        if vpc == subnet_mapping[subnet_id] and other_subnet != subnet_id:
                            subnet_links.add((subnet_id, other_subnet))
                elif "GatewayId" in route and "igw-" in route["GatewayId"]:
                    # Internet Gateway (public access)
                    graph.add_edge(subnet_id, "Internet", color="yellow")

    # Add subnet-to-subnet edges
    for s1, s2 in subnet_links:
        graph.add_edge(s1, s2, color="white", title="Connected via Route Table")

def save_graph(graph):
    """Save graph as an interactive HTML file."""
    from pyvis.network import Network
    net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white")
    net.from_nx(graph)
    
    # Set physics options to make nodes sticky
    for node in net.nodes:
        node['physics'] = False  # Disable physics for this node (makes it sticky)
    
     # Add edge labels
    for edge in net.edges:
        if 'label' in edge:
            edge['title'] = edge['label']  # Display the label as a tooltip
    
    net.save_graph("templates/aws_graph.html")
