"""
Unit tests for history trimming and summarization functionality.
"""

import unittest
from unittest.mock import patch, MagicMock
from typing import List
from models.a2a import A2AMessage, MessagePart
from utils import normalize_telex_message, strip_html_and_whitespace
from agents.agent import StudlyAgent
from config import HISTORY_CAP_MESSAGES, SUMMARY_THRESHOLD


class TestHTMLStripping(unittest.TestCase):
    """Tests for HTML stripping and whitespace normalization."""
    
    def test_strip_html_tags(self):
        """Test that HTML tags are properly stripped."""
        text = "<p>Hello <b>world</b></p>"
        result = strip_html_and_whitespace(text)
        self.assertEqual(result, "Hello world")
    
    def test_strip_html_entities(self):
        """Test that HTML entities are decoded."""
        text = "Hello&nbsp;world&amp;test"
        result = strip_html_and_whitespace(text)
        self.assertEqual(result, "Hello world&test")
    
    def test_normalize_whitespace(self):
        """Test that whitespace is normalized."""
        text = "Hello    world\n\n\ntest"
        result = strip_html_and_whitespace(text)
        self.assertEqual(result, "Hello world test")
    
    def test_complex_html(self):
        """Test with complex HTML markup."""
        text = "<div><p>Test <br />message</p><ul><li>Item</li></ul></div>"
        result = strip_html_and_whitespace(text)
        self.assertNotIn("<", result)
        self.assertNotIn(">", result)


class TestNormalizeMessage(unittest.TestCase):
    """Tests for message normalization with history capping."""
    
    def test_empty_message(self):
        """Test handling of empty message."""
        result = normalize_telex_message({})
        self.assertEqual(result, [])
    
    def test_query_only(self):
        """Test message with only a query, no history."""
        raw_message = {
            'parts': [
                {'kind': 'text', 'text': 'How do I learn Python?'}
            ]
        }
        result = normalize_telex_message(raw_message)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].role, 'user')
        self.assertEqual(result[0].parts[0].text, 'How do I learn Python?')
    
    def test_history_capping(self):
        """Test that history is capped to configured limit."""
        # Create a message with lots of history
        history_items = [
            {'kind': 'text', 'text': f'Message {i}'}
            for i in range(20)  # 20 history items
        ]
        
        raw_message = {
            'parts': [
                {'kind': 'text', 'text': 'Current query'},
                {'kind': 'data', 'data': history_items}
            ]
        }
        
        result = normalize_telex_message(raw_message)
        
        # Should be capped: at most HISTORY_CAP_MESSAGES
        self.assertLessEqual(len(result), HISTORY_CAP_MESSAGES)
        
        # Last message should be the current query
        self.assertEqual(result[-1].parts[0].text, 'Current query')
    
    def test_custom_history_cap(self):
        """Test that custom history cap is respected."""
        history_items = [
            {'kind': 'text', 'text': f'Message {i}'}
            for i in range(10)
        ]
        
        raw_message = {
            'parts': [
                {'kind': 'text', 'text': 'Current query'},
                {'kind': 'data', 'data': history_items}
            ]
        }
        
        custom_cap = 4
        result = normalize_telex_message(raw_message, history_cap=custom_cap)
        
        self.assertLessEqual(len(result), custom_cap)
    
    def test_html_stripping_in_messages(self):
        """Test that HTML is stripped from messages during normalization."""
        raw_message = {
            'parts': [
                {'kind': 'text', 'text': '<p>Test <b>query</b></p>'},
                {'kind': 'data', 'data': [
                    {'kind': 'text', 'text': '<p>History <br />item</p>'}
                ]}
            ]
        }
        
        result = normalize_telex_message(raw_message)
        
        # Check that HTML tags are removed
        for msg in result:
            text = msg.parts[0].text
            self.assertNotIn('<p>', text)
            self.assertNotIn('<b>', text)
            self.assertNotIn('<br />', text)
    
    def test_alternating_roles(self):
        """Test that history messages have alternating roles."""
        history_items = [
            {'kind': 'text', 'text': f'Message {i}'}
            for i in range(6)
        ]
        
        raw_message = {
            'parts': [
                {'kind': 'text', 'text': 'Current query'},
                {'kind': 'data', 'data': history_items}
            ]
        }
        
        result = normalize_telex_message(raw_message)
        
        # Check alternating roles (excluding last message which is the query)
        history_msgs = result[:-1]
        for i, msg in enumerate(history_msgs):
            expected_role = 'user' if i % 2 == 0 else 'agent'
            self.assertEqual(msg.role, expected_role)


class TestStudlyAgentSummarization(unittest.TestCase):
    """Tests for summarization and caching in StudlyAgent."""
    
    def setUp(self):
        """Set up test agent."""
        self.agent = StudlyAgent()
    
    def test_no_history_context(self):
        """Test context preparation with no history."""
        messages = [
            A2AMessage(role="user", parts=[MessagePart(kind="text", text="Test query")])
        ]
        
        context = self.agent._prepare_context(messages, "test-context")
        self.assertIn("No previous", context)
    
    @patch('agents.agent.ENABLE_SUMMARIZATION', True)
    @patch('agents.agent.SUMMARY_THRESHOLD', 3)
    def test_summarization_triggered(self):
        """Test that summarization is triggered when history exceeds threshold."""
        messages = [
            A2AMessage(role="user", parts=[MessagePart(kind="text", text="First query")]),
            A2AMessage(role="agent", parts=[MessagePart(kind="text", text="First response")]),
            A2AMessage(role="user", parts=[MessagePart(kind="text", text="Second query")]),
            A2AMessage(role="agent", parts=[MessagePart(kind="text", text="Second response")]),
            A2AMessage(role="user", parts=[MessagePart(kind="text", text="Current query")])
        ]
        
        # Mock the _generate_summary method instead
        with patch.object(self.agent, '_generate_summary', return_value="Summary of conversation"):
            context = self.agent._prepare_context(messages, "test-context")
            
            # Should use summary
            self.assertIn("Summary", context)
    
    @patch('agents.agent.ENABLE_SUMMARIZATION', False)
    def test_summarization_disabled(self):
        """Test that summarization is skipped when disabled."""
        messages = [
            A2AMessage(role="user", parts=[MessagePart(kind="text", text="First query")]),
            A2AMessage(role="agent", parts=[MessagePart(kind="text", text="First response")]),
            A2AMessage(role="user", parts=[MessagePart(kind="text", text="Current query")])
        ]
        
        context = self.agent._prepare_context(messages, "test-context")
        
        # Should use raw history, not summary
        self.assertIn("Recent conversation", context)
    
    def test_summary_caching(self):
        """Test that summaries are cached per context."""
        messages = [
            A2AMessage(role="user", parts=[MessagePart(kind="text", text=f"Query {i}")])
            for i in range(10)
        ]
        
        context_id = "test-context"
        
        with patch('agents.agent.ENABLE_SUMMARIZATION', True), \
             patch('agents.agent.SUMMARY_THRESHOLD', 3), \
             patch.object(self.agent, '_generate_summary', return_value="Cached summary") as mock_gen:
            
            # First call should generate summary
            context1 = self.agent._prepare_context(messages, context_id)
            self.assertIn("Cached summary", context1)
            
            # Second call should use cached summary
            context2 = self.agent._prepare_context(messages, context_id)
            self.assertIn("Cached summary", context2)
            
            # Should only call summary generation once
            self.assertEqual(mock_gen.call_count, 1)
    
    def test_history_capping_in_result(self):
        """Test that returned history is capped in TaskResult."""
        # Create messages exceeding the cap
        messages = [
            A2AMessage(role="user" if i % 2 == 0 else "agent", 
                      parts=[MessagePart(kind="text", text=f"Message {i}")])
            for i in range(20)
        ]
        
        # Mock LLM response
        with patch.object(self.agent, '_generate_study_plan', return_value="Study plan"):
            result = self.agent.process_messages(messages, context_id="test", task_id="test")
            
            # History in result should be capped
            self.assertLessEqual(len(result.history), HISTORY_CAP_MESSAGES)
    
    def test_message_cache_enabled(self):
        """Test that message caching works when enabled."""
        messages = [
            A2AMessage(role="user", parts=[MessagePart(kind="text", text="Test query")])
        ]
        
        context_id = "test-context"
        
        # Mock LLM response
        with patch('agents.agent.ENABLE_HISTORY_CACHE', True), \
             patch.object(self.agent, '_generate_study_plan', return_value="Study plan"):
            self.agent.process_messages(messages, context_id=context_id, task_id="test")
            
            # Check that messages are cached
            self.assertIn(context_id, self.agent.context_last_messages)
            self.assertEqual(self.agent.context_last_messages[context_id], messages)


class TestEndToEndHistoryTrimming(unittest.TestCase):
    """End-to-end tests for the complete history trimming pipeline."""
    
    def setUp(self):
        """Set up test agent."""
        self.agent = StudlyAgent()
    
    def test_large_telex_payload(self):
        """Test handling of large Telex payload with history trimming."""
        # Simulate a large Telex payload
        history_items = [
            {'kind': 'text', 'text': f'<p>History message {i} with <b>HTML</b></p>'}
            for i in range(50)
        ]
        
        raw_message = {
            'parts': [
                {'kind': 'text', 'text': '<p>Current study query</p>'},
                {'kind': 'data', 'data': history_items}
            ]
        }
        
        # Normalize the message
        messages = normalize_telex_message(raw_message)
        
        # Should be capped
        self.assertLessEqual(len(messages), HISTORY_CAP_MESSAGES)
        
        # HTML should be stripped
        for msg in messages:
            text = msg.parts[0].text
            self.assertNotIn('<p>', text)
            self.assertNotIn('<b>', text)
    
    def test_process_with_trimmed_history(self):
        """Test processing messages with trimmed history."""
        # Create a large history
        history_items = [
            {'kind': 'text', 'text': f'Message {i}'}
            for i in range(30)
        ]
        
        raw_message = {
            'parts': [
                {'kind': 'text', 'text': 'Help me study Python'},
                {'kind': 'data', 'data': history_items}
            ]
        }
        
        messages = normalize_telex_message(raw_message)
        
        # Mock LLM response
        with patch.object(self.agent, '_generate_study_plan', return_value="Here's your study plan..."):
            result = self.agent.process_messages(messages, context_id="test", task_id="test")
            
            # Result should be successful
            self.assertEqual(result.status.state, "completed")
            self.assertIsNotNone(result.status.message)
            
            # History should be capped
            self.assertLessEqual(len(result.history), HISTORY_CAP_MESSAGES)


if __name__ == '__main__':
    unittest.main()
