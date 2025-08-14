import pytest
import sys
import os
from unittest.mock import Mock, MagicMock
from typing import Dict, Any, List

# Add the backend directory to the Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models import Course, Lesson, CourseChunk
from vector_store import SearchResults

# Test Configuration
pytest.main_config = {
    "testpaths": ["tests"],
    "python_files": ["test_*.py"],
    "python_classes": ["Test*"],
    "python_functions": ["test_*"]
}

# Sample Test Data Fixtures

@pytest.fixture
def sample_course():
    """Sample course data for testing"""
    lessons = [
        Lesson(lesson_number=0, title="Introduction to Testing", lesson_link="https://example.com/lesson/0"),
        Lesson(lesson_number=1, title="Advanced Testing Concepts", lesson_link="https://example.com/lesson/1"),
        Lesson(lesson_number=2, title="Testing in Practice", lesson_link=None)
    ]
    return Course(
        title="Test Course for Unit Testing",
        course_link="https://example.com/test-course", 
        instructor="Test Instructor",
        lessons=lessons
    )

@pytest.fixture
def sample_course_chunks():
    """Sample course chunks for testing"""
    return [
        CourseChunk(
            content="This is the introduction lesson content. It covers the basics of software testing including unit tests, integration tests, and system testing.",
            course_title="Test Course for Unit Testing",
            lesson_number=0,
            chunk_index=0
        ),
        CourseChunk(
            content="In this lesson we dive deeper into advanced testing concepts such as mocking, test doubles, and behavior driven development.",
            course_title="Test Course for Unit Testing",
            lesson_number=1,
            chunk_index=1
        ),
        CourseChunk(
            content="This lesson content shows how to apply testing concepts in real-world scenarios. We discuss continuous integration, automated testing pipelines.",
            course_title="Test Course for Unit Testing",
            lesson_number=2,
            chunk_index=2
        )
    ]

@pytest.fixture
def sample_search_results():
    """Sample search results for testing"""
    return SearchResults(
        documents=[
            "This is the introduction lesson content. It covers the basics of software testing including unit tests, integration tests, and system testing.",
            "In this lesson we dive deeper into advanced testing concepts such as mocking, test doubles, and behavior driven development."
        ],
        metadata=[
            {"course_title": "Test Course for Unit Testing", "lesson_number": 0},
            {"course_title": "Test Course for Unit Testing", "lesson_number": 1}
        ],
        distances=[0.2, 0.4]
    )

@pytest.fixture
def empty_search_results():
    """Empty search results for testing"""
    return SearchResults(
        documents=[],
        metadata=[],
        distances=[]
    )

@pytest.fixture
def error_search_results():
    """Search results with error for testing"""
    return SearchResults.empty("Test error message")

# Mock Fixtures

@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing"""
    mock = Mock()
    mock.search = Mock()
    mock.get_lesson_link = Mock()
    mock._resolve_course_name = Mock()
    mock.course_catalog = Mock()
    return mock

@pytest.fixture 
def mock_anthropic_client():
    """Mock Anthropic client for testing"""
    mock = Mock()
    mock.messages = Mock()
    mock.messages.create = Mock()
    return mock

@pytest.fixture
def mock_anthropic_response():
    """Mock Anthropic API response for testing"""
    mock_response = Mock()
    mock_response.content = [Mock()]
    mock_response.content[0].text = "Test AI response"
    mock_response.stop_reason = "end_turn"
    return mock_response

@pytest.fixture
def mock_anthropic_tool_response():
    """Mock Anthropic API response with tool use"""
    mock_response = Mock()
    mock_content_block = Mock()
    mock_content_block.type = "tool_use"
    mock_content_block.name = "search_course_content"
    mock_content_block.input = {"query": "test query"}
    mock_content_block.id = "test_tool_id"
    
    mock_response.content = [mock_content_block]
    mock_response.stop_reason = "tool_use"
    return mock_response

@pytest.fixture
def mock_tool_manager():
    """Mock tool manager for testing"""
    mock = Mock()
    mock.get_tool_definitions = Mock(return_value=[])
    mock.execute_tool = Mock(return_value="Mock tool result")
    mock.get_last_sources = Mock(return_value=[])
    mock.reset_sources = Mock()
    return mock

@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    mock = Mock()
    mock.CHUNK_SIZE = 800
    mock.CHUNK_OVERLAP = 100
    mock.MAX_RESULTS = 5
    mock.ANTHROPIC_API_KEY = "test_api_key"
    mock.ANTHROPIC_MODEL = "test-model"
    mock.EMBEDDING_MODEL = "test-embedding-model"
    mock.CHROMA_PATH = "./test_chroma_db"
    mock.MAX_HISTORY = 2
    return mock