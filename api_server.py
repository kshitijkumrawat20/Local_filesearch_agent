"""
FastAPI Backend for Local File Search Agent
Runs as a background service - can be accessed by any frontend
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import uvicorn
import logging
import asyncio
from datetime import datetime
import json
import os

from agents.filesearch_agent import FileSearchAgent
from tools.file_tools import FileTools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Local File Search Agent API",
    description="AI-powered file search and document analysis backend",
    version="1.0.0"
)

# CORS middleware - allows frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
file_tools: Optional[FileTools] = None
agent_executor = None
sessions: Dict[str, dict] = {}  # Store session data

# Pydantic models for request/response
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str

class IndexDocumentRequest(BaseModel):
    file_path: str

class IndexDocumentResponse(BaseModel):
    success: bool
    message: str
    file_path: str

class HealthResponse(BaseModel):
    status: str
    version: str
    uptime: str
    indexed_documents: int

class DocumentInfo(BaseModel):
    file_path: str
    filename: str
    chunk_count: int

class ListDocumentsResponse(BaseModel):
    count: int
    documents: List[DocumentInfo]

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize agent and tools on startup"""
    global file_tools, agent_executor
    
    logger.info("=" * 70)
    logger.info("🚀 Starting Local File Search Agent API Server...")
    logger.info("=" * 70)
    
    try:
        # Get API key from environment
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.error("❌ No API key found! Set OPENAI_API_KEY or GROQ_API_KEY")
            raise ValueError("API key required")
        
        # Initialize agent with FileSearchAgent class
        logger.info("🤖 Creating AI agent...")
        agent = FileSearchAgent(api_key=api_key, root_dir="C:\\")
        
        # Store the graph as agent_executor for compatibility
        agent_executor = agent.graph
        
        # Get file_tools from agent
        file_tools = agent.file_tools_instance
        
        logger.info("✅ Backend is ready and listening!")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"❌ Failed to start backend: {e}")
        raise

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global file_tools
    
    logger.info("👋 Shutting down backend...")
    
    if file_tools:
        try:
            file_tools.cleanup_session_vectorstores()
            logger.info("✅ Cleanup completed")
        except Exception as e:
            logger.error(f"⚠️ Cleanup error: {e}")

# Health check endpoint
@app.get("/", response_model=HealthResponse)
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint - verify backend is running"""
    global file_tools
    
    indexed_count = len(file_tools.document_vectorstores) if file_tools else 0
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "uptime": "running",
        "indexed_documents": indexed_count
    }

# Chat endpoint - main interaction
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the AI agent
    
    The agent can:
    - Search files across your system
    - Index and query documents
    - Extract text from images (OCR)
    - Answer questions about your files
    """
    try:
        logger.info(f"💬 Chat request from session '{request.session_id}': {request.message[:50]}...")
        
        if not agent_executor:
            raise HTTPException(status_code=503, detail="Agent not initialized")
        
        # Configure session
        config = {"configurable": {"thread_id": request.session_id}}
        
        # Store session if new
        if request.session_id not in sessions:
            sessions[request.session_id] = {
                "created_at": datetime.now().isoformat(),
                "message_count": 0
            }
        
        sessions[request.session_id]["message_count"] += 1
        
        # Stream agent response
        response_text = ""
        logger.info("🤖 Agent processing...")
        
        for event in agent_executor.stream(
            {"messages": [{"role": "user", "content": request.message}]},
            config=config,
            stream_mode="values"
        ):
            if "messages" in event and len(event["messages"]) > 0:
                last_msg = event["messages"][-1]
                if hasattr(last_msg, 'content'):
                    response_text = last_msg.content
        
        if not response_text:
            response_text = "I apologize, but I couldn't generate a response. Please try rephrasing your question."
        
        logger.info(f"✅ Response generated ({len(response_text)} chars)")
        
        return ChatResponse(
            response=response_text,
            session_id=request.session_id,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"❌ Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

# Index document endpoint
@app.post("/api/index-document", response_model=IndexDocumentResponse)
async def index_document(request: IndexDocumentRequest):
    """
    Index a document for querying
    
    Supports: PDF, DOCX, XLSX, PPTX, TXT, and images (with OCR)
    """
    try:
        logger.info(f"📄 Indexing document: {request.file_path}")
        
        if not file_tools:
            raise HTTPException(status_code=503, detail="File tools not initialized")
        
        result = file_tools.index_document(request.file_path)
        
        # Check if successful
        success = "✅" in result or "Successfully indexed" in result
        
        logger.info(f"{'✅' if success else '❌'} Indexing {'successful' if success else 'failed'}")
        
        return IndexDocumentResponse(
            success=success,
            message=result,
            file_path=request.file_path
        )
        
    except Exception as e:
        logger.error(f"❌ Index error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error indexing document: {str(e)}")

# List indexed documents
@app.get("/api/indexed-documents", response_model=ListDocumentsResponse)
async def list_indexed_documents():
    """Get list of all indexed documents in current session"""
    try:
        if not file_tools:
            raise HTTPException(status_code=503, detail="File tools not initialized")
        
        documents = []
        for file_path, vs_info in file_tools.document_vectorstores.items():
            import os
            documents.append(DocumentInfo(
                file_path=file_path,
                filename=os.path.basename(file_path),
                chunk_count=vs_info['doc_count']
            ))
        
        logger.info(f"📋 Listed {len(documents)} indexed documents")
        
        return ListDocumentsResponse(
            count=len(documents),
            documents=documents
        )
        
    except Exception as e:
        logger.error(f"❌ List error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")

# Clear session
@app.post("/api/clear-session")
async def clear_session(session_id: str = "default"):
    """Clear a specific session's history"""
    try:
        if session_id in sessions:
            del sessions[session_id]
            logger.info(f"🧹 Cleared session: {session_id}")
            return {"success": True, "message": f"Session '{session_id}' cleared"}
        else:
            return {"success": False, "message": f"Session '{session_id}' not found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get session info
@app.get("/api/session-info")
async def get_session_info(session_id: str = "default"):
    """Get information about a session"""
    if session_id in sessions:
        return sessions[session_id]
    else:
        return {"exists": False}

# WebSocket endpoint for real-time streaming (optional, advanced)
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for real-time streaming responses
    Client can send messages and receive streaming responses
    """
    await websocket.accept()
    logger.info("🔌 WebSocket connection established")
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            message = message_data.get("message", "")
            session_id = message_data.get("session_id", "default")
            
            logger.info(f"💬 WebSocket message: {message[:50]}...")
            
            # Send acknowledgment
            await websocket.send_json({
                "type": "status",
                "message": "Processing..."
            })
            
            # Process with agent
            config = {"configurable": {"thread_id": session_id}}
            
            response_text = ""
            for event in agent_executor.stream(
                {"messages": [{"role": "user", "content": message}]},
                config=config,
                stream_mode="values"
            ):
                if "messages" in event and len(event["messages"]) > 0:
                    last_msg = event["messages"][-1]
                    if hasattr(last_msg, 'content'):
                        response_text = last_msg.content
                        
                        # Stream chunks to client
                        await websocket.send_json({
                            "type": "chunk",
                            "content": response_text
                        })
            
            # Send final response
            await websocket.send_json({
                "type": "complete",
                "response": response_text,
                "timestamp": datetime.now().isoformat()
            })
            
    except WebSocketDisconnect:
        logger.info("🔌 WebSocket disconnected")
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass

# Run server
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🚀 Local File Search Agent - FastAPI Backend")
    print("=" * 70)
    print("📍 Server will run at: http://127.0.0.1:8765")
    print("📖 API docs available at: http://127.0.0.1:8765/docs")
    print("=" * 70 + "\n")
    
    uvicorn.run(
        "api_server:app",
        host="127.0.0.1",
        port=8765,
        reload=True,  # Auto-reload on code changes (disable in production)
        log_level="info"
    )
