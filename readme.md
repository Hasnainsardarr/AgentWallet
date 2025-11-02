# Streamlit Frontend Guide

## Overview

A beautiful, modern chat interface for the CDP Wallet Agent built with Streamlit. This frontend provides a ChatGPT-like experience with proper loading states and no verbose "thinking" output.

## Features

✅ **Clean Chat Interface** - ChatGPT-style conversation UI
✅ **No Verbose Output** - Agent thinking process is hidden
✅ **Loading States** - Visual indicators during processing
✅ **Wallet Management** - Sidebar shows active wallet with quick actions
✅ **Message Formatting** - Transaction hashes and addresses are formatted nicely
✅ **Session Memory** - Conversations persist during session
✅ **Responsive Design** - Clean, modern UI with sidebar

## Installation

### 1. Install Python 3.11

```powershell
winget install --id Python.Python.3.11
py -3.11 --version


###Backend Setup

cd <PROJECT_ROOT>/packages/backend 

# Create virtual environment with Python 3.11
py -3.11 -m venv venv

# Activate the virtual environment
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create a .env file with your API keys
# Example:
# GOOGLE_API_KEY=your_google_api_key_here
# CDP_API_KEY_ID=your_cdp_api_key_id
# CDP_API_KEY_SECRET=your_cdp_api_key_secret
# CDP_WALLET_SECRET=your_cdp_wallet_secret
# DATABASE_URL=sqlite:///./wallet_demo.db
# NODE_ENV=development
# JWT_SECRET=dev-secret-change-in-production

# Start the backend 
python -m uvicorn src.app:app --reload --port 8000

Backend will be available at: http://localhost:8000







##Agent setup (make sure backend is running first)
cd <PROJECT_ROOT>/packages/agent

# Create virtual environment with Python 3.11
py -3.11 -m venv myenv

# Activate the virtual environment
myenv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create a .env file with your API keys


# Run the Streamlit frontend
python -m streamlit run src/streamlit_app.py --server.port 8501

Frontend will open in your browser at: http://localhost:8501


## Usage

### Interface Layout

```
┌─────────────────────────────────────────────────────────┐
│  Sidebar                    │  Main Chat Interface      │
│                             │                           │
│  💼 Wallet Agent            │  💬 CDP Wallet Agent Chat │
│  Base Sepolia Testnet       │                           │
│  ─────────────────          │  [Chat messages appear    │
│  Active Wallet               │   here as conversation]  │
│  ✅ 0x4517...9Fd            │                           │
│                             │  [Chat input at bottom]   │
│  Quick Actions              │                           │
│  🗑️ Clear Chat             │                           │
│  🚫 Forget Wallet           │                           │
│                             │                           │
│  📚 Example Commands        │                           │
└─────────────────────────────────────────────────────────┘
```

### Basic Workflow

1. **Create a Wallet**
   ```
   Type: "Create a new wallet"
   ```

2. **Check Balance**
   ```
   Type: "Check my wallet balance"
   ```

3. **Fund Wallet**
   ```
   Type: "Fund my wallet with ETH"
   Type: "Fund my wallet with USDC"
   ```

4. **Send Transfer**
   ```

   Type: "Send 0.5 USDC to 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"

   ```

5. **Grant Authority / Set Policy**
   ```

   Type: "Type: "Grant authority with 5 USDC per tx and 20 daily""
   
   ```






### Sidebar Features

**Active Wallet Section:**
- Shows current active wallet address
- "Copy Full Address" button for easy access

**Quick Actions:**
- **Clear Chat** - Clears conversation history (keeps wallet)
- **Forget Wallet** - Removes active wallet from local storage

**Example Commands:**
- Expandable section with common commands

## Features Explained

### 1. Chat Interface

- **User Messages** - Appear on the right with user avatar
- **Agent Messages** - Appear on the left with assistant avatar
- **Message Formatting**:
  - Transaction hashes → Shortened with BaseScan links
  - Wallet addresses → Shortened format (`0x4517...9Fd`)
  - Markdown support for formatting

### 2. Loading States

The app shows different loading indicators:

- `🤔 Processing your request...` - General processing
- `🔄 Connecting to agent...` - Initial connection
- Status updates during long operations

### 3. Wallet Management

- **Auto-detection** - "my wallet" automatically uses stored wallet
- **Explicit switching** - `use wallet 0x...` to change active wallet
- **Persistent storage** - Wallet persists across sessions

### 4. Error Handling

- Clear error messages with suggestions
- Network errors are caught and displayed nicely
- Backend connection issues are identified

## Customization

### Change Port

Edit `streamlit_app.py` or use command line:

```bash
streamlit run src/streamlit_app.py --server.port 8502
```

### Change Theme

Create `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"
```

### Hide Sidebar

Add to `streamlit_app.py`:

```python
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)
```

## Troubleshooting

### App Won't Start

**Error:** `ModuleNotFoundError: No module named 'streamlit'`

**Solution:**
```bash
pip install streamlit>=1.28.0
```

### Backend Connection Error

**Error:** `Error processing request: Connection refused`

**Solution:**
1. Ensure backend is running on port 8000
2. Check `BACKEND_URL` in `.env` file
3. Verify backend logs for errors

### Wallet Not Loading

**Issue:** Wallet not appearing in sidebar

**Solution:**
1. Check `packages/agent/src/.wallet_local.json` exists
2. Verify wallet format (42 characters, starts with 0x)
3. Use `use wallet 0x...` command to set it manually

### Agent Not Responding

**Issue:** Loading spinner but no response

**Solution:**
1. Check backend is running
2. Verify `GOOGLE_API_KEY` is set in `.env`
3. Check browser console for errors (F12)
4. Look at Streamlit logs in terminal

## Advanced Features

### Keyboard Shortcuts

- `Ctrl/Cmd + Enter` - Send message
- `Escape` - Cancel/clear input

### Streamlit Features Used

- `st.chat_message()` - Chat interface
- `st.chat_input()` - Input field
- `st.spinner()` - Loading indicators
- `st.cache_resource()` - Agent caching
- `st.session_state` - State management
- `st.sidebar` - Side panel

## Architecture

```
streamlit_app.py
├── Agent Integration
│   ├── create_agent() - Creates LangChain agent
│   └── AgentExecutor - Executes agent with memory
├── UI Components
│   ├── Sidebar - Wallet management
│   ├── Chat Interface - Message display
│   └── Input Handler - User input processing
├── Helper Functions
│   ├── expand_my_wallet() - Expands wallet references
│   ├── sanitize_addresses() - Address validation
│   └── format_message() - Message formatting
└── State Management
    ├── Session State - Conversation history
    ├── Wallet State - Active wallet tracking
    └── Agent State - Cached agent instance
```

## Comparison: CLI vs Streamlit

| Feature | CLI (`main.py`) | Streamlit (`streamlit_app.py`) |
|---------|-----------------|--------------------------------|
| **Interface** | Terminal | Web UI |
| **Loading States** | Text only | Visual spinners |
| **Message History** | Session-based | Persistent in session |
| **Wallet Display** | Text | Sidebar with actions |
| **Error Display** | Console output | Formatted error boxes |
| **Transaction Links** | Plain text | Clickable BaseScan links |
| **Verbose Output** | Can be enabled | Always hidden |

## Best Practices

1. **Always Start Backend First**
   - Frontend requires backend to be running
   - Check `http://localhost:8000` before starting Streamlit

2. **Keep Browser Tab Open**
   - Closing tab doesn't kill the app
   - Use Ctrl+C in terminal to stop

3. **Clear Chat When Switching Context**
   - Use "Clear Chat" for new conversations
   - Agent memory is cleared but wallet persists

4. **Monitor Backend Logs**
   - Keep backend terminal visible
   - Check for errors during operations

5. **Use Sidebar for Quick Info**
   - Active wallet always visible
   - Quick actions for common tasks

## Security Notes

⚠️ **Important:**
- This is a **testnet demo** - no real funds
- API keys are stored in `.env` file (never commit!)
- Wallet addresses are stored locally in `.wallet_local.json`
- All transactions are on Base Sepolia testnet

## Next Steps

1. ✅ **Install Streamlit**: `pip install streamlit`
2. ✅ **Start Backend**: `cd packages/backend && python -m uvicorn src.app:app --reload`
3. ✅ **Run Frontend**: `cd packages/agent && streamlit run src/streamlit_app.py`
4. ✅ **Open Browser**: Navigate to `http://localhost:8501`
5. ✅ **Start Chatting**: Type your first command!

## Example Conversation

```
You: Create a new wallet
Agent: ✅ Wallet created successfully:
      Wallet ID: 0x45176516F0ea8a2bE075379aac922b4DE95969Fd
      Address: 0x45176516F0ea8a2bE075379aac922b4DE95969Fd
      Network: base-sepolia

You: Fund my wallet with ETH
Agent: ✅ Testnet funding completed for ETH:
      Transaction: [0x11ce...a523](https://sepolia.basescan.org/tx/0x...)
      Status: Success

You: Check my balance
Agent: 💰 ETH (for gas): 0.0001 ETH
      💵 USDC (to send): 0.0 USDC

You: Send 0.1 USDC to 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0
Agent: ✅ Transfer successful:
      Amount: 0.1 USDC
      Transaction: [0x789...abc](https://sepolia.basescan.org/tx/0x...)
```

---

**Status:** ✅ Ready to use
**Version:** 1.0.0
**Last Updated:** 2024

