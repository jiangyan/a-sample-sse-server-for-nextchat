# MCP SSE Server

A simple Model Context Protocol (MCP) server with HTTP serving capabilities and a `get_tasklist` tool for task management.

## Features

- **MCP Server**: Implements the Model Context Protocol with a `get_tasklist` tool
- **HTTP API**: RESTful endpoints for easy integration
- **Server-Sent Events**: SSE endpoint for real-time communication
- **Task Management**: Sample task data organized by categories
- **Dual Mode**: Can run as either an MCP server or HTTP server

## Installation

1. Install dependencies:
```cmd
pip install -e .
```

## Usage

### Running as HTTP Server (Default)

```cmd
python sse-server.py
```

The server will start on `http://localhost:8000` with the following endpoints:

- `GET /` - Server information
- `GET /health` - Health check
- `GET /tools` - List available MCP tools
- `GET /tasks/{category}` - Get tasks by category
- `POST /mcp/sse` - Server-Sent Events endpoint

### Running as MCP Server

```cmd
python sse-server.py --mcp
```

This runs the server in MCP mode using stdio transport for integration with MCP clients.

## API Endpoints

### GET /tasks/{category}

Get tasks filtered by category.

**Available categories:**
- `work` - Work-related tasks
- `personal` - Personal tasks
- `learning` - Learning and education tasks
- `home` - Home and household tasks
- `all` - All tasks from all categories

**Example:**
```cmd
curl http://localhost:8000/tasks/work
```

**Response:**
```json
{
  "category": "work",
  "total_tasks": 4,
  "tasks": [
    {
      "id": 1,
      "title": "Complete project proposal",
      "status": "pending",
      "priority": "high",
      "due_date": "2024-01-15",
      "category": "work"
    }
  ],
  "timestamp": "2024-01-11T10:30:00"
}
```

## MCP Tool: get_tasklist

The MCP server provides a single tool called `get_tasklist` that accepts a category argument.

**Tool Schema:**
```json
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
}
```

## Sample Data

The server includes sample task data across four categories:

- **Work**: Project proposals, code reviews, meetings, documentation
- **Personal**: Shopping, appointments, family calls, exercise
- **Learning**: Reading, courses, coding practice
- **Home**: Repairs, organization, gardening

Each task includes:
- `id`: Unique identifier
- `title`: Task description
- `status`: pending, in_progress, or completed
- `priority`: low, medium, or high
- `due_date`: Target completion date
- `category`: Task category (added in responses)

## Development

### Project Structure

```
mcp-sse-server/
├── sse-server.py      # Main server implementation
├── pyproject.toml     # Project configuration
├── README.md          # This file
└── .gitignore         # Git ignore rules
```

### Testing the Server

1. Start the HTTP server:
```cmd
python sse-server.py
```

2. Test the endpoints:
```cmd
# Get server info
curl http://localhost:8000/

# Get work tasks
curl http://localhost:8000/tasks/work

# Get all tasks
curl http://localhost:8000/tasks/all

# Check health
curl http://localhost:8000/health

# List MCP tools
curl http://localhost:8000/tools
```

3. Test MCP mode (requires MCP client):
```cmd
python sse-server.py --mcp
```

## Dependencies

- `mcp>=1.0.0` - Model Context Protocol implementation
- `fastapi>=0.104.0` - Web framework for HTTP API
- `uvicorn>=0.24.0` - ASGI server
- `pydantic>=2.5.0` - Data validation
- `httpx>=0.25.0` - HTTP client library

## License

This project is open source and available under the MIT License.
