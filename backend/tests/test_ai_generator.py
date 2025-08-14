import pytest
from unittest.mock import Mock, patch, MagicMock
from ai_generator import AIGenerator


class TestAIGenerator:
    """Test suite for AI generator tool calling functionality"""

    @pytest.fixture
    def ai_generator(self):
        """Create AIGenerator instance for testing"""
        return AIGenerator("test_api_key", "test-model")

    def test_init_sets_correct_attributes(self, ai_generator):
        """Test that AIGenerator initializes with correct attributes"""
        assert ai_generator.model == "test-model"
        assert ai_generator.base_params["model"] == "test-model"
        assert ai_generator.base_params["temperature"] == 0
        assert ai_generator.base_params["max_tokens"] == 800

    @patch('anthropic.Anthropic')
    def test_generate_response_without_tools(self, mock_anthropic_class, mock_anthropic_response):
        """Test basic response generation without tool usage"""
        # Setup mock client
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_anthropic_class.return_value = mock_client
        
        ai_generator = AIGenerator("test_api_key", "test-model")
        
        # Execute
        result = ai_generator.generate_response("What is machine learning?")
        
        # Verify
        assert result == "Test AI response"
        mock_client.messages.create.assert_called_once()
        
        # Verify call parameters
        call_args = mock_client.messages.create.call_args[1]
        assert call_args["model"] == "test-model"
        assert call_args["messages"][0]["content"] == "What is machine learning?"
        assert "tools" not in call_args

    @patch('anthropic.Anthropic')
    def test_generate_response_with_conversation_history(self, mock_anthropic_class, mock_anthropic_response):
        """Test response generation includes conversation history in system prompt"""
        # Setup
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_anthropic_class.return_value = mock_client
        
        ai_generator = AIGenerator("test_api_key", "test-model")
        history = "User: Previous question\nAssistant: Previous answer"
        
        # Execute
        result = ai_generator.generate_response("Follow up question", conversation_history=history)
        
        # Verify history is included in system prompt
        call_args = mock_client.messages.create.call_args[1]
        system_content = call_args["system"]
        assert "Previous conversation:" in system_content
        assert "Previous question" in system_content

    @patch('anthropic.Anthropic')
    def test_generate_response_with_tools_no_tool_use(self, mock_anthropic_class, mock_anthropic_response, mock_tool_manager):
        """Test response generation with tools available but no tool use triggered"""
        # Setup
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_anthropic_class.return_value = mock_client
        
        ai_generator = AIGenerator("test_api_key", "test-model")
        tools = [{"name": "search_course_content", "description": "Search courses"}]
        
        # Execute
        result = ai_generator.generate_response(
            "What is the capital of France?",
            tools=tools,
            tool_manager=mock_tool_manager
        )
        
        # Verify tools were provided but not used
        call_args = mock_client.messages.create.call_args[1]
        assert "tools" in call_args
        assert call_args["tools"] == tools
        assert call_args["tool_choice"] == {"type": "auto"}
        assert result == "Test AI response"

    @patch('anthropic.Anthropic')
    def test_generate_response_with_tool_use(self, mock_anthropic_class, mock_anthropic_tool_response, mock_tool_manager):
        """Test response generation with tool usage workflow"""
        # Setup initial tool response
        mock_client = Mock()
        
        # Mock final response after tool execution  
        final_response = Mock()
        final_response.content = [Mock()]
        final_response.content[0].text = "Based on the search results, here is the answer."
        
        # Configure client to return tool response first, then final response
        mock_client.messages.create.side_effect = [mock_anthropic_tool_response, final_response]
        mock_anthropic_class.return_value = mock_client
        
        # Configure tool manager
        mock_tool_manager.execute_tool.return_value = "Search results content"
        
        ai_generator = AIGenerator("test_api_key", "test-model")
        tools = [{"name": "search_course_content", "description": "Search courses"}]
        
        # Execute
        result = ai_generator.generate_response(
            "What does the course say about testing?",
            tools=tools,
            tool_manager=mock_tool_manager
        )
        
        # Verify tool execution workflow
        assert mock_client.messages.create.call_count == 2
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="test query"
        )
        assert result == "Based on the search results, here is the answer."

    @patch('anthropic.Anthropic')
    def test_handle_tool_execution_builds_correct_messages(self, mock_anthropic_class, mock_anthropic_tool_response, mock_tool_manager):
        """Test that tool execution builds correct message sequence"""
        # Setup
        mock_client = Mock()
        final_response = Mock()
        final_response.content = [Mock()]
        final_response.content[0].text = "Final answer"
        
        mock_client.messages.create.side_effect = [mock_anthropic_tool_response, final_response]
        mock_anthropic_class.return_value = mock_client
        mock_tool_manager.execute_tool.return_value = "Tool execution result"
        
        ai_generator = AIGenerator("test_api_key", "test-model")
        tools = [{"name": "search_course_content"}]
        
        # Execute
        ai_generator.generate_response(
            "Search query",
            tools=tools, 
            tool_manager=mock_tool_manager
        )
        
        # Verify second call includes proper message sequence
        second_call_args = mock_client.messages.create.call_args_list[1][1]
        messages = second_call_args["messages"]
        
        # Should have: original user message, assistant tool use, user tool results
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Search query"
        assert messages[1]["role"] == "assistant" 
        assert messages[2]["role"] == "user"
        assert messages[2]["content"][0]["type"] == "tool_result"

    @patch('anthropic.Anthropic') 
    def test_handle_multiple_tool_calls(self, mock_anthropic_class, mock_tool_manager):
        """Test handling of multiple tool calls in single response"""
        # Setup response with multiple tool calls
        mock_client = Mock()
        
        # Create mock response with multiple tool uses
        tool_response = Mock()
        tool_response.stop_reason = "tool_use"
        
        tool_block1 = Mock()
        tool_block1.type = "tool_use"
        tool_block1.name = "search_course_content"
        tool_block1.input = {"query": "first query"}
        tool_block1.id = "tool_1"
        
        tool_block2 = Mock()
        tool_block2.type = "tool_use"
        tool_block2.name = "get_course_outline"
        tool_block2.input = {"course_name": "test course"}
        tool_block2.id = "tool_2"
        
        tool_response.content = [tool_block1, tool_block2]
        
        final_response = Mock()
        final_response.content = [Mock()]
        final_response.content[0].text = "Combined results answer"
        
        mock_client.messages.create.side_effect = [tool_response, final_response]
        mock_anthropic_class.return_value = mock_client
        
        # Configure tool manager for multiple calls
        mock_tool_manager.execute_tool.side_effect = ["Result 1", "Result 2"]
        
        ai_generator = AIGenerator("test_api_key", "test-model")
        tools = [{"name": "search_course_content"}, {"name": "get_course_outline"}]
        
        # Execute
        result = ai_generator.generate_response(
            "Complex query",
            tools=tools,
            tool_manager=mock_tool_manager
        )
        
        # Verify multiple tool executions
        assert mock_tool_manager.execute_tool.call_count == 2
        mock_tool_manager.execute_tool.assert_any_call("search_course_content", query="first query")
        mock_tool_manager.execute_tool.assert_any_call("get_course_outline", course_name="test course")
        
        # Verify final message contains both tool results
        second_call_args = mock_client.messages.create.call_args_list[1][1]
        tool_results = second_call_args["messages"][2]["content"]
        assert len(tool_results) == 2
        assert tool_results[0]["tool_use_id"] == "tool_1"
        assert tool_results[1]["tool_use_id"] == "tool_2"

    @patch('anthropic.Anthropic')
    def test_tool_execution_error_handling(self, mock_anthropic_class, mock_anthropic_tool_response, mock_tool_manager):
        """Test handling of tool execution errors"""
        # Setup
        mock_client = Mock()
        final_response = Mock()
        final_response.content = [Mock()]
        final_response.content[0].text = "Error handled response"
        
        mock_client.messages.create.side_effect = [mock_anthropic_tool_response, final_response]
        mock_anthropic_class.return_value = mock_client
        
        # Tool manager returns error
        mock_tool_manager.execute_tool.return_value = "Tool execution failed: Database error"
        
        ai_generator = AIGenerator("test_api_key", "test-model")
        tools = [{"name": "search_course_content"}]
        
        # Execute - should not crash
        result = ai_generator.generate_response(
            "Search query",
            tools=tools,
            tool_manager=mock_tool_manager
        )
        
        # Verify error is passed to second API call
        second_call_args = mock_client.messages.create.call_args_list[1][1]
        tool_result = second_call_args["messages"][2]["content"][0]
        assert "Tool execution failed: Database error" in tool_result["content"]
        assert result == "Error handled response"

    @patch('anthropic.Anthropic')
    def test_system_prompt_contains_tool_guidelines(self, mock_anthropic_class, mock_anthropic_response):
        """Test that system prompt includes proper tool usage guidelines"""
        # Setup
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_anthropic_class.return_value = mock_client
        
        ai_generator = AIGenerator("test_api_key", "test-model")
        
        # Execute
        ai_generator.generate_response("Test query")
        
        # Verify system prompt content
        call_args = mock_client.messages.create.call_args[1]
        system_prompt = call_args["system"]
        
        # Check for key tool usage guidelines
        assert "search_course_content" in system_prompt
        assert "get_course_outline" in system_prompt
        assert "One tool use per query maximum" in system_prompt
        assert "Course-specific content questions" in system_prompt

    @patch('anthropic.Anthropic')
    def test_temperature_and_tokens_configuration(self, mock_anthropic_class, mock_anthropic_response):
        """Test that temperature and max_tokens are correctly configured"""
        # Setup
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_anthropic_class.return_value = mock_client
        
        ai_generator = AIGenerator("test_api_key", "test-model")
        
        # Execute
        ai_generator.generate_response("Test query")
        
        # Verify configuration
        call_args = mock_client.messages.create.call_args[1]
        assert call_args["temperature"] == 0  # Deterministic responses
        assert call_args["max_tokens"] == 800  # Reasonable limit