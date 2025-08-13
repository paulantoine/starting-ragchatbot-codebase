# RAG System Query Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                   FRONTEND                                      │
│                                (script.js)                                     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                    1. User types query & clicks send
                                       │
                                       ▼
                    ┌─────────────────────────────────┐
                    │     sendMessage()               │
                    │  • Disable input                │
                    │  • Show loading animation       │
                    │  • Add user message to chat     │
                    └─────────────────────────────────┘
                                       │
                    2. POST /api/query with JSON payload
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                FASTAPI SERVER                                  │
│                                  (app.py)                                      │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                    3. API endpoint receives request
                                       │
                                       ▼
                    ┌─────────────────────────────────┐
                    │  query_documents()              │
                    │  • Create session if needed     │
                    │  • Call rag_system.query()     │
                    └─────────────────────────────────┘
                                       │
                    4. Forward to RAG system
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              RAG SYSTEM                                        │
│                           (rag_system.py)                                      │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                    5. Orchestrate query processing
                                       │
                                       ▼
                    ┌─────────────────────────────────┐
                    │     query()                     │
                    │  • Build prompt                 │
                    │  • Get conversation history     │
                    │  • Call AI generator with tools │
                    └─────────────────────────────────┘
                                       │
                    6. Send to AI generator
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            AI GENERATOR                                        │
│                           (ai_generator.py)                                    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                    7. Generate response with Claude API
                                       │
                                       ▼
                    ┌─────────────────────────────────┐
                    │  generate_response()            │
                    │  • Send to Claude with tools    │
                    │  • Handle tool execution        │
                    │  • Get final response           │
                    └─────────────────────────────────┘
                                       │
                    8. If Claude decides to use search tool
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           SEARCH TOOLS                                         │
│                          (search_tools.py)                                     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                    9. Execute search tool
                                       │
                                       ▼
                    ┌─────────────────────────────────┐
                    │  CourseSearchTool.execute()     │
                    │  • Parse search parameters      │
                    │  • Call vector store search     │
                    │  • Format results with context  │
                    │  • Track sources for UI         │
                    └─────────────────────────────────┘
                                       │
                    10. Query vector database
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           VECTOR STORE                                         │
│                          (vector_store.py)                                     │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                    11. Semantic search with ChromaDB
                                       │
                                       ▼
                    ┌─────────────────────────────────┐
                    │     search()                    │
                    │  • Resolve course names         │
                    │  • Query embeddings             │
                    │  • Apply filters                │
                    │  • Return ranked results        │
                    └─────────────────────────────────┘
                                       │
                    12. Return search results
                                       │
                                       ▼
                    ┌─────────────────────────────────┐
                    │     ChromaDB                    │
                    │  • Vector similarity search     │
                    │  • Embedding comparison         │
                    │  • Metadata filtering           │
                    └─────────────────────────────────┘
                                       │
                              Results flow back up
                                       │
                                       ▼
                    ┌─────────────────────────────────┐
                    │   Tool Results → Claude         │
                    │  • Search results added to      │
                    │    conversation context         │
                    │  • Claude generates final       │
                    │    natural language response    │
                    └─────────────────────────────────┘
                                       │
                    13. Response + sources back to RAG
                                       │
                                       ▼
                    ┌─────────────────────────────────┐
                    │   RAG System                    │
                    │  • Get sources from tool mgr    │
                    │  • Update conversation history  │
                    │  • Return (response, sources)   │
                    └─────────────────────────────────┘
                                       │
                    14. Return to API endpoint
                                       │
                                       ▼
                    ┌─────────────────────────────────┐
                    │   FastAPI Response              │
                    │  • Create QueryResponse         │
                    │  • Include answer, sources,     │
                    │    session_id                   │
                    └─────────────────────────────────┘
                                       │
                    15. JSON response to frontend
                                       │
                                       ▼
                    ┌─────────────────────────────────┐
                    │   Frontend Display              │
                    │  • Remove loading animation     │
                    │  • Render markdown response     │
                    │  • Show sources in collapsible  │
                    │  • Re-enable input              │
                    └─────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                                DATA FLOW                                       │
└─────────────────────────────────────────────────────────────────────────────────┘

Input:  "What is covered in lesson 2 of the MCP course?"
        ↓
Query:  POST /api/query {"query": "...", "session_id": "..."}
        ↓
Prompt: "Answer this question about course materials: ..."
        ↓
Tool:   search_course_content(query="lesson 2 content", course_name="MCP")
        ↓
Vector: Semantic search in ChromaDB for relevant chunks
        ↓
Results: [Course chunks with metadata about MCP lesson 2]
        ↓
Claude: Generates natural language answer from search results
        ↓
Output: {"answer": "Lesson 2 covers...", "sources": ["MCP - Lesson 2"], "session_id": "..."}
        ↓
UI:     Displays formatted answer with collapsible sources