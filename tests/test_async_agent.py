import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from agents.agent import StudlyAgent
from models.a2a import A2AMessage, MessagePart


@pytest.mark.asyncio
async def test_process_messages_async_success():
    """Test successful async message processing"""
    agent = StudlyAgent()
    
    messages = [
        A2AMessage(
            role="user",
            parts=[MessagePart(kind="text", text="Help me learn Python in 2 weeks")]
        )
    ]
    
    # Mock the LLM call
    with patch.object(agent.chain, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
        mock_response = MagicMock()
        mock_response.content = "# 2-Week Python Study Plan\n## Week 1: Basics\n## Week 2: Advanced Topics"
        mock_ainvoke.return_value = mock_response
        
        result = await agent.process_messages_async(messages=messages)
        
        assert result.status.state == "completed"
        assert result.status.message is not None
        assert result.status.message.role == "agent"
        assert len(result.artifacts) == 1
        assert result.artifacts[0].name == "study_plan"
        assert "Python" in result.artifacts[0].parts[0].text


@pytest.mark.asyncio
async def test_process_messages_async_timeout():
    """Test timeout handling in async message processing"""
    agent = StudlyAgent()
    
    messages = [
        A2AMessage(
            role="user",
            parts=[MessagePart(kind="text", text="Complex request")]
        )
    ]
    
    # Mock a slow LLM call that exceeds timeout
    async def slow_response(*args, **kwargs):
        await asyncio.sleep(10)  # Simulate slow response
        return MagicMock(content="Response")
    
    with patch.object(agent.chain, 'ainvoke', side_effect=slow_response):
        # Test with a short timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                agent.process_messages_async(messages=messages),
                timeout=0.5
            )


@pytest.mark.asyncio
async def test_process_messages_async_empty_text():
    """Test handling of empty text input"""
    agent = StudlyAgent()
    
    messages = [
        A2AMessage(
            role="user",
            parts=[MessagePart(kind="text", text="   ")]  # Empty/whitespace only
        )
    ]
    
    result = await agent.process_messages_async(messages=messages)
    
    assert result.status.state == "completed"
    assert "rephrase" in result.status.message.parts[0].text.lower()


@pytest.mark.asyncio
async def test_process_messages_async_llm_error():
    """Test handling of LLM errors"""
    agent = StudlyAgent()
    
    messages = [
        A2AMessage(
            role="user",
            parts=[MessagePart(kind="text", text="Help me study")]
        )
    ]
    
    # Mock an LLM error
    with patch.object(agent.chain, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
        mock_ainvoke.side_effect = Exception("API Error")
        
        result = await agent.process_messages_async(messages=messages)
        
        assert result.status.state == "completed"
        assert "issue" in result.status.message.parts[0].text.lower()


@pytest.mark.asyncio
async def test_context_locking():
    """Test that context locking prevents race conditions"""
    agent = StudlyAgent()
    
    messages = [
        A2AMessage(
            role="user",
            parts=[MessagePart(kind="text", text=f"Request {i}")]
        )
    ]
    
    context_id = "test-context"
    
    # Mock the LLM call to be fast
    with patch.object(agent.chain, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
        mock_response = MagicMock()
        mock_response.content = "Study plan"
        mock_ainvoke.return_value = mock_response
        
        # Run multiple concurrent requests with the same context
        tasks = [
            agent.process_messages_async(
                messages=[A2AMessage(
                    role="user",
                    parts=[MessagePart(kind="text", text=f"Request {i}")]
                )],
                context_id=context_id
            )
            for i in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(r.status.state == "completed" for r in results)
        assert all(r.contextId == context_id for r in results)
        
        # Context should have accumulated all interactions
        assert len(agent.study_contexts[context_id]) == 5


@pytest.mark.asyncio
async def test_multiple_contexts_concurrent():
    """Test handling multiple contexts concurrently"""
    agent = StudlyAgent()
    
    # Mock the LLM call
    with patch.object(agent.chain, 'ainvoke', new_callable=AsyncMock) as mock_ainvoke:
        mock_response = MagicMock()
        mock_response.content = "Study plan"
        mock_ainvoke.return_value = mock_response
        
        # Create tasks for different contexts
        tasks = []
        for i in range(10):
            messages = [
                A2AMessage(
                    role="user",
                    parts=[MessagePart(kind="text", text=f"Learn topic {i}")]
                )
            ]
            task = agent.process_messages_async(
                messages=messages,
                context_id=f"context-{i}"
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert len(results) == 10
        assert all(r.status.state == "completed" for r in results)
        
        # Each context should have exactly one entry
        for i in range(10):
            assert f"context-{i}" in agent.study_contexts
            assert len(agent.study_contexts[f"context-{i}"]) == 1
