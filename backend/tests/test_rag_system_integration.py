import pytest
from unittest.mock import Mock, patch, MagicMock
import os
from rag_system import RAGSystem


class TestRAGSystemIntegration:
    """Integration test suite for RAG system end-to-end workflows"""

    @pytest.fixture
    def rag_system(self, mock_config):
        """Create RAGSystem instance with mocked dependencies"""
        with (
            patch("rag_system.DocumentProcessor"),
            patch("rag_system.VectorStore"),
            patch("rag_system.AIGenerator"),
            patch("rag_system.SessionManager"),
            patch("rag_system.ToolManager"),
            patch("rag_system.CourseSearchTool"),
            patch("rag_system.CourseOutlineTool"),
        ):

            rag_system = RAGSystem(mock_config)

            # Properly mock the tool manager methods
            rag_system.tool_manager.get_last_sources = Mock(return_value=[])
            rag_system.tool_manager.get_tool_definitions = Mock(return_value=[])
            rag_system.tool_manager.reset_sources = Mock()

            return rag_system

    def test_rag_system_initialization(self, mock_config):
        """Test RAG system initializes all components correctly"""
        with (
            patch("rag_system.DocumentProcessor") as mock_doc_proc,
            patch("rag_system.VectorStore") as mock_vector_store,
            patch("rag_system.AIGenerator") as mock_ai_gen,
            patch("rag_system.SessionManager") as mock_session_mgr,
            patch("rag_system.ToolManager") as mock_tool_mgr,
            patch("rag_system.CourseSearchTool") as mock_search_tool,
            patch("rag_system.CourseOutlineTool") as mock_outline_tool,
        ):

            rag_system = RAGSystem(mock_config)

            # Verify all components are initialized
            mock_doc_proc.assert_called_once_with(
                mock_config.CHUNK_SIZE, mock_config.CHUNK_OVERLAP
            )
            mock_vector_store.assert_called_once_with(
                mock_config.CHROMA_PATH,
                mock_config.EMBEDDING_MODEL,
                mock_config.MAX_RESULTS,
            )
            mock_ai_gen.assert_called_once_with(
                mock_config.ANTHROPIC_API_KEY, mock_config.ANTHROPIC_MODEL
            )
            mock_session_mgr.assert_called_once_with(mock_config.MAX_HISTORY)

            # Verify tools are registered
            assert rag_system.tool_manager.register_tool.call_count == 2

    @patch("os.path.exists")
    def test_add_course_document_success(
        self, mock_exists, rag_system, sample_course, sample_course_chunks
    ):
        """Test successful course document addition"""
        # Setup
        mock_exists.return_value = True
        rag_system.document_processor.process_course_document.return_value = (
            sample_course,
            sample_course_chunks,
        )

        # Execute
        course, chunk_count = rag_system.add_course_document("test_course.txt")

        # Verify
        assert course == sample_course
        assert chunk_count == len(sample_course_chunks)
        rag_system.vector_store.add_course_metadata.assert_called_once_with(
            sample_course
        )
        rag_system.vector_store.add_course_content.assert_called_once_with(
            sample_course_chunks
        )

    def test_add_course_document_error_handling(self, rag_system):
        """Test error handling in course document addition"""
        # Setup - make document processor raise exception
        rag_system.document_processor.process_course_document.side_effect = Exception(
            "Processing error"
        )

        # Execute
        course, chunk_count = rag_system.add_course_document("invalid_file.txt")

        # Verify error handling
        assert course is None
        assert chunk_count == 0

    @patch("os.listdir")
    @patch("os.path.exists")
    @patch("os.path.isfile")
    def test_add_course_folder_success(
        self,
        mock_isfile,
        mock_exists,
        mock_listdir,
        rag_system,
        sample_course,
        sample_course_chunks,
    ):
        """Test successful course folder processing"""
        # Setup
        mock_exists.return_value = True
        mock_listdir.return_value = ["course1.txt", "course2.pdf", "not_a_course.jpg"]
        mock_isfile.side_effect = lambda path: path.endswith((".txt", ".pdf"))

        rag_system.vector_store.get_existing_course_titles.return_value = []

        # Create different courses for each file to avoid duplicate detection
        from models import Course, Lesson, CourseChunk

        course1 = Course(
            title="Course 1",
            course_link="https://example.com/course1",
            instructor="Instructor 1",
        )
        course2 = Course(
            title="Course 2",
            course_link="https://example.com/course2",
            instructor="Instructor 2",
        )
        chunks1 = [
            CourseChunk(
                content="Course 1 content",
                course_title="Course 1",
                lesson_number=0,
                chunk_index=0,
            )
        ]
        chunks2 = [
            CourseChunk(
                content="Course 2 content",
                course_title="Course 2",
                lesson_number=0,
                chunk_index=0,
            )
        ]

        # Return different courses for each call
        rag_system.document_processor.process_course_document.side_effect = [
            (course1, chunks1),
            (course2, chunks2),
        ]

        # Execute
        courses_added, chunks_added = rag_system.add_course_folder("test_folder")

        # Verify
        assert courses_added == 2  # Only .txt and .pdf files processed
        assert chunks_added == 2  # 1 chunk from each course
        assert rag_system.document_processor.process_course_document.call_count == 2

    @patch("os.listdir")
    @patch("os.path.exists")
    def test_add_course_folder_skip_existing_courses(
        self, mock_exists, mock_listdir, rag_system, sample_course, sample_course_chunks
    ):
        """Test that existing courses are skipped"""
        # Setup
        mock_exists.return_value = True
        mock_listdir.return_value = ["course1.txt"]

        # Existing course titles include our sample course
        rag_system.vector_store.get_existing_course_titles.return_value = [
            sample_course.title
        ]
        rag_system.document_processor.process_course_document.return_value = (
            sample_course,
            sample_course_chunks,
        )

        with patch("os.path.isfile", return_value=True):
            # Execute
            courses_added, chunks_added = rag_system.add_course_folder("test_folder")

        # Verify no courses were added (skipped existing)
        assert courses_added == 0
        assert chunks_added == 0
        rag_system.vector_store.add_course_metadata.assert_not_called()

    @patch("os.path.exists")
    def test_add_course_folder_nonexistent_folder(self, mock_exists, rag_system):
        """Test handling of nonexistent folder"""
        # Setup
        mock_exists.return_value = False

        # Execute
        courses_added, chunks_added = rag_system.add_course_folder("nonexistent_folder")

        # Verify
        assert courses_added == 0
        assert chunks_added == 0

    def test_add_course_folder_clear_existing(self, rag_system):
        """Test clearing existing data when flag is set"""
        with (
            patch("os.path.exists", return_value=True),
            patch("os.listdir", return_value=[]),
        ):

            # Execute
            rag_system.add_course_folder("test_folder", clear_existing=True)

            # Verify data was cleared
            rag_system.vector_store.clear_all_data.assert_called_once()

    def test_query_without_session(self, rag_system):
        """Test query processing without session context"""
        # Setup
        rag_system.ai_generator.generate_response.return_value = "Test response"
        rag_system.tool_manager.get_last_sources.return_value = [
            {"text": "Test Course", "link": None}
        ]

        # Execute
        response, sources = rag_system.query("What is machine learning?")

        # Verify
        assert response == "Test response"
        assert len(sources) == 1
        assert sources[0]["text"] == "Test Course"

        # Verify AI generator was called correctly
        rag_system.ai_generator.generate_response.assert_called_once()
        call_args = rag_system.ai_generator.generate_response.call_args[1]
        assert "What is machine learning?" in call_args["query"]
        assert call_args["conversation_history"] is None
        assert call_args["tools"] == rag_system.tool_manager.get_tool_definitions()
        assert call_args["tool_manager"] == rag_system.tool_manager

    def test_query_with_session(self, rag_system):
        """Test query processing with session context"""
        # Setup
        session_id = "test_session_123"
        conversation_history = "User: Previous question\nAssistant: Previous answer"

        rag_system.session_manager.get_conversation_history.return_value = (
            conversation_history
        )
        rag_system.ai_generator.generate_response.return_value = (
            "Context-aware response"
        )
        rag_system.tool_manager.get_last_sources.return_value = []

        # Execute
        response, sources = rag_system.query(
            "Follow up question", session_id=session_id
        )

        # Verify
        assert response == "Context-aware response"

        # Verify session management
        rag_system.session_manager.get_conversation_history.assert_called_once_with(
            session_id
        )
        rag_system.session_manager.add_exchange.assert_called_once_with(
            session_id, "Follow up question", "Context-aware response"
        )

        # Verify AI generator received conversation history
        call_args = rag_system.ai_generator.generate_response.call_args[1]
        assert call_args["conversation_history"] == conversation_history

    def test_query_with_tool_usage(self, rag_system):
        """Test query processing that triggers tool usage"""
        # Setup to simulate tool usage
        rag_system.ai_generator.generate_response.return_value = (
            "Answer based on search results"
        )
        rag_system.tool_manager.get_last_sources.return_value = [
            {"text": "Test Course - Lesson 1", "link": "https://example.com/lesson/1"},
            {
                "text": "Another Course - Lesson 2",
                "link": "https://example.com/lesson/2",
            },
        ]

        # Execute
        response, sources = rag_system.query("What does the course say about testing?")

        # Verify
        assert response == "Answer based on search results"
        assert len(sources) == 2
        assert sources[0]["text"] == "Test Course - Lesson 1"
        assert sources[0]["link"] == "https://example.com/lesson/1"

        # Verify sources were reset after retrieval
        rag_system.tool_manager.reset_sources.assert_called_once()

    def test_query_course_specific_content(self, rag_system):
        """Test query processing for course-specific content questions"""
        # Setup query that should trigger course search
        course_query = "Explain the testing concepts covered in the advanced course"

        rag_system.ai_generator.generate_response.return_value = (
            "Course-specific response"
        )
        rag_system.tool_manager.get_last_sources.return_value = [
            {"text": "Advanced Course", "link": None}
        ]

        # Execute
        response, sources = rag_system.query(course_query)

        # Verify
        assert response == "Course-specific response"

        # Verify proper prompt format was used
        call_args = rag_system.ai_generator.generate_response.call_args[1]
        assert "Answer this question about course materials:" in call_args["query"]
        assert course_query in call_args["query"]

    def test_query_general_knowledge(self, rag_system):
        """Test query processing for general knowledge questions"""
        # Setup query that should NOT trigger tools
        general_query = "What is the capital of France?"

        rag_system.ai_generator.generate_response.return_value = "Paris"
        rag_system.tool_manager.get_last_sources.return_value = []

        # Execute
        response, sources = rag_system.query(general_query)

        # Verify
        assert response == "Paris"
        assert len(sources) == 0

        # Verify AI generator still received tools (decision is made by AI)
        call_args = rag_system.ai_generator.generate_response.call_args[1]
        assert call_args["tools"] is not None
        assert call_args["tool_manager"] is not None

    def test_get_course_analytics(self, rag_system):
        """Test course analytics retrieval"""
        # Setup
        rag_system.vector_store.get_course_count.return_value = 3
        rag_system.vector_store.get_existing_course_titles.return_value = [
            "Course 1",
            "Course 2",
            "Course 3",
        ]

        # Execute
        analytics = rag_system.get_course_analytics()

        # Verify
        assert analytics["total_courses"] == 3
        assert len(analytics["course_titles"]) == 3
        assert "Course 1" in analytics["course_titles"]

    def test_end_to_end_workflow_with_mocked_components(
        self, mock_config, sample_course, sample_course_chunks
    ):
        """Test complete end-to-end workflow with carefully mocked components"""
        with (
            patch("rag_system.DocumentProcessor") as mock_doc_proc_class,
            patch("rag_system.VectorStore") as mock_vector_store_class,
            patch("rag_system.AIGenerator") as mock_ai_gen_class,
            patch("rag_system.SessionManager") as mock_session_mgr_class,
            patch("rag_system.ToolManager") as mock_tool_mgr_class,
            patch("rag_system.CourseSearchTool"),
            patch("rag_system.CourseOutlineTool"),
        ):

            # Setup mock instances
            mock_doc_proc = Mock()
            mock_vector_store = Mock()
            mock_ai_gen = Mock()
            mock_session_mgr = Mock()
            mock_tool_mgr = Mock()

            mock_doc_proc_class.return_value = mock_doc_proc
            mock_vector_store_class.return_value = mock_vector_store
            mock_ai_gen_class.return_value = mock_ai_gen
            mock_session_mgr_class.return_value = mock_session_mgr
            mock_tool_mgr_class.return_value = mock_tool_mgr

            # Setup workflow
            mock_doc_proc.process_course_document.return_value = (
                sample_course,
                sample_course_chunks,
            )
            mock_vector_store.get_existing_course_titles.return_value = []
            mock_ai_gen.generate_response.return_value = "Comprehensive answer"
            mock_tool_mgr.get_tool_definitions.return_value = [
                {"name": "search_course_content"}
            ]
            mock_tool_mgr.get_last_sources.return_value = [
                {"text": "Test Course", "link": None}
            ]

            # Create RAG system and simulate complete workflow
            rag_system = RAGSystem(mock_config)

            # 1. Add course document
            with patch("os.path.exists", return_value=True):
                course, chunks = rag_system.add_course_document("test_course.txt")
                assert course == sample_course
                assert chunks == len(sample_course_chunks)

            # 2. Process query
            response, sources = rag_system.query("What does the course teach?")
            assert response == "Comprehensive answer"
            assert len(sources) == 1

            # Verify all components were used correctly
            mock_doc_proc.process_course_document.assert_called()
            mock_vector_store.add_course_metadata.assert_called()
            mock_vector_store.add_course_content.assert_called()
            mock_ai_gen.generate_response.assert_called()
            mock_tool_mgr.get_last_sources.assert_called()
            mock_tool_mgr.reset_sources.assert_called()

    def test_error_handling_in_query_processing(self, rag_system):
        """Test error handling during query processing"""
        # Setup AI generator to raise exception
        rag_system.ai_generator.generate_response.side_effect = Exception(
            "AI API error"
        )

        # Execute - should not crash the system
        with pytest.raises(Exception, match="AI API error"):
            rag_system.query("Test query")

    def test_session_management_integration(self, rag_system):
        """Test session management throughout query processing"""
        session_id = "session_123"

        # First query
        rag_system.ai_generator.generate_response.return_value = "First response"
        rag_system.tool_manager.get_last_sources.return_value = []
        rag_system.session_manager.get_conversation_history.return_value = None

        response1, _ = rag_system.query("First question", session_id=session_id)

        # Verify session was updated
        rag_system.session_manager.add_exchange.assert_called_with(
            session_id, "First question", "First response"
        )

        # Second query with history
        conversation_history = "User: First question\nAssistant: First response"
        rag_system.session_manager.get_conversation_history.return_value = (
            conversation_history
        )
        rag_system.ai_generator.generate_response.return_value = (
            "Second response with context"
        )

        response2, _ = rag_system.query("Follow up", session_id=session_id)

        # Verify history was used
        second_call_args = rag_system.ai_generator.generate_response.call_args_list[1][
            1
        ]
        assert second_call_args["conversation_history"] == conversation_history
