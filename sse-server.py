#!/usr/bin/env python3
"""
Simple MCP Server with HTTP serving and get_tasklist tool
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid
import signal

from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
import uvicorn
from pydantic import BaseModel

from mcp import ClientSession, StdioServerParameters
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    TextContent,
    Tool,
    INVALID_PARAMS,
    INTERNAL_ERROR
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample task data organized by category
SAMPLE_TASKS = {
    "work": [
        {"id": 1, "title": "Complete project proposal", "status": "pending", "priority": "high", "due_date": "2024-01-15"},
        {"id": 2, "title": "Review code changes", "status": "in_progress", "priority": "medium", "due_date": "2024-01-12"},
        {"id": 3, "title": "Team meeting preparation", "status": "completed", "priority": "low", "due_date": "2024-01-10"},
        {"id": 4, "title": "Update documentation", "status": "pending", "priority": "medium", "due_date": "2024-01-20"}
    ],
    "personal": [
        {"id": 5, "title": "Grocery shopping", "status": "pending", "priority": "medium", "due_date": "2024-01-13"},
        {"id": 6, "title": "Doctor appointment", "status": "completed", "priority": "high", "due_date": "2024-01-08"},
        {"id": 7, "title": "Call family", "status": "pending", "priority": "low", "due_date": "2024-01-14"},
        {"id": 8, "title": "Exercise routine", "status": "in_progress", "priority": "medium", "due_date": "2024-01-11"}
    ],
    "learning": [
        {"id": 9, "title": "Read Python book chapter 5", "status": "in_progress", "priority": "medium", "due_date": "2024-01-16"},
        {"id": 10, "title": "Complete online course module", "status": "pending", "priority": "high", "due_date": "2024-01-18"},
        {"id": 11, "title": "Practice coding exercises", "status": "completed", "priority": "low", "due_date": "2024-01-09"}
    ],
    "home": [
        {"id": 12, "title": "Fix leaky faucet", "status": "pending", "priority": "high", "due_date": "2024-01-17"},
        {"id": 13, "title": "Organize garage", "status": "pending", "priority": "low", "due_date": "2024-01-25"},
        {"id": 14, "title": "Plant new flowers", "status": "completed", "priority": "medium", "due_date": "2024-01-05"}
    ]
}

# Create MCP Server instance
server = Server("mcp-sse-server")

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="get_tasklist",
            description="Get a list of tasks filtered by category",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "The category to filter tasks by",
                        "enum": ["work", "personal", "learning", "home", "all"]
                    }
                },
                "required": ["category"]
            }
        ),
        Tool(
            name="test_slack",
            description="Test Slack integration",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls"""
    if name == "test_slack":
        # Handle test_slack tool
        return [
            TextContent(
                type="text",
                text="bingo!"
            )
        ]
    elif name == "get_tasklist":
        # Handle get_tasklist tool
        if "category" not in arguments:
            raise ValueError("Missing required argument: category")
        
        category = arguments["category"].lower()
        
        try:
            if category == "all":
                # Return all tasks from all categories
                all_tasks = []
                for cat, tasks in SAMPLE_TASKS.items():
                    for task in tasks:
                        task_with_category = task.copy()
                        task_with_category["category"] = cat
                        all_tasks.append(task_with_category)
                result_tasks = all_tasks
            elif category in SAMPLE_TASKS:
                # Return tasks for specific category
                result_tasks = [
                    {**task, "category": category} 
                    for task in SAMPLE_TASKS[category]
                ]
            else:
                # Invalid category
                available_categories = list(SAMPLE_TASKS.keys()) + ["all"]
                raise ValueError(f"Invalid category '{category}'. Available categories: {', '.join(available_categories)}")
            
            # Format the response
            response_data = {
                "category": category,
                "total_tasks": len(result_tasks),
                "tasks": result_tasks,
                "timestamp": datetime.now().isoformat()
            }
            
            return [
                TextContent(
                    type="text",
                    text=json.dumps(response_data, indent=2)
                )
            ]
            
        except Exception as e:
            logger.error(f"Error in get_tasklist: {str(e)}")
            raise ValueError(f"Error retrieving tasks: {str(e)}")
    else:
        raise ValueError(f"Unknown tool: {name}")

# FastAPI app for HTTP serving
app = FastAPI(
    title="MCP SSE Server",
    description="A simple MCP server with HTTP serving and task management",
    version="0.1.0"
)

class TaskListRequest(BaseModel):
    category: str

@app.get("/")
async def root():
    """Root endpoint with server information"""
    return {
        "name": "MCP SSE Server",
        "version": "0.1.0",
        "description": "A simple MCP server with HTTP serving and task management",
        "available_endpoints": [
            "/",
            "/health",
            "/tools",
            "/tasks/{category}",
            "/mcp/sse",
            "/mcp",
            "/mcp/ws"
        ],
        "mcp_endpoints": {
            "sse": "/mcp/sse",
            "jsonrpc": "/mcp",
            "websocket": "/mcp/ws"
        },
        "available_tools": [
            {
                "name": "get_tasklist",
                "description": "Get a list of tasks filtered by category",
                "categories": ["work", "personal", "learning", "home", "all"]
            },
            {
                "name": "test_slack",
                "description": "Test Slack integration"
            }
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/tools")
async def list_tools():
    """List available MCP tools"""
    tools = await handle_list_tools()
    return {"tools": [tool.model_dump() for tool in tools]}

@app.get("/tasks/{category}")
async def get_tasks(category: str):
    """Get tasks by category via HTTP"""
    try:
        result = await handle_call_tool("get_tasklist", {"category": category})
        return json.loads(result[0].text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in HTTP get_tasks: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/mcp/sse")
async def mcp_sse_endpoint(request: Request):
    """Server-Sent Events endpoint for MCP communication"""
    
    # Store the request body for processing
    body = await request.body()
    
    if body:
        try:
            message = json.loads(body.decode())
            logger.info(f"Received MCP request: {message}")
            
            method = message.get("method")
            request_id = message.get("id")
            params = message.get("params", {})
            
            # Handle requests that expect responses
            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {
                                "listChanged": True
                            }
                        },
                        "serverInfo": {
                            "name": "mcp-sse-server",
                            "version": "0.1.0"
                        }
                    }
                }
                return response
                
            elif method == "tools/list":
                # Manually construct tools response to avoid any serialization issues
                tools_data = [
                    {
                        "name": "get_tasklist",
                        "description": "Get a list of tasks filtered by category",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "category": {
                                    "type": "string",
                                    "description": "The category to filter tasks by",
                                    "enum": ["work", "personal", "learning", "home", "all"]
                                }
                            },
                            "required": ["category"]
                        }
                    },
                    {
                        "name": "test_slack",
                        "description": "Test Slack integration",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                ]
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": tools_data
                    }
                }
                logger.info(f"Sending tools/list response: {json.dumps(response, indent=2)}")
                return response
                
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                try:
                    result = await handle_call_tool(tool_name, arguments)
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "content": [content.model_dump() for content in result]
                        }
                    }
                    return response
                except Exception as e:
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": str(e)
                        }
                    }
                    return error_response
                    
            # Handle notifications (no response expected)
            elif method == "notifications/initialized":
                # Return 202 Accepted for notifications
                return Response(status_code=202)
                
            else:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
                return error_response
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in request body: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                }
            }
            return error_response
    else:
        # No request body - return error
        return Response(status_code=400, content="Request body required")

@app.get("/mcp/sse")
async def mcp_sse_get_endpoint():
    """GET version of SSE endpoint for server-initiated messages"""
    
    async def event_stream():
        try:
            logger.info("MCP SSE GET connection established")
            
            # Send server capabilities immediately
            server_info = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {
                            "listChanged": True
                        }
                    },
                    "serverInfo": {
                        "name": "mcp-sse-server",
                        "version": "0.1.0"
                    }
                }
            }
            yield f"data: {json.dumps(server_info)}\n\n"
            
            # Send available tools immediately
            tools = await handle_list_tools()
            tools_notification = {
                "jsonrpc": "2.0",
                "method": "notifications/tools_changed", 
                "params": {
                    "tools": [tool.model_dump() for tool in tools]
                }
            }
            yield f"data: {json.dumps(tools_notification)}\n\n"
            
            # Keep connection alive
            while True:
                await asyncio.sleep(30)
                heartbeat = {
                    "jsonrpc": "2.0",
                    "method": "notifications/ping",
                    "params": {
                        "timestamp": datetime.now().isoformat()
                    }
                }
                yield f"data: {json.dumps(heartbeat)}\n\n"
                
        except asyncio.CancelledError:
            logger.info("MCP SSE GET connection cancelled")
            return
        except Exception as e:
            logger.error(f"Error in SSE GET stream: {e}")
            error_msg = {
                "jsonrpc": "2.0", 
                "method": "notifications/error",
                "params": {
                    "error": str(e)
                }
            }
            yield f"data: {json.dumps(error_msg)}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS", 
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "X-Accel-Buffering": "no"
        }
    )

# Add a proper MCP endpoint that handles requests and responses
@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """Handle MCP JSON-RPC requests"""
    try:
        body = await request.body()
        message = json.loads(body.decode())
        logger.info(f"Received MCP request: {message}")
        
        method = message.get("method")
        request_id = message.get("id")
        params = message.get("params", {})
        
        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {
                            "listChanged": True
                        }
                    },
                    "serverInfo": {
                        "name": "mcp-sse-server",
                        "version": "0.1.0"
                    }
                }
            }
            return response
            
        elif method == "tools/list":
            # Manually construct tools response
            tools_data = [
                {
                    "name": "get_tasklist",
                    "description": "Get a list of tasks filtered by category",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "The category to filter tasks by",
                                "enum": ["work", "personal", "learning", "home", "all"]
                            }
                        },
                        "required": ["category"]
                    }
                },
                {
                    "name": "test_slack",
                    "description": "Test Slack integration",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            ]
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": tools_data
                }
            }
            return response
            
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            try:
                result = await handle_call_tool(tool_name, arguments)
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [content.model_dump() for content in result]
                    }
                }
                return response
            except Exception as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }
                return error_response
        else:
            error_response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
            return error_response
            
    except Exception as e:
        logger.error(f"Error in MCP endpoint: {e}")
        return {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32700,
                "message": "Parse error"
            }
        }

# Add CORS options handler
@app.options("/mcp/sse")
async def mcp_sse_options():
    """Handle CORS preflight for SSE endpoint"""
    return Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": "86400"
        }
    )

@app.options("/mcp")
async def mcp_options():
    """Handle CORS preflight for MCP endpoint"""
    return Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Max-Age": "86400"
        }
    )

# Add WebSocket endpoint for MCP
@app.websocket("/mcp/ws")
async def mcp_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for MCP communication"""
    await websocket.accept()
    logger.info("MCP WebSocket connection established")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            logger.info(f"Received WebSocket message: {data}")
            
            try:
                message = json.loads(data)
                method = message.get("method")
                request_id = message.get("id")
                params = message.get("params", {})
                
                if method == "initialize":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {
                                "tools": {}
                            },
                            "serverInfo": {
                                "name": "mcp-sse-server",
                                "version": "0.1.0"
                            }
                        }
                    }
                    await websocket.send_text(json.dumps(response))
                    
                elif method == "tools/list":
                    tools = await handle_list_tools()
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "tools": [tool.model_dump() for tool in tools]
                        }
                    }
                    await websocket.send_text(json.dumps(response))
                    
                elif method == "tools/call":
                    tool_name = params.get("name")
                    arguments = params.get("arguments", {})
                    
                    try:
                        result = await handle_call_tool(tool_name, arguments)
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {
                                "content": [content.model_dump() for content in result]
                            }
                        }
                        await websocket.send_text(json.dumps(response))
                    except Exception as e:
                        error_response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32603,
                                "message": str(e)
                            }
                        }
                        await websocket.send_text(json.dumps(error_response))
                        
                else:
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        }
                    }
                    await websocket.send_text(json.dumps(error_response))
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in WebSocket message: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error"
                    }
                }
                await websocket.send_text(json.dumps(error_response))
                
    except WebSocketDisconnect:
        logger.info("MCP WebSocket connection disconnected")
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {e}")

async def run_mcp_server():
    """Run the MCP server using stdio transport"""
    from mcp.server.stdio import stdio_server
    from mcp.server.lowlevel import NotificationOptions
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-sse-server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

def main():
    """Main entry point"""
    import sys
    
    def signal_handler(signum, frame):
        """Handle shutdown signals"""
        logger.info("Received shutdown signal, forcing exit...")
        sys.exit(0)
    
    # Register signal handlers for Windows
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--mcp":
        # Run as MCP server with stdio transport
        asyncio.run(run_mcp_server())
    else:
        # Run as HTTP server
        logger.info("Starting HTTP server on http://localhost:8000")
        logger.info("Available endpoints:")
        logger.info("  GET  /              - Server information")
        logger.info("  GET  /health        - Health check")
        logger.info("  GET  /tools         - List MCP tools")
        logger.info("  GET  /tasks/{category} - Get tasks by category")
        logger.info("  POST /mcp/sse       - MCP Server-Sent Events")
        logger.info("")
        logger.info("Available task categories: work, personal, learning, home, all")
        logger.info("")
        logger.info("To run as MCP server: python sse-server.py --mcp")
        logger.info("Press Ctrl+C to stop the server")
        
        try:
            uvicorn.run(
                app,
                host="127.0.0.1",  # Bind to localhost only instead of 0.0.0.0
                port=8000,
                log_level="info",
                access_log=False,  # Reduce noise in logs
                server_header=False,  # Reduce server header info
                timeout_keep_alive=5,  # Shorter keep-alive timeout
                timeout_graceful_shutdown=2  # Shorter graceful shutdown timeout
            )
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
            sys.exit(0)

if __name__ == "__main__":
    main()
