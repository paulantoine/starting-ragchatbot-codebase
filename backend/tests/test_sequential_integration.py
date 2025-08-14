import pytest
from unittest.mock import Mock, patch
from ai_generator import AIGenerator


class TestSequentialToolIntegration:
    """Integration tests for sequential tool calling scenarios"""

    # Removed ai_generator fixture - will create it in each test with proper mocking

    @pytest.fixture
    def mock_tool_manager(self):
        """Create mock tool manager with realistic responses"""
        manager = Mock()

        # Mock responses for different tool calls
        def execute_tool_side_effect(tool_name, **kwargs):
            if tool_name == "get_course_outline":
                if kwargs.get("course_name") == "Machine Learning Fundamentals":
                    return """Course: Machine Learning Fundamentals
Instructor: Dr. Smith

Lesson 0: Introduction to ML
Lesson 1: Data Preprocessing  
Lesson 2: Supervised Learning
Lesson 3: Unsupervised Learning
Lesson 4: Neural Networks and Deep Learning
Lesson 5: Model Evaluation
"""
                return "Course not found"

            elif tool_name == "search_course_content":
                query = kwargs.get("query", "")
                if (
                    "neural networks" in query.lower()
                    or "deep learning" in query.lower()
                ):
                    return """Found relevant courses:
- Advanced Deep Learning (Instructor: Prof. Johnson)
  - Covers neural network architectures, backpropagation, CNNs, RNNs
  - Lesson 2: Deep Neural Networks focuses on multi-layer perceptrons
  - Lesson 3: Convolutional Neural Networks for image processing
  
- Artificial Intelligence Concepts (Instructor: Dr. Lee)  
  - Lesson 6: Introduction to Neural Networks
  - Covers basic perceptron, activation functions, gradient descent
"""
                return "No relevant content found"

            return "Tool execution error"

        manager.execute_tool.side_effect = execute_tool_side_effect
        return manager

    @patch("anthropic.Anthropic")
    def test_complex_course_comparison_scenario(
        self, mock_anthropic_class, mock_tool_manager
    ):
        """
        Test complex scenario: 'Find a course that discusses the same topic as lesson 4 of Machine Learning Fundamentals'

        Expected flow:
        1. Get outline of 'Machine Learning Fundamentals' to find what lesson 4 covers
        2. Search for courses that discuss neural networks/deep learning
        3. Synthesize comparison results
        """
        # Setup mock client
        mock_client = Mock()

        # Round 1: Claude gets course outline
        first_response = Mock()
        first_response.stop_reason = "tool_use"
        first_tool_block = Mock()
        first_tool_block.type = "tool_use"
        first_tool_block.name = "get_course_outline"
        first_tool_block.input = {"course_name": "Machine Learning Fundamentals"}
        first_tool_block.id = "tool_1"
        first_response.content = [first_tool_block]

        # Round 2: Claude searches for related courses
        second_response = Mock()
        second_response.stop_reason = "tool_use"
        second_tool_block = Mock()
        second_tool_block.type = "tool_use"
        second_tool_block.name = "search_course_content"
        second_tool_block.input = {"query": "neural networks deep learning"}
        second_tool_block.id = "tool_2"
        second_response.content = [second_tool_block]

        # Final synthesis
        final_response = Mock()
        final_response.content = [Mock()]
        final_response.content[
            0
        ].text = """Based on the course outline, lesson 4 of Machine Learning Fundamentals covers "Neural Networks and Deep Learning". 

I found two courses that discuss the same topic:

1. **Advanced Deep Learning** (Prof. Johnson) - This course has dedicated lessons on neural network architectures and deep learning concepts, making it highly relevant to lesson 4's content.

2. **Artificial Intelligence Concepts** (Dr. Lee) - Lesson 6 covers "Introduction to Neural Networks" which overlaps with the neural networks portion of lesson 4.

Advanced Deep Learning would be the most similar course as it focuses specifically on the deep learning concepts covered in lesson 4."""

        # Configure mock client
        mock_client.messages.create.side_effect = [
            first_response,
            second_response,
            final_response,
        ]
        mock_anthropic_class.return_value = mock_client

        # Create AIGenerator instance with mocked client
        ai_generator = AIGenerator("test_api_key", "test-model")

        tools = [
            {"name": "get_course_outline", "description": "Get course overview"},
            {"name": "search_course_content", "description": "Search course content"},
        ]

        # Execute the complex query
        result = ai_generator.generate_response(
            "Find a course that discusses the same topic as lesson 4 of Machine Learning Fundamentals",
            tools=tools,
            tool_manager=mock_tool_manager,
        )

        # Verify the complete workflow
        assert mock_client.messages.create.call_count == 3
        assert mock_tool_manager.execute_tool.call_count == 2

        # Verify first tool call got course outline
        mock_tool_manager.execute_tool.assert_any_call(
            "get_course_outline", course_name="Machine Learning Fundamentals"
        )

        # Verify second tool call searched for neural networks content
        mock_tool_manager.execute_tool.assert_any_call(
            "search_course_content", query="neural networks deep learning"
        )

        # Verify final result contains meaningful comparison
        assert "Neural Networks and Deep Learning" in result
        assert "Advanced Deep Learning" in result
        assert "Prof. Johnson" in result
        assert "most similar course" in result

    @patch("anthropic.Anthropic")
    def test_multi_course_comparison_scenario(
        self, mock_anthropic_class, mock_tool_manager
    ):
        """
        Test scenario requiring comparison across multiple courses
        """
        # Setup mock client
        mock_client = Mock()

        # Round 1: Search for machine learning courses
        first_response = Mock()
        first_response.stop_reason = "tool_use"
        first_tool_block = Mock()
        first_tool_block.type = "tool_use"
        first_tool_block.name = "search_course_content"
        first_tool_block.input = {"query": "machine learning algorithms"}
        first_tool_block.id = "tool_1"
        first_response.content = [first_tool_block]

        # Round 2: Get outline of specific course
        second_response = Mock()
        second_response.stop_reason = "tool_use"
        second_tool_block = Mock()
        second_tool_block.type = "tool_use"
        second_tool_block.name = "get_course_outline"
        second_tool_block.input = {"course_name": "Advanced Deep Learning"}
        second_tool_block.id = "tool_2"
        second_response.content = [second_tool_block]

        # Final response
        final_response = Mock()
        final_response.content = [Mock()]
        final_response.content[0].text = (
            "Comprehensive comparison of machine learning courses based on search and outline results."
        )

        mock_client.messages.create.side_effect = [
            first_response,
            second_response,
            final_response,
        ]
        mock_anthropic_class.return_value = mock_client

        # Create AIGenerator instance with mocked client
        ai_generator = AIGenerator("test_api_key", "test-model")

        tools = [
            {"name": "get_course_outline", "description": "Get course overview"},
            {"name": "search_course_content", "description": "Search course content"},
        ]

        # Execute
        result = ai_generator.generate_response(
            "Compare the machine learning courses and give me details about Advanced Deep Learning",
            tools=tools,
            tool_manager=mock_tool_manager,
        )

        # Verify sequential execution with different tool types
        assert mock_client.messages.create.call_count == 3
        assert mock_tool_manager.execute_tool.call_count == 2

        # Verify mixed tool usage
        calls = mock_tool_manager.execute_tool.call_args_list
        assert calls[0][0] == ("search_course_content",)
        assert calls[1][0] == ("get_course_outline",)

        assert (
            result
            == "Comprehensive comparison of machine learning courses based on search and outline results."
        )

    @patch("anthropic.Anthropic")
    def test_progressive_refinement_scenario(
        self, mock_anthropic_class, mock_tool_manager
    ):
        """
        Test progressive refinement: broad search → specific outline → detailed content
        """
        mock_client = Mock()

        # Round 1: Broad search
        first_response = Mock()
        first_response.stop_reason = "tool_use"
        first_tool_block = Mock()
        first_tool_block.type = "tool_use"
        first_tool_block.name = "search_course_content"
        first_tool_block.input = {"query": "data science"}
        first_tool_block.id = "tool_1"
        first_response.content = [first_tool_block]

        # Round 2: Early termination - Claude has enough info
        second_response = Mock()
        second_response.stop_reason = "stop"
        second_response.content = [Mock()]
        second_response.content[0].text = (
            "Based on the search, here are the available data science courses with their key topics."
        )

        mock_client.messages.create.side_effect = [first_response, second_response]
        mock_anthropic_class.return_value = mock_client

        # Create AIGenerator instance with mocked client
        ai_generator = AIGenerator("test_api_key", "test-model")

        tools = [{"name": "search_course_content"}, {"name": "get_course_outline"}]

        # Execute
        result = ai_generator.generate_response(
            "What data science courses are available?",
            tools=tools,
            tool_manager=mock_tool_manager,
        )

        # Verify early termination works correctly
        assert (
            mock_client.messages.create.call_count == 2
        )  # Stopped after first round + response
        assert mock_tool_manager.execute_tool.call_count == 1
        assert "data science courses" in result

    @patch("anthropic.Anthropic")
    def test_error_recovery_in_multi_round_scenario(self, mock_anthropic_class):
        """Test error recovery when first tool call fails but system continues gracefully"""
        # Create failing tool manager
        failing_tool_manager = Mock()
        failing_tool_manager.execute_tool.return_value = None  # Simulate failure

        mock_client = Mock()

        # Claude tries to use tools but they fail
        tool_response = Mock()
        tool_response.stop_reason = "tool_use"
        tool_block = Mock()
        tool_block.type = "tool_use"
        tool_block.name = "search_course_content"
        tool_block.input = {"query": "test"}
        tool_block.id = "tool_1"
        tool_response.content = [tool_block, Mock()]
        tool_response.content[0].text = "I'll search for course information."

        mock_client.messages.create.return_value = tool_response
        mock_anthropic_class.return_value = mock_client

        # Create AIGenerator instance with mocked client
        ai_generator = AIGenerator("test_api_key", "test-model")

        tools = [{"name": "search_course_content"}]

        # Execute with failing tools
        result = ai_generator.generate_response(
            "Find me course information", tools=tools, tool_manager=failing_tool_manager
        )

        # Verify graceful failure handling
        assert mock_client.messages.create.call_count == 1
        assert failing_tool_manager.execute_tool.call_count == 1
        assert result == "I'll search for course information."
