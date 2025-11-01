import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app import app, agent


@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.mark.asyncio
async def test_a2a_endpoint_success(client):
    """Test successful async request to /tasks/send"""
    payload = {
        "jsonrpc": "2.0",
        "id": "test-123",
        "method": "execute",
        "params": {
            "contextId": "ctx-1",
            "taskId": "task-1",
            "messages": [
                {
                    "kind": "message",
                    "role": "user",
                    "parts": [
                        {
                            "kind": "text",
                            "text": "Help me learn Python"
                        }
                    ]
                }
            ]
        }
    }
    
    # Mock the async agent call
    with patch.object(agent, 'process_messages_async', new_callable=AsyncMock) as mock_process:
        from models.a2a import TaskResult, TaskStatus, A2AMessage, MessagePart, Artifact
        
        mock_result = TaskResult(
            id="task-1",
            contextId="ctx-1",
            status=TaskStatus(
                state="completed",
                message=A2AMessage(
                    role="agent",
                    parts=[MessagePart(kind="text", text="Study plan generated")]
                )
            ),
            artifacts=[
                Artifact(
                    name="study_plan",
                    parts=[MessagePart(kind="text", text="# Python Study Plan")]
                )
            ]
        )
        mock_process.return_value = mock_result
        
        response = client.post(
            '/tasks/send',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "test-123"
        assert data["result"]["status"]["state"] == "completed"


@pytest.mark.asyncio
async def test_a2a_endpoint_timeout(client):
    """Test timeout handling in /tasks/send endpoint"""
    payload = {
        "jsonrpc": "2.0",
        "id": "test-timeout",
        "method": "execute",
        "params": {
            "messages": [
                {
                    "kind": "message",
                    "role": "user",
                    "parts": [
                        {
                            "kind": "text",
                            "text": "Complex request"
                        }
                    ]
                }
            ]
        }
    }
    
    # Mock a slow async call that times out
    async def slow_process(*args, **kwargs):
        await asyncio.sleep(10)
        return None
    
    with patch.object(agent, 'process_messages_async', side_effect=slow_process):
        response = client.post(
            '/tasks/send',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 408  # Request Timeout
        data = json.loads(response.data)
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "test-timeout"
        assert "error" in data
        assert data["error"]["code"] == -32000
        assert "timeout" in data["error"]["message"].lower()


def test_a2a_endpoint_invalid_json(client):
    """Test handling of invalid JSON body"""
    response = client.post(
        '/tasks/send',
        data="invalid json",
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["jsonrpc"] == "2.0"
    assert "error" in data


def test_a2a_endpoint_missing_jsonrpc(client):
    """Test handling of missing jsonrpc field"""
    payload = {
        "id": "test-123",
        "method": "execute"
    }
    
    response = client.post(
        '/tasks/send',
        data=json.dumps(payload),
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "error" in data


def test_a2a_endpoint_method_not_found(client):
    """Test handling of unknown method"""
    payload = {
        "jsonrpc": "2.0",
        "id": "test-123",
        "method": "unknown_method",
        "params": {}
    }
    
    response = client.post(
        '/tasks/send',
        data=json.dumps(payload),
        content_type='application/json'
    )
    
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data["error"]["code"] == -32601


@pytest.mark.asyncio
async def test_a2a_endpoint_message_send_method(client):
    """Test the message/send method"""
    payload = {
        "jsonrpc": "2.0",
        "id": "test-msg-send",
        "method": "message/send",
        "params": {
            "message": {
                "kind": "message",
                "role": "user",
                "messageId": "msg-123",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Learn JavaScript"
                    }
                ]
            },
            "configuration": {
                "blocking": True
            }
        }
    }
    
    with patch.object(agent, 'process_messages_async', new_callable=AsyncMock) as mock_process:
        from models.a2a import TaskResult, TaskStatus, A2AMessage, MessagePart, Artifact
        
        mock_result = TaskResult(
            id="msg-123",
            contextId="auto-generated",
            status=TaskStatus(
                state="completed",
                message=A2AMessage(
                    role="agent",
                    parts=[MessagePart(kind="text", text="JavaScript plan")]
                )
            ),
            artifacts=[]
        )
        mock_process.return_value = mock_result
        
        response = client.post(
            '/tasks/send',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["result"]["status"]["state"] == "completed"
