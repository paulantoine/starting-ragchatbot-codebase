# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

### Prerequisites
- Python 3.13+ with `uv` package manager
- Anthropic API key in `.env` file: `ANTHROPIC_API_KEY=your_key_here`

### Start Development Server
```bash
# Quick start
chmod +x run.sh && ./run.sh

# Manual start
cd backend && uv run uvicorn app:app --reload --port 8000
```

### Install Dependencies
```bash
uv sync
```

### Access Points
- Web Interface: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Architecture Overview

This is a **Retrieval-Augmented Generation (RAG) chatbot** for course materials with a modular backend architecture:

### Core Components Flow
1. **Document Processing Pipeline** (`document_processor.py`):
   - Parses structured course documents with metadata extraction
   - Performs sentence-based chunking with configurable overlap
   - Enhances chunks with course/lesson context for better retrieval

2. **Vector Storage System** (`vector_store.py`):
   - Uses ChromaDB with sentence-transformers for semantic search
   - Maintains separate collections for course metadata and content
   - Supports course name resolution and lesson filtering

3. **Tool-Based Search Architecture** (`search_tools.py`):
   - Implements pluggable tool system for AI function calling
   - `CourseSearchTool` handles semantic search with smart course name matching
   - `ToolManager` orchestrates tool execution and source tracking

4. **AI Integration** (`ai_generator.py`):
   - Claude API integration with tool calling support
   - Handles tool execution workflow and conversation context
   - Uses system prompts to control search behavior and response format

5. **Session Management** (`session_manager.py`):
   - Maintains conversation history with configurable limits
   - Supports session-based context for multi-turn conversations

6. **RAG Orchestration** (`rag_system.py`):
   - Main coordinator that connects all components
   - Handles document ingestion from `/docs` folder
   - Manages query processing workflow from input to response

### Data Models (`models.py`)
- `Course`: Structured course metadata with lessons
- `CourseChunk`: Vector storage unit with course/lesson context
- `Lesson`: Individual lesson metadata within courses

### Expected Document Format
Course documents should follow this structure:
```
Course Title: [title]
Course Link: [optional URL]
Course Instructor: [instructor name]

Lesson 0: Introduction
Lesson Link: [optional URL]
[lesson content...]

Lesson 1: Next Topic
[lesson content...]
```

### Configuration (`config.py`)
Key settings in dataclass format:
- `CHUNK_SIZE`: 800 characters for text chunks
- `CHUNK_OVERLAP`: 100 characters for context preservation
- `MAX_RESULTS`: 5 search results maximum
- `ANTHROPIC_MODEL`: claude-sonnet-4-20250514
- `EMBEDDING_MODEL`: all-MiniLM-L6-v2

### Frontend Integration
- Static file serving through FastAPI with CORS enabled
- WebSocket-like chat interface with markdown rendering
- Real-time course statistics and suggested questions
- Source attribution display in collapsible sections

## Development Notes

### Adding New Tools
1. Inherit from `Tool` abstract base class in `search_tools.py`
2. Implement `get_tool_definition()` and `execute()` methods
3. Register with `ToolManager` in `rag_system.py`

### Document Processing
- Documents are automatically loaded from `/docs` folder on startup
- System avoids re-processing existing courses by checking titles
- Use `clear_existing=True` for full rebuild when calling `add_course_folder()`

### Vector Store Collections
- `course_catalog`: Course titles and instructor metadata for name resolution
- `course_content`: Actual chunked course material for content search

### Error Handling
- Graceful fallbacks at each layer (document processing, vector search, AI generation)
- UTF-8 encoding handling with error recovery in document reading
- Empty result handling with informative error messages