#!/usr/bin/env python3
"""
Test script to verify clickable source links functionality
"""

import sys
import os
sys.path.append('backend')

from vector_store import VectorStore
from search_tools import CourseSearchTool
from config import config

def test_lesson_link_retrieval():
    """Test that lesson links can be retrieved from the vector store"""
    print("Testing lesson link retrieval...")
    
    # Initialize vector store
    vector_store = VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL, config.MAX_RESULTS)
    
    # Test getting lesson link for a known course and lesson
    course_title = "Building Towards Computer Use with Anthropic"
    lesson_number = 0
    
    lesson_link = vector_store.get_lesson_link(course_title, lesson_number)
    
    if lesson_link:
        print(f"✅ Successfully retrieved lesson link: {lesson_link}")
        return True
    else:
        print(f"❌ Failed to retrieve lesson link for {course_title}, Lesson {lesson_number}")
        return False

def test_search_tool_sources():
    """Test that search tool returns sources with links"""
    print("\nTesting search tool source formatting...")
    
    # Initialize components
    vector_store = VectorStore(config.CHROMA_PATH, config.EMBEDDING_MODEL, config.MAX_RESULTS)
    search_tool = CourseSearchTool(vector_store)
    
    # Perform a search
    result = search_tool.execute("computer use introduction")
    
    # Check if sources were generated
    sources = search_tool.last_sources
    
    if sources:
        print(f"✅ Generated {len(sources)} sources:")
        for i, source in enumerate(sources):
            if isinstance(source, dict):
                text = source.get('text', 'No text')
                link = source.get('link', 'No link')
                print(f"  {i+1}. Text: {text}")
                print(f"     Link: {link}")
            else:
                print(f"  {i+1}. Legacy format: {source}")
        return True
    else:
        print("❌ No sources generated")
        return False

if __name__ == "__main__":
    print("Testing Clickable Sources Implementation")
    print("=" * 50)
    
    # Check if ChromaDB exists
    if not os.path.exists(config.CHROMA_PATH):
        print("❌ ChromaDB not found. Please run the application first to initialize the database.")
        sys.exit(1)
    
    test1_passed = test_lesson_link_retrieval()
    test2_passed = test_search_tool_sources()
    
    print("\n" + "=" * 50)
    if test1_passed and test2_passed:
        print("✅ All tests passed! Clickable sources should work.")
    else:
        print("❌ Some tests failed. Check the implementation.")
