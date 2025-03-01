from flask import render_template, request, jsonify
import aws_resource

def init_app(app):
    """Register Flask routes."""
    visibility_states = {
    "ec2": True,
    "asg": True,
    "elb": True,
    "nat": True,
    "igw": True,
    "nacl": True
    }

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/graph")
    def graph():
        """Serve the Pyvis-generated AWS graph."""
        return render_template("aws_graph.html")

    @app.route("/update")
    def update():
        """Trigger a manual AWS graph update."""
        aws_resource.build_graph()
        return jsonify({"message": "Graph updated!"})
    
    @app.route('/toggle/<resource>', methods=['POST'])
    def toggle_resource(resource):
        if resource in visibility_states:
            visibility_states[resource] = not visibility_states[resource]
            return jsonify({"status": "success", "resource": resource, "visible": visibility_states[resource]})
        return jsonify({"status": "error", "message": "Invalid resource"}), 400

