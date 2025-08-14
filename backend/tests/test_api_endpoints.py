import pytest
from fastapi.testclient import TestClient
import json


@pytest.mark.api
class TestAPIEndpoints:
    """Test suite for FastAPI endpoints"""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns welcome message"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "RAG System Test API"
    
    def test_query_endpoint_with_new_session(self, client):
        """Test /api/query endpoint creates new session when none provided"""
        query_data = {
            "query": "What is software testing?"
        }
        response = client.post("/api/query", json=query_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        
        # Check data types and content
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)
        assert data["answer"] == "Test response"
        assert len(data["sources"]) > 0
        
        # Check source structure
        source = data["sources"][0]
        assert "text" in source
        assert "link" in source
        assert source["text"] == "Test source"
        assert source["link"] == "http://test.com"
    
    def test_query_endpoint_with_existing_session(self, client):
        """Test /api/query endpoint uses provided session_id"""
        query_data = {
            "query": "Explain unit testing",
            "session_id": "existing_session_123"
        }
        response = client.post("/api/query", json=query_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "existing_session_123"
    
    def test_query_endpoint_missing_query(self, client):
        """Test /api/query endpoint returns 422 for missing query"""
        response = client.post("/api/query", json={})
        assert response.status_code == 422
    
    def test_query_endpoint_invalid_json(self, client):
        """Test /api/query endpoint handles invalid JSON"""
        response = client.post(
            "/api/query",
            data="invalid json",
            headers={"content-type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_courses_endpoint(self, client):
        """Test /api/courses endpoint returns course statistics"""
        response = client.get("/api/courses")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "total_courses" in data
        assert "course_titles" in data
        
        # Check data types and content from mock
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
        assert data["total_courses"] == 2
        assert len(data["course_titles"]) == 2
        assert "Test Course 1" in data["course_titles"]
        assert "Test Course 2" in data["course_titles"]
    
    def test_clear_session_endpoint(self, client):
        """Test /api/sessions/clear endpoint clears session"""
        clear_data = {
            "session_id": "test_session_to_clear"
        }
        response = client.post("/api/sessions/clear", json=clear_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "success" in data
        assert "message" in data
        
        # Check content
        assert data["success"] is True
        assert "cleared successfully" in data["message"]
        assert "test_session_to_clear" in data["message"]
    
    def test_clear_session_endpoint_missing_session_id(self, client):
        """Test /api/sessions/clear endpoint returns 422 for missing session_id"""
        response = client.post("/api/sessions/clear", json={})
        assert response.status_code == 422
    
    def test_nonexistent_endpoint(self, client):
        """Test accessing nonexistent endpoint returns 404"""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404


@pytest.mark.api
class TestAPIEndpointErrors:
    """Test suite for API endpoint error handling"""
    
    def test_query_endpoint_with_exception(self, client, mock_rag_system):
        """Test /api/query endpoint handles RAG system exceptions"""
        # Configure mock to raise exception
        mock_rag_system.query.side_effect = Exception("Test error")
        
        query_data = {"query": "test query"}
        response = client.post("/api/query", json=query_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Test error"
    
    def test_courses_endpoint_with_exception(self, client, mock_rag_system):
        """Test /api/courses endpoint handles RAG system exceptions"""
        # Configure mock to raise exception
        mock_rag_system.get_course_analytics.side_effect = Exception("Analytics error")
        
        response = client.get("/api/courses")
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Analytics error"
    
    def test_clear_session_endpoint_with_exception(self, client, mock_rag_system):
        """Test /api/sessions/clear endpoint handles session manager exceptions"""
        # Configure mock to raise exception
        mock_rag_system.session_manager.clear_session.side_effect = Exception("Session error")
        
        clear_data = {"session_id": "test_session"}
        response = client.post("/api/sessions/clear", json=clear_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert data["detail"] == "Session error"


@pytest.mark.api
class TestAPIDataValidation:
    """Test suite for API data validation"""
    
    def test_query_endpoint_empty_string_query(self, client):
        """Test /api/query endpoint handles empty string query"""
        query_data = {"query": ""}
        response = client.post("/api/query", json=query_data)
        
        # Should still work with empty query - the validation allows it
        assert response.status_code == 200
    
    def test_query_endpoint_very_long_query(self, client):
        """Test /api/query endpoint handles very long query"""
        long_query = "test " * 1000  # 5000 character query
        query_data = {"query": long_query}
        response = client.post("/api/query", json=query_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
    
    def test_query_endpoint_with_unicode(self, client):
        """Test /api/query endpoint handles Unicode characters"""
        query_data = {"query": "What is 测试? Explain αβγδε and 🚀🔥💯"}
        response = client.post("/api/query", json=query_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
    
    def test_clear_session_empty_session_id(self, client):
        """Test /api/sessions/clear endpoint handles empty session_id"""
        clear_data = {"session_id": ""}
        response = client.post("/api/sessions/clear", json=clear_data)
        
        # Should still work with empty session_id
        assert response.status_code == 200


@pytest.mark.api
class TestAPIResponseFormats:
    """Test suite for API response format consistency"""
    
    def test_query_response_with_string_sources(self, client, mock_rag_system):
        """Test /api/query handles legacy string source format"""
        # Configure mock to return string sources instead of dict
        mock_rag_system.query.return_value = ("Test answer", ["Source 1", "Source 2"])
        
        query_data = {"query": "test"}
        response = client.post("/api/query", json=query_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should convert string sources to SourceItem format
        assert len(data["sources"]) == 2
        assert data["sources"][0]["text"] == "Source 1"
        assert data["sources"][0]["link"] is None
        assert data["sources"][1]["text"] == "Source 2"
        assert data["sources"][1]["link"] is None
    
    def test_query_response_with_mixed_sources(self, client, mock_rag_system):
        """Test /api/query handles mixed source formats"""
        # Configure mock to return mixed source formats
        mixed_sources = [
            {"text": "Dict source", "link": "http://example.com"},
            "String source",
            {"text": "Dict without link"}
        ]
        mock_rag_system.query.return_value = ("Test answer", mixed_sources)
        
        query_data = {"query": "test"}
        response = client.post("/api/query", json=query_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should handle all source formats correctly
        assert len(data["sources"]) == 3
        assert data["sources"][0]["text"] == "Dict source"
        assert data["sources"][0]["link"] == "http://example.com"
        assert data["sources"][1]["text"] == "String source"
        assert data["sources"][1]["link"] is None
        assert data["sources"][2]["text"] == "Dict without link"
        assert data["sources"][2]["link"] is None