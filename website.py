from flask import render_template, request, jsonify
import aws_resource

visibility_states = {
    "ec2": True,
    "asg": True,
    "elb": True,
    "nat": True,
    "igw": True,
    "nacl": True
}

resource_details = {
    "ec2": [],
    "asg": [],
    "elb": [],
    "nat": [],
    "igw": [],
    "nacl": []
}

def init_app(app):
    """Register Flask routes."""

    @app.route("/")
    def index():
        return render_template("test-index.html")

    @app.route("/graph")
    def graph():
        """Serve the Pyvis-generated AWS graph."""
        return render_template("aws_graph.html")

    @app.route("/update")
    def update():
        """Trigger a manual AWS graph update."""
        aws_resource.build_graph(visibility_states, resource_details)
        return jsonify({"message": "Graph updated!"})
    
    @app.route('/toggle/<resource>', methods=['POST'])
    def toggle_resource(resource):
        if resource in visibility_states:
            visibility_states[resource] = not visibility_states[resource]
            aws_resource.build_graph(visibility_states, resource_details)  # Rebuild the graph with updated visibility states
            return jsonify({"status": "success", "resource": resource, "visible": visibility_states[resource]})
        return jsonify({"status": "error", "message": "Invalid resource"}), 400

    @app.route('/details/<resource>', methods=['GET'])
    def get_resource_details(resource):
        if resource in resource_details:
            return jsonify({"status": "success", "details": resource_details[resource]})
        return jsonify({"status": "error", "message": "Invalid resource"}), 400

