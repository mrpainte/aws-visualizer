import boto3
import networkx as nx
import time

# Global AWS clients
ec2_client = None
elb_client = None
elbv2_client = None
asg_client = None

# Global resource details
resource_details = {
    "ec2": [],
    "asg": [],
    "elb": [],
    "nat": [],
    "igw": [],
    "nacl": [],
    "subnet": [],
    "sg": [],
    "route_table": []  # Add route_table to resource details
}

# Global visibility states
visibility_states = {
    "ec2": True,
    "asg": True,
    "elb": True,
    "nat": True,
    "igw": True,
    "nacl": True,
    "subnet": True,
    "sg": True,
    "route_table": True  # Add route_table to visibility states
}

def set_clients(ec2, elb, elbv2, asg):
    """Initialize global AWS clients."""
    global ec2_client, elb_client, elbv2_client, asg_client
    ec2_client, elb_client, elbv2_client, asg_client = ec2, elb, elbv2, asg

def fetch_aws_data():
    """Periodically fetch AWS data."""
    while True:
        build_graph(visibility_states, resource_details)
        time.sleep(120)  # Refresh every 2 minutes

def build_graph(visibility_states, resource_details):
    """Builds the AWS connectivity graph."""
    graph = nx.Graph()
    instance_info = {}
    resource_details["ec2"] = []
    resource_details["asg"] = []
    resource_details["elb"] = []
    resource_details["nat"] = []
    resource_details["igw"] = []
    resource_details["nacl"] = []
    resource_details["subnet"] = []
    resource_details["sg"] = []
    resource_details["route_table"] = []  # Initialize route_table details

    if visibility_states["ec2"]:
        instance_info = fetch_ec2_instances2(graph, instance_info, resource_details["ec2"])
    subnet_mapping = fetch_subnets(graph, resource_details["subnet"])
    if visibility_states["asg"]:
        fetch_asgs(graph, resource_details["asg"])
    if visibility_states["elb"]:
        fetch_load_balancers2(graph, instance_info, resource_details["elb"])
    if visibility_states["nat"]:
        fetch_nat_gateways(graph, resource_details["nat"])
    if visibility_states["igw"]:
        fetch_internet_gateways(graph, resource_details["igw"])
    if visibility_states["nacl"]:
        fetch_network_acls(graph, resource_details["nacl"])
    if visibility_states["sg"]:
        fetch_security_groups(graph, resource_details["sg"])
    if visibility_states["route_table"]:
        fetch_route_tables(graph, subnet_mapping, resource_details["route_table"])  # Pass route_table details list
    save_graph(graph)

def fetch_route_tables(graph, subnet_mapping, details_list):
    """Fetch route tables and determine subnet-to-subnet connectivity."""
    route_tables = ec2_client.describe_route_tables()
    subnet_links = set()
    
    for rt in route_tables["RouteTables"]:
        rt_id = rt["RouteTableId"]
        graph.add_node(rt_id, label=f"RT: {rt_id}", color="brown", title=f"Route Table: {rt_id}")
        details_list.append(f"Route Table ID: {rt_id}")

        for assoc in rt.get("Associations", []):
            subnet_id = assoc.get("SubnetId")
            if not subnet_id:
                continue  # Skip non-explicit subnet associations
            graph.add_edge(rt_id, subnet_id, color="gray", title="Associated with Subnet")

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

def fetch_subnets(graph, details_list):
    """Fetch subnets and add them to the graph."""
    subnets = ec2_client.describe_subnets()
    subnet_mapping = {}  # Store subnet-to-VPC relationships
    for subnet in subnets["Subnets"]:
        subnet_id = subnet["SubnetId"]
        vpc_id = subnet["VpcId"]
        name_tag = next((tag["Value"] for tag in subnet.get("Tags", []) if tag["Key"] == "Name"), subnet_id)
        graph.add_node(subnet_id, label=f"Subnet: {name_tag}", color="purple", title=f"Subnet in VPC {vpc_id}")
        subnet_mapping[subnet_id] = vpc_id
        # Add subnet details to the details list
        details_list.append(f"Subnet ID: {subnet_id}, VPC ID: {vpc_id}, Name: {name_tag}")
    return subnet_mapping

def fetch_security_groups(graph, details_list):
    """Fetch security groups and add them to the graph."""
    security_groups = ec2_client.describe_security_groups()["SecurityGroups"]
    for sg in security_groups:
        sg_id = sg["GroupId"]
        sg_name = sg["GroupName"]
        inbound_rules = sg["IpPermissions"]
        outbound_rules = sg["IpPermissionsEgress"]

        inbound_rules_str = "\n".join([f"Inbound: {rule}" for rule in inbound_rules])
        outbound_rules_str = "\n".join([f"Outbound: {rule}" for rule in outbound_rules])

        sg_title = f"SG: {sg_name}\nInbound Rules:\n{inbound_rules_str}\nOutbound Rules:\n{outbound_rules_str}"

        graph.add_node(sg_id, label=f"SG: {sg_name}", color="blue", title=sg_title)
        # Add security group details to the details list
        details_list.append(f"SG ID: {sg_id}, Name: {sg_name}, Inbound Rules: {inbound_rules_str}, Outbound Rules: {outbound_rules_str}")

def fetch_ec2_instances2(graph, instance_info, details_list):
    """Fetch EC2 instances, add them to the graph, and connect them to security groups."""
    instances = ec2_client.describe_instances()
    if "Reservations" in instances:
        for reservation in instances["Reservations"]:
            if "Instances" in reservation:
                for instance in reservation["Instances"]:
                    instance_id = instance["InstanceId"]
                    subnet_id = instance["SubnetId"]
                    instance_info[instance_id] = instance  # Store metadata
                    instance_name = next((tag["Value"] for tag in instance.get("Tags", []) if tag["Key"] == "Name"), instance_id)

                    graph.add_node(
                        instance_id,
                        label=f"EC2: {instance_name}",
                        color="green",
                        title=f"Instance ID: {instance_id}\nSubnet: {subnet_id}\nState: {instance['State']['Name']}",
                    )
                    # add the instance node to the subnet node
                    graph.add_edge(subnet_id, instance_id, color="gray", title="Located In")

                    # Connect EC2 to its security groups
                    for sg in instance.get("SecurityGroups", []):
                        sg_id = sg["GroupId"]
                        sg_name = sg["GroupName"]
                        sg_details = ec2_client.describe_security_groups(GroupIds=[sg_id])["SecurityGroups"][0]
                        inbound_rules = sg_details["IpPermissions"]
                        outbound_rules = sg_details["IpPermissionsEgress"]

                        inbound_rules_str = "\n".join([f"Inbound: {rule}" for rule in inbound_rules])
                        outbound_rules_str = "\n".join([f"Outbound: {rule}" for rule in outbound_rules])

                        sg_title = f"SG: {sg_name}\nInbound Rules:\n{inbound_rules_str}\nOutbound Rules:\n{outbound_rules_str}"

                        graph.add_node(sg_id, label=f"SG: {sg_name}", color="blue", title=sg_title)
                        # add the sg node to the instance node
                        graph.add_edge(instance_id, sg_id, color="gray", title="Attached to SG")

                    # Add instance details to the details list
                    details_list.append(f"Instance ID: {instance_id}, Name: {instance_name}, State: {instance['State']['Name']}, Subnet: {subnet_id}")

    return instance_info

def fetch_asgs(graph, details_list):
    """Fetch Auto Scaling Groups and link them to EC2 instances."""
    asgs = asg_client.describe_auto_scaling_groups()["AutoScalingGroups"]
    for asg in asgs:
        asg_name = asg["AutoScalingGroupName"]
        graph.add_node(asg_name, label=f"ASG: {asg_name}", color="cyan")
        for instance in asg["Instances"]:
            graph.add_edge(asg_name, instance["InstanceId"], color="gray", title="ASG Manages")
        # Add ASG details to the details list
        details_list.append(f"ASG Name: {asg_name}, Instances: {len(asg['Instances'])}")

def fetch_load_balancers2(graph, instance_info, details_list):
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

        # Add ALB details to the details list
        details_list.append(f"ALB Name: {alb_name}, ARN: {alb_arn}")

    # Classic Load Balancers (ELBs)
    for elb in elb_data["LoadBalancerDescriptions"]:
        elb_name = elb["LoadBalancerName"]
        graph.add_node(elb_name, label=f"ELB: {elb_name}", color="orange", title=f"ELB: {elb_name}")

        for instance in elb["Instances"]:
            ec2_id = instance["InstanceId"]
            if ec2_id in instance_info:
                graph.add_edge(elb_name, ec2_id, color="red", title="Routes Traffic to")

        # Add ELB details to the details list
        details_list.append(f"ELB Name: {elb_name}")

def fetch_nat_gateways(graph, details_list):
    """Fetch NAT Gateways and link them to subnets."""
    nat_client = boto3.client("ec2")
    nat_gateways = nat_client.describe_nat_gateways()["NatGateways"]

    for ngw in nat_gateways:
        ngw_id = ngw["NatGatewayId"]
        subnet_id = ngw["SubnetId"]
        graph.add_node(ngw_id, label=f"NAT GW: {ngw_id}", color="yellow")
        graph.add_edge(ngw_id, subnet_id, color="white", title="Located In")

        # Add NAT Gateway details to the details list
        details_list.append(f"NAT Gateway ID: {ngw_id}, Subnet ID: {subnet_id}")

def fetch_internet_gateways(graph, details_list):
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

        # Add Internet Gateway details to the details list
        details_list.append(f"Internet Gateway ID: {igw_id}")

def fetch_network_acls(graph, details_list):
    """Fetch Network ACLs and link them to subnets."""
    nacl_client = boto3.client("ec2")
    nacls = nacl_client.describe_network_acls()["NetworkAcls"]

    for nacl in nacls:
        nacl_id = nacl["NetworkAclId"]
        graph.add_node(nacl_id, label=f"NACL: {nacl_id}", color="pink")

        for assoc in nacl["Associations"]:
            subnet_id = assoc["SubnetId"]
            graph.add_edge(nacl_id, subnet_id, color="gray", title="Applies to Subnet")

        # Add Network ACL details to the details list
        details_list.append(f"NACL ID: {nacl_id}")

def save_graph(graph):
    """Save graph as an interactive HTML file."""
    from pyvis.network import Network
    net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white")
    net.from_nx(graph)
    
    # Set physics options to enable auto-scaling
    net.set_options("""
    var options = {
        "physics": {
            "enabled": true,
            "barnesHut": {
                "gravitationalConstant": -8000,
                "centralGravity": 0.3,
                "springLength": 95,
                "springConstant": 0.04,
                "damping": 0.09,
                "avoidOverlap": 0.1
            },
            "minVelocity": 0.75
        },
        "nodes": {
            "scaling": {
                "min": 10,
                "max": 30
            }
        },
        "edges": {
            "scaling": {
                "min": 1,
                "max": 5
            }
        }
    }
    """)
    
    # Set physics options to make nodes sticky
    for node in net.nodes:
        node['physics'] = False  # Disable physics for this node (makes it sticky)
    
    # Add edge labels
    for edge in net.edges:
        if 'label' in edge:
            edge['title'] = edge['label']  # Display the label as a tooltip
    
    net.save_graph("templates/aws_graph.html")
    net.save_graph("static/aws_graph.html")
