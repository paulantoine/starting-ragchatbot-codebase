# Clickable Sources Implementation

This document describes the implementation of clickable source citations that open lesson videos in new tabs.

## Overview

The chat interface now displays source citations as clickable links that open the corresponding lesson videos in new browser tabs. The links are embedded invisibly (no visible URL text) and maintain the same visual appearance as before.

## Changes Made

### 1. Backend: Search Tools (`backend/search_tools.py`)

**Modified `_format_results` method:**
- Changed source format from simple strings to objects with `text` and `link` properties
- Added lesson link retrieval using `vector_store.get_lesson_link()`
- Maintains backward compatibility with legacy string format

```python
# New source format
source = {
    "text": "Course Title - Lesson X",
    "link": "https://lesson-video-url.com"
}
```

### 2. Backend: Vector Store (`backend/vector_store.py`)

**Fixed `get_lesson_link` method:**
- Added missing return statement in exception handling
- Method retrieves lesson links from the `course_catalog` collection's JSON metadata

### 3. Frontend: JavaScript (`frontend/script.js`)

**Modified `addMessage` function:**
- Updated source rendering to handle both new object format and legacy strings
- Creates clickable `<a>` tags with `target="_blank"` and `rel="noopener noreferrer"`
- Maintains visual consistency with existing design

```javascript
// New source rendering logic
if (source.link) {
    return `<a href="${source.link}" target="_blank" rel="noopener noreferrer">${escapeHtml(source.text)}</a>`;
}
```

### 4. Frontend: CSS (`frontend/style.css`)

**Added styles for clickable source links:**
- Links use primary color scheme
- Subtle hover effects with border-bottom animation
- No visible URL text, maintaining clean appearance

```css
.sources-content a {
    color: var(--primary-color);
    text-decoration: none;
    border-bottom: 1px solid transparent;
    transition: all 0.2s ease;
}
```

## Data Flow

1. **Document Processing**: Lesson links are extracted and stored in `course_catalog` collection as JSON metadata
2. **Search Execution**: When AI searches for content, `CourseSearchTool` retrieves relevant chunks
3. **Link Retrieval**: For each result, the system looks up the lesson link using course title and lesson number
4. **Source Formatting**: Sources are formatted as objects containing both display text and clickable links
5. **Frontend Rendering**: JavaScript renders sources as clickable links that open in new tabs

## Backward Compatibility

The implementation maintains full backward compatibility:
- Legacy string sources are still supported
- Existing functionality remains unchanged
- Graceful fallback when lesson links are not available

## Security Features

- Links open in new tabs with `target="_blank"`
- Security attributes: `rel="noopener noreferrer"`
- HTML escaping prevents XSS attacks
- No visible URL text reduces phishing risks

## Testing

A test script `test_clickable_sources.py` is provided to verify:
- Lesson link retrieval from vector store
- Source formatting with links
- End-to-end functionality

## Usage

Users can now:
1. Ask questions about course content
2. View source citations in the collapsible "Sources" section
3. Click on any source to open the corresponding lesson video
4. Videos open in new tabs without disrupting the chat session

## Example

**User Query**: "What is computer use with Anthropic?"

**Response Sources**: 
- [Building Towards Computer Use with Anthropic - Lesson 0] ← Clickable link
- [Building Towards Computer Use with Anthropic - Lesson 1] ← Clickable link

Clicking these sources opens the actual lesson videos from the course platform.
