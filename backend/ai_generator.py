import anthropic
from typing import List, Optional, Dict, Any


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive search tools for course information.

Available Tools:
- **search_course_content**: Search within course materials for specific content
- **get_course_outline**: Get course overview with title, link, and complete lesson list

Tool Usage Guidelines:
- Use **search_course_content** for questions about specific course content or detailed educational materials
- Use **get_course_outline** for questions about course structure, lesson lists, or course overviews
- **Multi-round tool usage**: You can use tools up to 2 times in separate rounds for complex queries
- **Sequential reasoning**: Use initial tool results to inform follow-up tool calls when needed
- **Progressive information gathering**: Start broad, then narrow focus based on results
- Synthesize tool results into accurate, fact-based responses
- If tools yield no results, state this clearly without offering alternatives

Multi-Tool Usage Examples:
- Search broad course content → Get specific course outline for detailed structure
- Search one course → Search related course for comparison or additional context  
- Get course outline → Search specific lesson content for detailed information
- Find course discussing topic X → Search for courses with similar topics for comparison

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course-specific content questions**: Use search_course_content first, then answer
- **Course outline/structure questions**: Use get_course_outline first, then answer
- **Complex queries**: Use multiple tool rounds to gather comprehensive information, then synthesize
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the search results" or "using the outline tool"
 - Do not explain your multi-round tool usage process

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

        # Configuration for sequential tool calling
        self.MAX_TOOL_ROUNDS = 2

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        Supports sequential tool calling for up to 2 rounds.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Use sequential tool calling if tools are available
        if tools and tool_manager:
            return self._sequential_tool_calling(
                query, system_content, tools, tool_manager
            )

        # Fall back to single API call without tools
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content,
        }

        response = self.client.messages.create(**api_params)
        return response.content[0].text

    def _sequential_tool_calling(
        self, query: str, system_content: str, tools: List, tool_manager
    ) -> str:
        """
        Handle sequential tool calling with up to MAX_TOOL_ROUNDS rounds.

        Args:
            query: The user's question
            system_content: System prompt with conversation history
            tools: Available tools for Claude to use
            tool_manager: Manager to execute tools

        Returns:
            Final response after all tool rounds
        """
        # Initialize conversation with user query
        messages = [{"role": "user", "content": query}]
        round_count = 0

        while round_count < self.MAX_TOOL_ROUNDS:
            # Prepare API call with tools available
            api_params = {
                **self.base_params,
                "messages": messages,
                "system": system_content,
                "tools": tools,
                "tool_choice": {"type": "auto"},
            }

            # Get response from Claude
            response = self.client.messages.create(**api_params)

            # Check if Claude decided to use tools
            if response.stop_reason != "tool_use":
                # Claude didn't use tools, return direct response
                return response.content[0].text

            # Claude used tools - add response to conversation
            messages.append({"role": "assistant", "content": response.content})

            # Execute all tool calls and collect results
            tool_results = self._execute_tools(response, tool_manager)

            # If no tool results (all tools failed), terminate early
            if not tool_results:
                # Return Claude's original response since tools failed
                return (
                    response.content[0].text
                    if response.content
                    else "I apologize, but I encountered an error while processing your request."
                )

            # Add tool results to conversation
            messages.append({"role": "user", "content": tool_results})

            round_count += 1

        # Max rounds reached - make final synthesis call without tools
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content,
        }

        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text

    def _execute_tools(self, response, tool_manager) -> List[Dict]:
        """
        Execute all tool calls in a response and return formatted results.

        Args:
            response: Claude response containing tool use blocks
            tool_manager: Manager to execute tools

        Returns:
            List of tool results formatted for conversation, empty list if all tools fail
        """
        tool_results = []
        for content_block in response.content:
            if content_block.type == "tool_use":
                tool_result = tool_manager.execute_tool(
                    content_block.name, **content_block.input
                )

                # Only add results if tool execution succeeded
                if tool_result is not None:
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": tool_result,
                        }
                    )

        return tool_results

    def _handle_tool_execution(
        self, initial_response, base_params: Dict[str, Any], tool_manager
    ):
        """
        Legacy method for backward compatibility - delegates to new tool execution method.

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools

        Returns:
            Final response text after tool execution
        """
        # Start with existing messages
        messages = base_params["messages"].copy()

        # Add AI's tool use response
        messages.append({"role": "assistant", "content": initial_response.content})

        # Execute tools using new method
        tool_results = self._execute_tools(initial_response, tool_manager)

        # Add tool results as single message
        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        # Prepare final API call without tools
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": base_params["system"],
        }

        # Get final response
        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text
