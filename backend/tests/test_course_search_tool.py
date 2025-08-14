import pytest
from unittest.mock import Mock, patch
from search_tools import CourseSearchTool
from vector_store import SearchResults


class TestCourseSearchTool:
    """Test suite for CourseSearchTool.execute() method"""

    def test_execute_basic_query_success(
        self, mock_vector_store, sample_search_results
    ):
        """Test basic query execution with successful results"""
        # Setup
        mock_vector_store.search.return_value = sample_search_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson/0"

        tool = CourseSearchTool(mock_vector_store)

        # Execute
        result = tool.execute("testing concepts")

        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="testing concepts", course_name=None, lesson_number=None
        )

        # Check result format includes course context
        assert "[Test Course for Unit Testing - Lesson 0]" in result
        assert "[Test Course for Unit Testing - Lesson 1]" in result
        assert "This is the introduction lesson content" in result
        assert "In this lesson we dive deeper" in result

    def test_execute_with_course_name_filter(
        self, mock_vector_store, sample_search_results
    ):
        """Test query execution with course name filter"""
        # Setup
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)

        # Execute
        result = tool.execute("testing concepts", course_name="Test Course")

        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="testing concepts", course_name="Test Course", lesson_number=None
        )

    def test_execute_with_lesson_number_filter(
        self, mock_vector_store, sample_search_results
    ):
        """Test query execution with lesson number filter"""
        # Setup
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)

        # Execute
        result = tool.execute("testing concepts", lesson_number=1)

        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="testing concepts", course_name=None, lesson_number=1
        )

    def test_execute_with_both_filters(self, mock_vector_store, sample_search_results):
        """Test query execution with both course name and lesson number filters"""
        # Setup
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)

        # Execute
        result = tool.execute(
            "testing concepts", course_name="Test Course", lesson_number=1
        )

        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="testing concepts", course_name="Test Course", lesson_number=1
        )

    def test_execute_empty_results(self, mock_vector_store, empty_search_results):
        """Test handling of empty search results"""
        # Setup
        mock_vector_store.search.return_value = empty_search_results
        tool = CourseSearchTool(mock_vector_store)

        # Execute
        result = tool.execute("nonexistent content")

        # Verify
        assert result == "No relevant content found."

    def test_execute_empty_results_with_course_filter(
        self, mock_vector_store, empty_search_results
    ):
        """Test handling of empty results with course filter"""
        # Setup
        mock_vector_store.search.return_value = empty_search_results
        tool = CourseSearchTool(mock_vector_store)

        # Execute
        result = tool.execute("nonexistent content", course_name="Test Course")

        # Verify
        assert result == "No relevant content found in course 'Test Course'."

    def test_execute_empty_results_with_lesson_filter(
        self, mock_vector_store, empty_search_results
    ):
        """Test handling of empty results with lesson filter"""
        # Setup
        mock_vector_store.search.return_value = empty_search_results
        tool = CourseSearchTool(mock_vector_store)

        # Execute
        result = tool.execute("nonexistent content", lesson_number=5)

        # Verify
        assert result == "No relevant content found in lesson 5."

    def test_execute_empty_results_with_both_filters(
        self, mock_vector_store, empty_search_results
    ):
        """Test handling of empty results with both filters"""
        # Setup
        mock_vector_store.search.return_value = empty_search_results
        tool = CourseSearchTool(mock_vector_store)

        # Execute
        result = tool.execute(
            "nonexistent content", course_name="Test Course", lesson_number=5
        )

        # Verify
        assert (
            result == "No relevant content found in course 'Test Course' in lesson 5."
        )

    def test_execute_search_error(self, mock_vector_store, error_search_results):
        """Test handling of search errors"""
        # Setup
        mock_vector_store.search.return_value = error_search_results
        tool = CourseSearchTool(mock_vector_store)

        # Execute
        result = tool.execute("test query")

        # Verify error is returned
        assert result == "Test error message"

    def test_format_results_with_lesson_links(self, mock_vector_store):
        """Test result formatting includes lesson links"""
        # Setup search results
        search_results = SearchResults(
            documents=["Test content"],
            metadata=[{"course_title": "Test Course", "lesson_number": 1}],
            distances=[0.1],
        )

        mock_vector_store.search.return_value = search_results
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson/1"

        tool = CourseSearchTool(mock_vector_store)

        # Execute
        result = tool.execute("test query")

        # Verify lesson link retrieval was called
        mock_vector_store.get_lesson_link.assert_called_once_with("Test Course", 1)

        # Verify sources are tracked
        assert len(tool.last_sources) == 1
        assert tool.last_sources[0]["text"] == "Test Course - Lesson 1"
        assert tool.last_sources[0]["link"] == "https://example.com/lesson/1"

    def test_format_results_without_lesson_number(self, mock_vector_store):
        """Test result formatting for content without lesson numbers"""
        # Setup search results without lesson number
        search_results = SearchResults(
            documents=["Test content without lesson"],
            metadata=[{"course_title": "Test Course"}],
            distances=[0.1],
        )

        mock_vector_store.search.return_value = search_results
        tool = CourseSearchTool(mock_vector_store)

        # Execute
        result = tool.execute("test query")

        # Verify format excludes lesson number
        assert "[Test Course]" in result
        assert "Test content without lesson" in result

        # Verify sources don't include lesson number
        assert len(tool.last_sources) == 1
        assert tool.last_sources[0]["text"] == "Test Course"
        assert tool.last_sources[0]["link"] is None

    def test_source_tracking_reset_between_searches(
        self, mock_vector_store, sample_search_results
    ):
        """Test that sources are properly managed between searches"""
        # Setup
        mock_vector_store.search.return_value = sample_search_results
        tool = CourseSearchTool(mock_vector_store)

        # First search
        tool.execute("first query")
        first_sources = tool.last_sources.copy()

        # Second search with different results
        single_result = SearchResults(
            documents=["Single result"],
            metadata=[{"course_title": "Another Course", "lesson_number": 3}],
            distances=[0.1],
        )
        mock_vector_store.search.return_value = single_result

        tool.execute("second query")

        # Verify sources are updated, not appended
        assert len(tool.last_sources) == 1
        assert tool.last_sources != first_sources
        assert tool.last_sources[0]["text"] == "Another Course - Lesson 3"

    def test_get_tool_definition(self, mock_vector_store):
        """Test that tool definition is correctly formatted"""
        tool = CourseSearchTool(mock_vector_store)
        definition = tool.get_tool_definition()

        # Verify structure
        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition

        # Verify schema properties
        schema = definition["input_schema"]
        assert schema["type"] == "object"
        assert "query" in schema["properties"]
        assert "course_name" in schema["properties"]
        assert "lesson_number" in schema["properties"]
        assert schema["required"] == ["query"]

    def test_execute_with_malformed_metadata(self, mock_vector_store):
        """Test handling of malformed metadata in search results"""
        # Setup search results with missing metadata fields
        malformed_results = SearchResults(
            documents=["Test content"], metadata=[{}], distances=[0.1]  # Empty metadata
        )

        mock_vector_store.search.return_value = malformed_results
        tool = CourseSearchTool(mock_vector_store)

        # Execute - should not crash
        result = tool.execute("test query")

        # Verify graceful handling
        assert "[unknown]" in result
        assert "Test content" in result
        assert len(tool.last_sources) == 1
        assert tool.last_sources[0]["text"] == "unknown"
