import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, List
from fastapi.testclient import TestClient
import tempfile
import shutil

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

# API Testing Fixtures

@pytest.fixture
def mock_rag_system():
    """Mock RAG system for API testing"""
    mock = Mock()
    mock.query = Mock(return_value=("Test response", [{"text": "Test source", "link": "http://test.com"}]))
    mock.get_course_analytics = Mock(return_value={"total_courses": 2, "course_titles": ["Test Course 1", "Test Course 2"]})
    mock.session_manager = Mock()
    mock.session_manager.create_session = Mock(return_value="test_session_id")
    mock.session_manager.clear_session = Mock()
    return mock

@pytest.fixture
def test_app(mock_rag_system):
    """FastAPI test application with mocked dependencies"""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from pydantic import BaseModel
    from typing import List, Optional
    
    # Create test app without static file mounting to avoid filesystem issues
    app = FastAPI(title="Course Materials RAG System - Test", root_path="")
    
    # Add middleware
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    
    # Pydantic models (copied from main app)
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class SourceItem(BaseModel):
        text: str
        link: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[SourceItem]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    class ClearSessionRequest(BaseModel):
        session_id: str

    class ClearSessionResponse(BaseModel):
        success: bool
        message: str
    
    # API endpoints with mocked RAG system
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()
            
            answer, sources = mock_rag_system.query(request.query, session_id)
            
            source_items = []
            for source in sources:
                if isinstance(source, dict):
                    source_items.append(SourceItem(text=source.get('text', ''), link=source.get('link')))
                else:
                    source_items.append(SourceItem(text=str(source), link=None))
            
            return QueryResponse(
                answer=answer,
                sources=source_items,
                session_id=session_id
            )
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/sessions/clear", response_model=ClearSessionResponse)
    async def clear_session(request: ClearSessionRequest):
        try:
            mock_rag_system.session_manager.clear_session(request.session_id)
            return ClearSessionResponse(
                success=True,
                message=f"Session {request.session_id} cleared successfully"
            )
        except Exception as e:
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/")
    async def root():
        return {"message": "RAG System Test API"}
    
    return app

@pytest.fixture
def client(test_app):
    """Test client for API endpoints"""
    return TestClient(test_app)

@pytest.fixture
def temp_docs_dir():
    """Temporary directory with test documents"""
    temp_dir = tempfile.mkdtemp()
    
    # Create a test document
    test_doc_path = os.path.join(temp_dir, "test_course.txt")
    with open(test_doc_path, "w", encoding="utf-8") as f:
        f.write("""Course Title: Test Course for API Testing
Course Link: https://example.com/test-course
Course Instructor: Test Instructor

Lesson 0: Introduction
Lesson Link: https://example.com/lesson/0
This is the introduction lesson content. It covers the basics of testing API endpoints.

Lesson 1: Advanced Topics
This lesson covers advanced API testing concepts including mocking and fixtures.
""")
    
    yield temp_dir
    shutil.rmtree(temp_dir)