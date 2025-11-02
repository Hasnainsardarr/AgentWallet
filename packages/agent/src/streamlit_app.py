"""
Streamlit chat interface for CDP Wallet Agent.
"""
import streamlit as st
import os
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from tools import WalletTools
from prompts import SYSTEM_PROMPT
from wallet_store import load_wallet, save_wallet, clear_wallet

# Load environment variables
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

ADDR_RE = re.compile(r"\b0x[a-fA-F0-9]{40}\b")

def extract_addresses(text: str):
    return ADDR_RE.findall(text or "")

def wants_to_use_wallet(text: str) -> str | None:
    t = (text or "").lower()
    if "use wallet" in t or "switch to wallet" in t or "set wallet" in t:
        addrs = extract_addresses(text)
        return addrs[0] if addrs else None
    return None

def expand_my_wallet(text: str, current_wallet: str | None) -> tuple[str, str | None]:
    """Expand 'my wallet' references to actual wallet address."""
    t = text
    info = None
    if current_wallet:
        t = t.replace("my wallet", f"wallet {current_wallet}")
        t = t.replace("My wallet", f"wallet {current_wallet}")
        t = t.replace("this wallet", f"wallet {current_wallet}")
        t = t.replace("This wallet", f"wallet {current_wallet}")
    else:
        if "my wallet" in text.lower() or "this wallet" in text.lower():
            info = "No stored wallet found. Please 'create a new wallet' or say 'use wallet 0x...' to set it explicitly."
    return t, info

def sanitize_addresses(text: str, current_wallet: str | None) -> tuple[str, str | None]:
    """Warn if user provides external addresses (won't switch wallet)."""
    info = None
    addrs = extract_addresses(text)
    if addrs and current_wallet:
        for a in addrs:
            if a != current_wallet:
                info = f"Ignoring external address {a}. Using stored wallet {current_wallet}. To switch, type: use wallet {a}"
                break
    return text, info

def create_agent(get_current_input, on_wallet_created):
    """Create and cache the agent executor."""
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=GOOGLE_API_KEY,
        temperature=0.1,
        convert_system_message_to_human=True,
        max_output_tokens=1024,
    )

    wallet_tools = WalletTools(
        api_base=BACKEND_URL,
        get_current_user_input=get_current_input,
        on_wallet_created=on_wallet_created,
    )
    tools = wallet_tools.get_tools()

    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        output_key="output"
    )

    template = f"""{SYSTEM_PROMPT}

NON-NEGOTIABLE WALLET RULES:
A) Never create a wallet unless the user clearly asks to create/open/generate/make/set up a new wallet/account/address.
B) Only use the locally stored wallet as the source of truth.
C) Never switch to another 0x address unless the user explicitly says: "use wallet 0x...".
D) If the user provides another 0x address in a command, treat it only as a recipient (do not switch active wallet).
E) If no stored wallet exists and the user says "my wallet", ask them to create or set one.

TOOLS AVAILABLE:
{{tools}}

FORMAT:
Question: the input question you must answer
Thought: think about what to do (be specific and brief)
Action: the action to take, must be one of [{{tool_names}}]
Action Input: the input to the action
Observation: the result of the action
... (repeat)
Thought: I now know the final answer
Final Answer: the final answer to the original input question (be concise)

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

    agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)

    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,
        verbose=False,  # Don't show thinking process in UI
        handle_parsing_errors=True,
        max_iterations=10,
        max_execution_time=180,
        return_intermediate_steps=False
    )
    
    return agent_executor

def format_message(text: str) -> str:
    """Format message for better display in Streamlit."""
    # Format transaction hashes as links
    import re
    tx_pattern = r'0x[a-fA-F0-9]{64}'
    
    def replace_tx(match):
        tx_hash = match.group(0)
        return f"[{tx_hash[:10]}...{tx_hash[-8:]}](https://sepolia.basescan.org/tx/{tx_hash})"
    
    text = re.sub(tx_pattern, replace_tx, text)
    
    # Format addresses as shortened links
    addr_pattern = r'\b0x[a-fA-F0-9]{40}\b'
    
    def replace_addr(match):
        addr = match.group(0)
        return f"`{addr[:8]}...{addr[-6:]}`"
    
    text = re.sub(addr_pattern, replace_addr, text)
    
    return text

def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="Agent Wallet",
        page_icon="💼",
        layout="wide"
    )
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "current_wallet" not in st.session_state:
        st.session_state.current_wallet = load_wallet()
    
    if "user_input" not in st.session_state:
        st.session_state.user_input = ""
    
    # Initialize agent only once
    @st.cache_resource
    def get_agent():
        def get_current_input():
            return st.session_state.get("user_input", "")
        
        def on_wallet_created(address: str):
            save_wallet(address)
            st.session_state.current_wallet = address
        
        return create_agent(get_current_input, on_wallet_created)
    
    if "agent" not in st.session_state:
        st.session_state.agent = get_agent()
        st.session_state.agent_memory = st.session_state.agent.memory
    
    # Sidebar
    with st.sidebar:
        st.title("💼 Agent wallet")
        st.markdown("**Base Sepolia Testnet**")
        st.markdown(f"Backend: `{BACKEND_URL}`")
        
        st.divider()
        
        # Wallet management
        st.subheader("Active Wallet")
        if st.session_state.current_wallet:
            st.success(f"`{st.session_state.current_wallet[:10]}...{st.session_state.current_wallet[-8:]}`")
            if st.button("🔍 Copy Full Address", use_container_width=True):
                st.code(st.session_state.current_wallet, language=None)
                st.info("Address copied!")
        else:
            st.warning("No wallet set")
            st.info("Create a wallet or use 'use wallet 0x...'")
        
        st.divider()
        
        # Quick actions
        st.subheader("Quick Actions")
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.agent_memory.clear()
            st.rerun()
        
        if st.button("🚫 Forget Wallet", use_container_width=True):
            clear_wallet()
            st.session_state.current_wallet = None
            st.success("Wallet cleared!")
            st.rerun()
        
        st.divider()
        
        # Help
        with st.expander("📚 Example Commands"):
            st.markdown("""
**Wallet Operations:**
- "Create a new wallet"
- "Use wallet 0xABC..." (switch active wallet)
- "Show my wallet balance"
- "forget wallet"

**Funding:**
- "Fund my wallet with ETH"
- "Fund wallet 0xABC... with USDC"

**Permissions:**
- "Grant authority with 5 USDC per tx and 20 daily limit"
- "Check policy for my wallet"

**Transfers:**
- "Send 0.5 USDC to 0xDEF..."
            """)
    
    # Main chat interface
    st.title("💬 Agent Wallet")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(format_message(message["content"]))
    
    # Chat input
    user_input = st.chat_input("Ask me anything about your wallet...")
    
    if user_input:
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Process user input
        user_input_lower = user_input.lower()
        
        # Handle special commands
        if user_input_lower.startswith("use wallet "):
            addr = wants_to_use_wallet(user_input)
            if addr and len(addr) == 42:
                save_wallet(addr)
                st.session_state.current_wallet = addr
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"✅ Active wallet set to: `{addr[:10]}...{addr[-8:]}`"
                })
                st.rerun()
            else:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "⚠️ Couldn't find a valid 0x address after 'use wallet'. Please provide a full 42-character address."
                })
                st.rerun()
        
        if user_input_lower in ('forget wallet', 'clear wallet'):
            clear_wallet()
            st.session_state.current_wallet = None
            st.session_state.messages.append({
                "role": "assistant",
                "content": "✅ Local wallet cleared. You can 'create a new wallet' or 'use wallet 0x...'"
            })
            st.rerun()
        
        # Expand "my wallet" references
        processed_input, info = expand_my_wallet(user_input, st.session_state.current_wallet)
        if info:
            st.session_state.messages.append({"role": "assistant", "content": f"ℹ️ {info}"})
        
        # Sanitize addresses
        processed_input, info2 = sanitize_addresses(processed_input, st.session_state.current_wallet)
        if info2:
            st.session_state.messages.append({"role": "assistant", "content": f"ℹ️ {info2}"})
        
        # Store processed input for agent
        st.session_state.user_input = processed_input
        
        # Get agent response with loading state
        with st.chat_message("assistant"):
            try:
                with st.spinner("🤔 Processing your request..."):
                    result = st.session_state.agent.invoke(
                        {"input": processed_input},
                        {"max_execution_time": 180}
                    )
                    
                    output = result.get('output', 'No response generated')
                    
                    # Format and display response
                    formatted_output = format_message(output)
                    st.markdown(formatted_output)
                    
                    # Add to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": output
                    })
                    
                    # Show active wallet info
                    if st.session_state.current_wallet:
                        st.caption(f"💡 Active wallet: `{st.session_state.current_wallet[:10]}...{st.session_state.current_wallet[-8:]}`")
                    
            except Exception as e:
                error_msg = f"❌ Error processing request: {str(e)}\n\n💡 Try rephrasing your request or check the backend connection."
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })

if __name__ == "__main__":
    # Check API key
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "your_google_api_key_here":
        st.error("⚠️ GOOGLE_API_KEY not set. Please set it in .env file.")
        st.info("Get your API key from: https://makersuite.google.com/app/apikey")
        st.stop()
    
    main()

