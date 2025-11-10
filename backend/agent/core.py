"""Core agent with session-scoped memory."""
import logging
import warnings
from typing import Dict, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory

from agent.tools import AgentTools
from agent.prompts import get_system_prompt
from utils.config import settings

logger = logging.getLogger(__name__)

# In-memory conversation store keyed by session_id so context persists across requests
MEMORIES: Dict[str, ConversationBufferMemory] = {}

class WalletAgent:
    """Integrated wallet agent."""
    
    def __init__(self, cdp_service, db_service):
        self.cdp_service = cdp_service
        self.db_service = db_service
        # Silence warnings
        warnings.filterwarnings("ignore", message="Convert_system_message_to_human will be deprecated!")
        warnings.filterwarnings(
            "ignore",
            message="Please see the migration guide at: https://python.langchain.com/docs/versions/migrating_memory/",
        )
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=settings.google_api_key,
            temperature=0.1,
            convert_system_message_to_human=True,
            max_output_tokens=1024,
        )
    
    async def process(
        self,
        message: str,
        session_id: str,
        wallet_address: Optional[str] = None
    ) -> str:
        """Process user message with wallet context."""
        import time
        start_time = time.time()
        logger.info(f"[Agent] Starting to process message for session {session_id}")
        
        try:
            tools_instance = AgentTools(
                cdp_service=self.cdp_service,
                db_service=self.db_service,
                session_id=session_id,
                current_wallet=wallet_address
            )
            tools = tools_instance.get_tools()

            system_prompt = get_system_prompt(wallet_address)

            # PromptTemplate with required ReAct variables for create_react_agent
            template = f"""{system_prompt}

TOOLS AVAILABLE:
{{tools}}

FORMAT:
Question: the input question you must answer
Thought: think about what to do (be specific and brief)
Action: the action to take, must be one of [{{tool_names}}]
Action Input: the input to the action
Observation: the result of the action
... (repeat Thought/Action/Action Input/Observation as needed)
Thought: I now know the final answer
Final Answer: the final answer to the original input question (be concise and natural)

CONVERSATION HISTORY:
{{chat_history}}

USER QUERY:
{{input}}

YOUR RESPONSE:
{{agent_scratchpad}}"""

            prompt = PromptTemplate(
                template=template,
                input_variables=["input", "agent_scratchpad", "chat_history", "tools", "tool_names"]
            )

            agent = create_react_agent(llm=self.llm, tools=tools, prompt=prompt)

            # Use per-session memory so previous turns are available when deciding tools
            memory = MEMORIES.get(session_id)
            if memory is None:
                memory = ConversationBufferMemory(
                    memory_key="chat_history",
                    return_messages=True,
                    output_key="output"
                )
                MEMORIES[session_id] = memory

            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                memory=memory,
                verbose=True,  # Enable to see agent reasoning and tool calls
                handle_parsing_errors="Check your output and make sure it conforms to the expected format!",
                max_iterations=10,  # Reduced to prevent loops - most tasks need 2-5 iterations
                max_execution_time=120,  # Reduced to 2 minutes for faster feedback
                return_intermediate_steps=False,
                early_stopping_method="force"
            )

            result = await agent_executor.ainvoke(
                {"input": message},
                {"max_execution_time": 600}  # Match the executor's max_execution_time
            )
            
            elapsed = time.time() - start_time
            logger.info(f"[Agent] Completed processing in {elapsed:.2f} seconds")
            
            return result.get('output', 'No response generated')
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[Agent] Processing error after {elapsed:.2f} seconds: {e}", exc_info=True)
            raise

