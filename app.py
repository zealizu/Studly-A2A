from flask import Flask, request, jsonify, Response, stream_with_context
from models.a2a import JSONRPCRequest, JSONRPCResponse, TaskResult, TaskStatus, Artifact, MessagePart, A2AMessage
from agents.agent import StudlyAgent
import json
from flask_cors import CORS
from utils import normalize_telex_message
from pydantic import ValidationError
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
            "streaming": True,
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
    """Main A2A Endpoint"""
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
        
        # Log raw body for debugging Telex payloads
        app.logger.info(f"Raw Telex body: {json.dumps(body, indent=2)}")
        
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
        print(body)
        
        # Now safe: Model supports Telex nesting
        rpc_request = JSONRPCRequest(**body)
        
        # Extract messages
        messages = []
        context_id = None
        task_id = None
        config = None
        
        if rpc_request.method == "message/send":
            raw_message = rpc_request.params.message
            config = rpc_request.params.configuration
            
            # Call the normalizer for Telex format
            messages = normalize_telex_message(raw_message)
            
            task_id = raw_message.messageId
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
        
        print(messages)  # Debug: Should now show list of A2AMessage
        
        if not messages:
            # Fallback if normalizer returns empty (rare, but safe)
            app.logger.warning("Normalizer returned empty messages - using fallback")
            fallback_message = A2AMessage(role="user", parts=[MessagePart(kind="text", text="Please provide a study topic.")])
            messages = [fallback_message]
        
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

@app.route("/tasks/sendSubscribe", methods=["POST"])
def a2a_stream_endpoint():
    """A2A Streaming Endpoint - Yields SSE for progressive responses"""
    def generate_stream():
        body = request.get_json()
        if body is None:
            yield f"data: {json.dumps({'error': 'No JSON body'})}\n\n"
            return
        
        # Log and validate (mirror your /tasks/send logic)
        app.logger.info(f"Stream Telex body: {json.dumps(body, indent=2)}")
        if body.get("jsonrpc") != "2.0" or "id" not in body:
            yield f"data: {json.dumps({'error': 'Invalid JSON-RPC'})}\n\n"
            return

        print(body)  # Your debug
        
        # Parse RPC (your try-fallback if needed; assume updated model)
        rpc_request = JSONRPCRequest(**body)
        
        # Extract/normalize (reuse your code)
        messages = []
        task_id = body.get('id')
        if rpc_request.method == "message/send":
            raw_message = rpc_request.params.message
            messages = normalize_telex_message(raw_message)
            if not messages:
                messages = [A2AMessage(role="user", parts=[MessagePart(kind="text", text="Default query")])]
        # ... (execute unchanged)
        
        print(messages)  # Your debug

        # Yield initial "in_progress"
        yield f"data: {json.dumps({'id': task_id, 'status': {'state': 'in_progress'}, 'message': {'role': 'agent', 'parts': [{'kind': 'text', 'text': 'Generating your study plan...'}]}})}\n\n"
        
        # Stream Gemini chunks (from your chain)
        user_text = messages[-1].parts[0].text if messages and messages[-1].parts else "Quick study plan"
        full_plan = ""  # Aggregate chunks
        for chunk in agent.chain.stream({"query": user_text}):  # LangChain stream
            if hasattr(chunk, 'content') and chunk.content:
                full_plan += chunk.content
                # Yield incremental chunk for client
                yield f"data: {json.dumps({'id': task_id, 'chunk': chunk.content})}\n\n"

        # Final "completed" with aggregated plan
        yield f"data: {json.dumps({'id': task_id, 'status': {'state': 'completed'}, 'artifacts': [{'name': 'study_plan', 'parts': [{'kind': 'text', 'text': full_plan}]}]})}\n\n"
        yield "data: [DONE]\n\n"
        # End SSE
    return Response(
        stream_with_context(generate_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",  # Telex CORS
            "Access-Control-Allow-Headers": "Content-Type",
            "X-Accel-Buffering": "no"  # Disable buffering in proxies
        }
    )
        
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)