"""Main agent entry point with Gemini and conversation memory."""
import os, re
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

if not GOOGLE_API_KEY or GOOGLE_API_KEY == "your_google_api_key_here":
    print("Warning: GOOGLE_API_KEY not set. Please set it in .env file.")
    print("Get your API key from: https://makersuite.google.com/app/apikey")

ADDR_RE = re.compile(r"\b0x[a-fA-F0-9]{40}\b")

def extract_addresses(text: str):
    return ADDR_RE.findall(text or "")

def wants_to_create(text: str) -> bool:
    """
    Robust create intent detector:
    Matches: create/open/generate/make/spin up/set up/build/new (wallet/account/address)
    """
    t = (text or "").lower()
    patterns = [
        r"\bcreate\b.*\b(wallet|account|address)\b",
        r"\bopen\b.*\b(wallet|account)\b",
        r"\bmake\b.*\b(wallet|account|address)\b",
        r"\bspin\s*up\b.*\b(wallet|account)\b",
        r"\bset\s*up\b.*\b(wallet|account)\b",
        r"\bgenerate\b.*\b(wallet|account|address)\b",
        r"\bnew\b.*\b(wallet|account|address)\b",
        r"\bbuild\b.*\b(wallet|account)\b",
    ]
    import re as _re
    return any(_re.search(p, t) for p in patterns)

def wants_to_use_wallet(text: str) -> str | None:
    t = (text or "").lower()
    if "use wallet" in t or "switch to wallet" in t or "set wallet" in t:
        addrs = extract_addresses(text)
        return addrs[0] if addrs else None
    return None

def expand_my_wallet(text: str, current_wallet: str | None) -> tuple[str, str | None]:
    t = text
    info = None
    if current_wallet:
        t = t.replace("my wallet", f"wallet {current_wallet}")
        t = t.replace("My wallet", f"wallet {current_wallet}")
        t = t.replace("this wallet", f"wallet {current_wallet}")
        t = t.replace("This wallet", f"wallet {current_wallet}")
    else:
        if "my wallet" in text.lower() or "this wallet" in text.lower():
            info = ("No stored wallet found. Please 'create a new wallet' or say "
                    "'use wallet 0x...' to set it explicitly.")
    return t, info

def sanitize_addresses(text: str, current_wallet: str | None) -> tuple[str, str | None]:
    info = None
    addrs = extract_addresses(text)
    if addrs and current_wallet:
        for a in addrs:
            if a != current_wallet:
                info = (f"Ignoring external address {a}. Using stored wallet {current_wallet}. "
                        f"To switch, type: use wallet {a}")
                break
    return text, info

def create_agent_with_memory(get_current_input, on_wallet_created):
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
        on_wallet_created=on_wallet_created,   # <-- NEW: persist right when created
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
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=10,
        max_execution_time=180,
        return_intermediate_steps=False
    )
    return agent_executor

def main():
    print("=" * 60)
    print("CDP Wallet Agent (Gemini + LangChain)")
    print("=" * 60)
    print(f"\n✓ Connected to backend: {BACKEND_URL}")
    print("✓ Network: Base Sepolia (Testnet)")
    print("\nType 'quit', 'exit', or 'q' to exit")
    print("Type 'clear' to clear conversation history")
    print("Type 'help' for command examples\n")

    last_user_input = {"text": ""}
    current_wallet_ref = {"id": load_wallet()}

    def get_current_input():
        return last_user_input["text"]

    def on_wallet_created(address: str):
        # Persist and update local memory immediately
        save_wallet(address)
        current_wallet_ref["id"] = address

    agent = create_agent_with_memory(get_current_input, on_wallet_created)

    if current_wallet_ref["id"]:
        print(f"✓ Loaded stored wallet: {current_wallet_ref['id']}")

    while True:
        try:
            raw = input("\n🔵 You: ")
            user_input = raw.strip("\n\r")
            last_user_input["text"] = raw

            if not user_input:
                continue

            low = user_input.lower()
            if low in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break

            if low == 'clear':
                agent.memory.clear()
                print("✓ Conversation history cleared (local wallet preserved)")
                continue

            if low.startswith("use wallet "):
                addr = wants_to_use_wallet(user_input)
                if addr and len(addr) == 42:
                    save_wallet(addr)
                    current_wallet_ref["id"] = addr
                    print(f"✓ Active wallet set to: {addr}")
                else:
                    print("⚠️ Couldn't find a valid 0x… address after 'use wallet'.")
                continue

            if low in ('forget wallet', 'clear wallet'):
                clear_wallet()
                current_wallet_ref["id"] = None
                print("✓ Local wallet cleared. You can 'create a new wallet' or 'use wallet 0x…'")
                continue

            if low == 'help':
                print("""
📚 Example Commands:

Wallet Operations:
  • "Create a new wallet"
  • "Use wallet 0xABC..."     (switch active wallet explicitly)
  • "Show my wallet balance"  (uses stored wallet)
  • "forget wallet"           (clears local wallet)

Funding:
  • "Fund my wallet with ETH"
  • "Fund wallet 0xABC... with USDC"

Permissions:
  • "Grant authority with 5 USDC per tx and 20 daily limit"
  • "Check policy for my wallet"

Transfers:
  • "Send 0.5 USDC to 0xDEF..."

Rules:
  • The agent never switches wallets unless you say 'use wallet 0x...'
  • If you include other addresses, they are treated as recipients only
                """)
                continue

            # Expand "my wallet"
            user_input, info1 = expand_my_wallet(user_input, current_wallet_ref["id"])
            # Warn if other addresses appear (we will not switch)
            user_input, info2 = sanitize_addresses(user_input, current_wallet_ref["id"])

            if info1: print(f"ℹ️ {info1}")
            if info2: print(f"ℹ️ {info2}")

            # Run agent
            result = agent.invoke({"input": user_input}, {"max_execution_time": 60})
            output = result.get('output', 'No response generated')

            print(f"\n🤖 Agent: {output}")

            # Always display the currently stored wallet after each turn
            if current_wallet_ref["id"]:
                print(f"\n💡 Active wallet: {current_wallet_ref['id']}")

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {str(e)}")
            print("💡 Type 'clear' to reset or 'quit' to exit")

if __name__ == "__main__":
    main()
