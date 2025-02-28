from flask import render_template, request, jsonify
import aws_resource

def init_app(app):
    """Register Flask routes."""

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
