import asyncio  # Manages asynchronous operations
import os  # Provide interaction with the operating system.

from camel.agents import ChatAgent  # creates Agents
from camel.models import ModelFactory  # encapsulates LLM
from camel.toolkits import HumanToolkit, MCPToolkit  # import tools
from camel.toolkits.mcp_toolkit import MCPClient
from camel.types import ModelPlatformType, ModelType
from dotenv import load_dotenv

from config import PLATFORM_TYPE, MODEL_TYPE, MODEL_CONFIG, MESSAGE_WINDOW_SIZE, TOKEN_LIMIT

# load_dotenv()

from prompts import get_tools_description, get_user_message

async def main():
    # Simply add the Coral server address as a tool
    coral_url = os.getenv("CORAL_SSE_URL", default = "http://localhost:5555/sse") + f"?agentId={os.getenv('CORAL_AGENT_ID', 'interface-agent')}&agentDescription=User interaction agent that facilitates communication between users and other agents"
    server = MCPClient(command_or_url=coral_url, timeout=3000000.0)

    mcp_toolkit = MCPToolkit([server])
    
    try:
        await mcp_toolkit.connect()
        print("Connected to coral server.")
        camel_agent = await create_interface_agent(mcp_toolkit)

        # Let the agent run autonomously like the unified debug agent
        first_run = True
        while True:
            try:
                if first_run:
                    # On first run, explicitly tell the agent to start listening
                    resp = await camel_agent.astep("Start by calling wait_for_mentions tool to listen for messages")
                    first_run = False
                else:
                    # On subsequent runs, let the agent continue autonomously
                    resp = await camel_agent.astep("")
                
                if resp.msgs:
                    msgzero = resp.msgs[0]
                    msgzerojson = msgzero.to_dict()
                    print("Agent response:", msgzerojson)
                
                # Small delay to prevent overwhelming the system
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Error in agent loop: {e}")
                await asyncio.sleep(5)
    finally:
        await mcp_toolkit.disconnect()

async def create_interface_agent(connected_mcp_toolkit):
    tools = connected_mcp_toolkit.get_tools()
    sys_msg = (
        f"""
            You are a helpful assistant responsible for interacting with the user and working with other agents to meet the user's requests. You can interact with other agents using the chat tools.
            User interaction is your speciality. You identify as "{os.getenv("CORAL_AGENT_ID", default = "N/A")}".
            
            **WORKFLOW PROCESS:**
            
            1. **Listen for Messages**: Start by calling the wait_for_mentions tool (timeoutMs: 30000) to transition to listening state and receive new messages from other agents or users.
            
            2. **User Interaction**: As a user interaction agent, only you can interact with the user. Use the user_input tool to get new tasks from the user when needed.
            
            3. **Agent Collaboration**: Work with other agents to meet user requests. Make sure to put the name of the agent(s) you are talking to in the mentions field of the send message tool.
            
            4. **Continuous Operation**: After handling any messages, return to step 1 to wait for new mentions.
            
            Make sure that all information comes from reliable sources and that all calculations are done using the appropriate tools by the appropriate agents. Make sure your responses are much more reliable than guesses! You should make sure no agents are guessing too, by suggesting the relevant agents to do each part of a task to the agents you are working with. Do a refresh of the available agents before asking the user for input.
            
            {os.getenv("CORAL_PROMPT_SYSTEM", default = "")}
            
            Here are the guidelines for using the communication tools:
            {get_tools_description()}
            """
    )
    model = ModelFactory.create(
        model_platform=ModelPlatformType[PLATFORM_TYPE],
        model_type=ModelType[MODEL_TYPE],
        api_key=os.getenv("OPENAI_API_KEY"),
        model_config_dict=MODEL_CONFIG,
    )
    camel_agent = ChatAgent(  # create agent with our mcp tools
        system_message=sys_msg,
        model=model,
        tools=tools,
        message_window_size=MESSAGE_WINDOW_SIZE,
        token_limit=TOKEN_LIMIT
    )
    return camel_agent


if __name__ == "__main__":
    asyncio.run(main())
