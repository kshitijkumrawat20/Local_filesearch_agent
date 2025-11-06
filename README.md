# AI File Search Agent

An intelligent Streamlit-based application that helps you find and manage files on Windows systems using AI agents powered by LangGraph and GROQ LLM.

## Features

- 🔍 **Smart File Search**: AI-powered file and folder discovery
- 🤖 **Interactive Agent**: Conversational interface with context awareness  
- 🔧 **Tool Integration**: File management and shell command capabilities
- 🤝 **Human Assistance**: Agent can request help when needed
- 💬 **Chat Interface**: User-friendly Streamlit web interface
- 🗂️ **Directory Navigation**: Systematic exploration of file structures

## Project Structure

```
ai_agents_project/
├── agents/
│   └── file_search_agent.py     # Main AI agent implementation
├── tools/
│   └── file_tools.py            # File management and shell tools
├── utils/
│   └── state_manager.py         # State management utilities
├── config/
│   └── settings.py              # Configuration settings
├── ui/
│   └── components.py            # Streamlit UI components
├── app.py                       # Main Streamlit application
├── requirements.txt             # Python dependencies
├── .env.template               # Environment variables template
└── README.md                   # This file
```

## Prerequisites

- Python 3.8 or higher
- Windows operating system
- GROQ API key ([Get one here](https://groq.com/))

## Installation

1. **Clone or download the project**:
   ```bash
   cd ai_agents_project
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   - Copy `.env.template` to `.env`
   - Edit `.env` and add your GROQ API key:
     ```
     GROQ_API_KEY=your_actual_api_key_here
     ```

## Usage

1. **Start the application**:
   ```bash
   streamlit run app.py
   ```

2. **Open your browser** to the URL shown (typically `http://localhost:8501`)

3. **Configure settings** in the sidebar:
   - Set your preferred root directory for searches
   - Choose a unique thread ID for conversation tracking

4. **Start chatting** with the AI agent:
   - "Find my profile picture"
   - "Look for Excel files in Documents"
   - "Show me folders in Desktop"
   - "Open the latest report"

## How It Works

### Core Components

- **FileSearchAgent**: The main AI agent that orchestrates file search operations
- **File Tools**: Integrated tools for file management, shell operations, and file opening
- **State Manager**: Handles conversation state and memory management
- **Streamlit UI**: Provides an intuitive chat interface

### Agent Capabilities

The AI agent can:
- Navigate Windows directory structures intelligently
- Use file management tools to list directory contents
- Execute shell commands to interact with the file system
- Open files using their default applications
- Request human assistance when encountering ambiguous situations
- Maintain conversation context across multiple interactions

### Human-in-the-Loop

When the agent encounters situations requiring clarification, it will:
1. Pause execution and request human assistance
2. Present the human with relevant context and options
3. Wait for human input through the Streamlit interface
4. Continue processing with the provided guidance

## Configuration

### Environment Variables

- `GROQ_API_KEY`: Your GROQ API key (required)
- `DEFAULT_ROOT_DIR`: Override default root directory (optional)
- `LLM_MODEL`: Override default LLM model (optional)

### Application Settings

Modify `config/settings.py` to customize:
- LLM model and parameters
- Default directories
- UI configuration
- Tool settings

## Development

### Adding New Tools

1. Create tool functions in `tools/file_tools.py`
2. Use the `@tool` decorator from LangChain
3. Add tools to the agent's tool list
4. Update documentation

### Customizing the UI

1. Modify components in `ui/components.py`
2. Update the main application logic in `app.py`
3. Adjust styling and layout as needed

### Extending Agent Capabilities

1. Enhance the `FileSearchAgent` class in `agents/file_search_agent.py`
2. Add new state management features in `utils/state_manager.py`
3. Create additional specialized agents as needed

## Troubleshooting

### Common Issues

1. **API Key Errors**:
   - Ensure your GROQ API key is correctly set in the `.env` file
   - Verify the key is valid and has sufficient credits

2. **File Permission Issues**:
   - Run the application with appropriate permissions
   - Consider adjusting the root directory if access is restricted

3. **Tool Execution Errors**:
   - Check that all required dependencies are installed
   - Verify Windows shell commands are available

4. **Memory Issues**:
   - Clear conversation history using the sidebar button
   - Restart the application if needed

### Debug Mode

To enable debug logging, set the environment variable:
```bash
export LANGCHAIN_VERBOSE=true
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source. Please ensure compliance with all dependencies' licenses.

## Acknowledgments

- Built with [LangGraph](https://github.com/langchain-ai/langgraph) for agent workflows
- Powered by [GROQ](https://groq.com/) for fast LLM inference
- UI created with [Streamlit](https://streamlit.io/)
- Uses [LangChain](https://langchain.com/) for tool integration