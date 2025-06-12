#!/usr/bin/env python3
"""
Test script to demonstrate MCP server functionality
"""

import asyncio
import json
import subprocess
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_mcp_server():
    """Test the MCP server functionality"""
    
    # Start the MCP server as a subprocess
    server_params = StdioServerParameters(
        command="python",
        args=["sse-server.py", "--mcp"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()
            
            print("🚀 MCP Server connected successfully!")
            print()
            
            # List available tools
            print("📋 Available tools:")
            tools = await session.list_tools()
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")
                print(f"    Schema: {json.dumps(tool.inputSchema, indent=6)}")
            print()
            
            # Test the get_tasklist tool with different categories
            categories = ["work", "personal", "learning", "home", "all"]
            
            for category in categories:
                print(f"🔍 Testing get_tasklist with category: {category}")
                try:
                    result = await session.call_tool("get_tasklist", {"category": category})
                    
                    if result.content:
                        data = json.loads(result.content[0].text)
                        print(f"  ✅ Success! Found {data['total_tasks']} tasks")
                        
                        # Show first few tasks
                        for i, task in enumerate(data['tasks'][:2]):
                            print(f"    {i+1}. {task['title']} ({task['status']}, {task['priority']} priority)")
                        
                        if len(data['tasks']) > 2:
                            print(f"    ... and {len(data['tasks']) - 2} more tasks")
                    else:
                        print("  ❌ No content returned")
                        
                except Exception as e:
                    print(f"  ❌ Error: {e}")
                
                print()
            
            # Test invalid category
            print("🔍 Testing get_tasklist with invalid category: invalid")
            try:
                result = await session.call_tool("get_tasklist", {"category": "invalid"})
                print("  ❌ Should have failed but didn't")
            except Exception as e:
                print(f"  ✅ Correctly failed with error: {e}")
            
            print()
            
            # Test the test_slack tool
            print("🔍 Testing test_slack tool")
            try:
                result = await session.call_tool("test_slack", {})
                
                if result.content:
                    print(f"  ✅ Success! Response: {result.content[0].text}")
                else:
                    print("  ❌ No content returned")
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
            
            print()
            print("🎉 All tests completed!")

if __name__ == "__main__":
    asyncio.run(test_mcp_server()) 