#!/usr/bin/env python3
"""
Coral Unified Debug Agent - Single agent for complete debugging workflow
Consolidates Debug Orchestrator and BugLocator functionality to reduce LLM costs
"""

import logging
import os, json, asyncio, traceback
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.prompts import ChatPromptTemplate
from langchain.chat_models import init_chat_model
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import urllib.parse
from unified_debug_solver import UnifiedDebugSolver

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DebugWorkflowInput(BaseModel):
    """Input schema for the unified debug workflow tool."""
    bug_description: str = Field(description="The bug description or issue report to debug")
    repository_name: str = Field(default=None, description="Repository name to target specific codebase (optional)")
    auto_edit_mode: bool = Field(default=False, description="If true, automatically apply fixes without human approval")


class RepositoryIndexInput(BaseModel):
    """Input schema for repository indexing tool."""
    repo_path: str = Field(description="Path to the repository to index")
    repo_name: str = Field(description="Name for the repository collection")


async def unified_debug_workflow(bug_description: str, repository_name: str = None, auto_edit_mode: bool = False):
    """
    Complete unified debugging workflow using direct tool calls instead of agent communication.
    
    Args:
        bug_description (str): The bug description to debug
        repository_name (str): Optional repository name to target specific codebase
        auto_edit_mode (bool): If True, automatically apply fixes without human approval
        
    Returns:
        str: JSON formatted workflow results with all steps and final status
    """
    solver = UnifiedDebugSolver()
    workflow_result = await solver.debug_repository_issue(bug_description, repository_name, auto_edit_mode)
    return workflow_result


async def index_repository_tool(repo_path: str, repo_name: str):
    """
    Index a repository for bug localization.
    
    Args:
        repo_path (str): Path to the repository to index
        repo_name (str): Name for the repository collection
        
    Returns:
        str: JSON formatted indexing results
    """
    solver = UnifiedDebugSolver()
    index_result = await solver.index_repository(repo_path, repo_name)
    return index_result


def get_tools_description(tools):
    descriptions = []
    for tool in tools:
        try:
            # Handle StructuredTool with Pydantic schema
            if hasattr(tool.args_schema, 'model_json_schema'):
                schema = tool.args_schema.model_json_schema()
            else:
                schema = tool.args_schema
            schema_str = json.dumps(schema).replace('{', '{{').replace('}', '}}')
            descriptions.append(f"Tool: {tool.name}, Schema: {schema_str}")
        except Exception as e:
            # Fallback to just tool name and description
            descriptions.append(f"Tool: {tool.name}, Description: {tool.description}")
    return "\\n".join(descriptions)


async def create_agent(coral_tools, agent_tools):
    coral_tools_description = get_tools_description(coral_tools)
    agent_tools_description = get_tools_description(agent_tools)
    combined_tools = coral_tools + agent_tools

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            f"""You are a unified debugging agent that handles the complete debugging workflow from bug analysis to code fixes. You consolidate the functionality of multiple specialized agents into a single, cost-effective agent.

            **CORE CAPABILITIES:**
            - Bug localization using vector similarity search
            - Code fix generation using Mistral Codestral
            - Human approval workflows
            - Git patch application
            - Repository indexing and management

            **WORKFLOW PROCESS:**
            
            1. **Listen for Mentions**: Call wait_for_mentions from coral tools (timeoutMs: 30000) to receive mentions from Interface Agent or users.
            
            2. **Parse Requests**: When you receive a mention, analyze the content to identify:
               - **Bug Reports**: Error descriptions, unexpected behavior, performance issues, crashes, etc.
               - **Repository Indexing**: Requests to index new repositories for analysis
               - **Repository Context**: Look for "Repository: [repo-name]" format in messages
            
            3. **Bug Debugging Workflow**: For bug reports, use your `unified_debug_workflow` tool:
               - Extract repository name if mentioned (format: "Repository: [repo-name]")
               - Pass the complete bug description to the tool
               - Set auto_edit_mode based on user preferences (default: false for human approval)
               - The tool will handle: bug localization → code fixing → human review → patch application
               - Return comprehensive workflow results to the sender
            
            4. **Repository Indexing**: For indexing requests, use your `index_repository_tool`:
               - Parse repository path and name from the request
               - Index the repository for future bug localization
               - Return indexing results to the sender
            
            5. **Response Handling**: Always send results back using send_message from coral tools:
               - Include comprehensive workflow summaries
               - Provide clear status updates (completed, failed, partial)
               - Include any relevant file paths or fix recommendations
               - Mention the sender in the response
            
            6. **Error Handling**: If any step fails:
               - Provide detailed error information
               - Suggest recovery steps or alternative approaches
               - Always respond to the sender even on failures
            
            7. **Continuous Operation**: Return to step 1 to wait for new mentions
            
            **COST OPTIMIZATION FEATURES:**
            - Single LLM call per debugging session (vs 6-10 in multi-agent setup)
            - Direct tool calling eliminates agent-to-agent communication overhead
            - Consolidated workflow reduces unnecessary coordination steps
            - Repository-aware processing minimizes redundant searches
            
            **RESPONSE FORMAT:**
            Always provide structured responses with:
            - **Status**: Clear indication of success/failure
            - **Steps Completed**: Summary of workflow steps executed
            - **Results**: Key findings, fixes generated, files modified
            - **Next Actions**: Any required follow-up steps
            
            **AUTO-EDIT MODE:**
            - When auto_edit_mode=false: Human approval required for patches
            - When auto_edit_mode=true: Automatic patch application
            - Always inform users about the current mode setting
            
            **REPOSITORY AWARENESS:**
            - Support for multiple repository collections
            - Automatic collection switching based on repository names
            - Maintains context across debugging sessions
            
            **ERROR RECOVERY:**
            - Graceful degradation when tools fail
            - Fallback options for partial workflow completion
            - Clear error messaging with actionable guidance
            
            These are the list of coral tools: {coral_tools_description}
            These are the list of your tools: {agent_tools_description}
            
            **Remember**: You are a single, unified agent that replaces multiple specialized agents. Your goal is to provide the same comprehensive debugging capabilities while dramatically reducing LLM costs through direct tool integration."""
        ),
        ("placeholder", "{agent_scratchpad}")
    ])

    model = init_chat_model(
        model=os.getenv("MODEL_NAME", "deepseek-chat"),
        model_provider=os.getenv("MODEL_PROVIDER", "openai"),  # DeepSeek uses OpenAI-compatible API
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        temperature=float(os.getenv("MODEL_TEMPERATURE", "0.1")),
        max_tokens=int(os.getenv("MODEL_MAX_TOKENS", "8000")),
        base_url=os.getenv("MODEL_BASE_URL", "https://api.deepseek.com/v1")
    )

    agent = create_tool_calling_agent(model, combined_tools, prompt)
    return AgentExecutor(agent=agent, tools=combined_tools, verbose=True, handle_parsing_errors=True)


async def main():
    runtime = os.getenv("CORAL_ORCHESTRATION_RUNTIME", None)
    if runtime is None:
        load_dotenv()

    base_url = os.getenv("CORAL_SSE_URL")
    agentID = os.getenv("CORAL_AGENT_ID")

    coral_params = {
        "agentId": agentID
    }

    query_string = urllib.parse.urlencode(coral_params)

    CORAL_SERVER_URL = f"{base_url}?{query_string}"
    logger.info(f"Connecting to Coral Server: {CORAL_SERVER_URL}")
    
    timeout = int(os.getenv("TIMEOUT_MS", 300))

    client = MultiServerMCPClient(
        connections={
            "coral": {
                "transport": "sse",
                "url": CORAL_SERVER_URL,
                "timeout": timeout,
                "sse_read_timeout": timeout,
            }
        }
    )
    logger.info("Coral Server Connection Established")

    coral_tools = await client.get_tools(server_name="coral")
    logger.info(f"Coral tools count: {len(coral_tools)}")

    # Create unified debug agent tools
    agent_tools = [
        StructuredTool.from_function(
            name="unified_debug_workflow",
            func=unified_debug_workflow,
            description="Complete unified debugging workflow including bug localization, code fixing, human review, and patch application. Handles entire debugging process in a single tool call.",
            args_schema=DebugWorkflowInput,
            coroutine=unified_debug_workflow
        ),
        StructuredTool.from_function(
            name="index_repository_tool", 
            func=index_repository_tool,
            description="Index a repository for bug localization. Creates vector embeddings of code elements for similarity search.",
            args_schema=RepositoryIndexInput,
            coroutine=index_repository_tool
        )
    ]
    
    agent_executor = await create_agent(coral_tools, agent_tools)

    while True:
        try:
            logger.info("Starting new agent invocation")
            await agent_executor.ainvoke({"agent_scratchpad": []})
            logger.info("Completed agent invocation, restarting loop")
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error in agent loop: {str(e)}")
            logger.error(traceback.format_exc())
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())