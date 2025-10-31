from flask import Flask, request, jsonify, Response
from models.a2a import JSONRPCRequest, JSONRPCResponse, TaskResult, TaskStatus, Artifact, MessagePart, A2AMessage
from agents.agent import StudlyAgent
import json
from flask_cors import CORS
app = Flask(__name__)
CORS(app)
agent = StudlyAgent()

@app.route("/")
def home():
    return "Server is live"

@app.route("/.well-known/agent.json",methods=["GET"])
def agent_card():
    metadata = {
        "name": "Studly",
        "description": "The Study Plan Generator is an AI-driven assistant that creates personalized, adaptive study schedules based on a user's goals, available time, and preferred learning style.",
        "url": request.host_url.rstrip('/'),
        "version": "1.0",
        "capabilities":{
            "streaming": False,
            "pushNotifications": False
        },
        "skills": [
            {
                "name": "generate_study_plan",
                "description": "Creates personalized study plans based on user input."
            }
        ]
    }
    metadata_json = json.dumps(metadata, indent=2)
    return Response(metadata_json, mimetype="application/json")

@app.route("/tasks/send", methods=["POST"])
def a2a_endpoint():
    "Main A2A Endpoint"
    try:
        body = request.get_json()
        if body is None:
            return jsonify({
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32600,
                    "message": "Invalid Request: No JSON body"
                }
            }), 400
        
        # Validate JSON-RPC request
        if body.get("jsonrpc") != "2.0" or "id" not in body:
            return jsonify({
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "error": {
                    "code": -32600,
                    "message": "Invalid Request: jsonrpc must be '2.0' and id is required"
                }
            }), 400
        
        rpc_request = JSONRPCRequest(**body)
        
        # Extract messages
        messages = []
        context_id = None
        task_id = None
        config = None
        
        if rpc_request.method == "message/send":
            messages = [rpc_request.params.message]
            config = rpc_request.params.configuration
        elif rpc_request.method == "execute":
            messages = rpc_request.params.messages
            context_id = rpc_request.params.contextId
            task_id = rpc_request.params.taskId
        else:
            return jsonify({
                "jsonrpc": "2.0",
                "id": rpc_request.id,
                "error": {"code": -32601, "message": "Method not found"}
            }), 404
        print(messages)
        result = agent.process_messages(
                messages=messages,
                context_id=context_id,
                task_id=task_id,
                config=config
            )

        
        response = JSONRPCResponse(
            id=rpc_request.id,
            result=result
        )
        return jsonify(response.model_dump())
    except Exception as e:
        app.logger.error(
        f"A2A endpoint error - ID: {body.get('id') if 'body' in locals() else 'N/A'}, "
        f"Method: {body.get('method') if 'body' in locals() else 'N/A'}, "
        f"Exception: {str(e)}",
        exc_info=True  # Includes full traceback
    )
        return jsonify({
            "jsonrpc": "2.0",
            "id": body.get("id") if "body" in locals() else None,
            "error": {
                "code": -32603,
                "message": "Internal error",
                "data": {"details": str(e)}
            }
        }), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)