"""HTTP Server wrapper for MCP Server - for deployment on Easypanel"""

import os
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.responses import JSONResponse
import uvicorn

from .server import app as mcp_app


# Health check endpoint
async def health_check(request):
    """Health check endpoint for container orchestration"""
    return JSONResponse({
        "status": "healthy",
        "service": "odoo-mcp-server",
        "version": "1.0.0"
    })


# Create SSE transport
transport = SseServerTransport("/messages/")


async def handle_sse(scope, receive, send):
    """Handle MCP SSE connections with headers to prevent buffering"""
    
    async def wrapped_send(message):
        if message["type"] == "http.response.start":
            headers = [
                (b"cache-control", b"no-cache"),
                (b"x-accel-buffering", b"no"),
                (b"connection", b"keep-alive"),
            ]
            # Add existing headers from transport if not present
            existing_keys = {h[0] for h in headers}
            for k, v in message.get("headers", []):
                if k not in existing_keys:
                    headers.append((k, v))
            message["headers"] = headers
            
        await send(message)

    async with transport.connect_sse(
        scope, receive, wrapped_send
    ) as streams:
        import sys
        try:
            print(f"[MCP] Starting mcp_app.run()...", file=sys.stderr)
            await mcp_app.run(
                streams[0], streams[1],
                mcp_app.create_initialization_options()
            )
            print(f"[MCP] mcp_app.run() completed normally.", file=sys.stderr)
        except Exception as e:
            print(f"[MCP ERROR] mcp_app.run() failed: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            raise

# Create nested /sse app to handle both SSE stream and messages
from starlette.applications import Starlette as NestedStarlette

sse_sub_app = NestedStarlette(
    debug=True,
    routes=[
        # Messages endpoint MUST come before the root to match first
        Mount("/messages", app=transport.handle_post_message),
        # Root handles the SSE stream
        Route("/", endpoint=lambda request: None),  # placeholder, actual handled below
    ]
)

# Actually, Starlette Mount doesn't work well for this pattern.
# Let's use a custom ASGI app that routes based on path:

async def sse_router(scope, receive, send):
    """Custom router for /sse/* paths"""
    import sys
    path = scope.get("path", "")
    method = scope.get("method", "")
    print(f"[SSE Router] path={path}, method={method}", file=sys.stderr)
    
    # If path contains /messages, delegate to post handler
    if "/messages" in path:
        print(f"[SSE Router] Routing to POST handler", file=sys.stderr)
        await transport.handle_post_message(scope, receive, send)
    else:
        # Otherwise, it's the SSE stream (root of /sse mount)
        print(f"[SSE Router] Routing to SSE handler", file=sys.stderr)
        await handle_sse(scope, receive, send)


# ============================================================================
# Streamable HTTP Transport for n8n compatibility
# ============================================================================
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
import json
import asyncio
from io import BytesIO


async def handle_streamable_http(request: Request):
    """
    Handle Streamable HTTP MCP requests (for n8n).
    This is a simpler request/response pattern than SSE.
    """
    import sys
    
    method = request.method
    print(f"[Streamable HTTP] {method} /mcp", file=sys.stderr)
    
    if method == "GET":
        # Return server info for discovery
        return JSONResponse({
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "odoo-mcp-server",
                    "version": "1.0.0"
                },
                "capabilities": {
                    "tools": {}
                }
            }
        })
    
    if method == "POST":
        try:
            body = await request.json()
            print(f"[Streamable HTTP] Request: {json.dumps(body)[:200]}", file=sys.stderr)
            
            # Create in-memory streams for MCP communication
            request_queue = asyncio.Queue()
            response_queue = asyncio.Queue()
            
            # Put the incoming request in the queue
            await request_queue.put(body)
            
            # Create stream wrappers
            class RequestStream:
                async def __aiter__(self):
                    while True:
                        try:
                            msg = await asyncio.wait_for(request_queue.get(), timeout=0.1)
                            yield msg
                        except asyncio.TimeoutError:
                            break
            
            class ResponseStream:
                def __init__(self):
                    self.messages = []
                
                async def send(self, msg):
                    self.messages.append(msg)
                    await response_queue.put(msg)
            
            read_stream = RequestStream()
            write_stream = ResponseStream()
            
            # Run MCP for single request/response
            async def run_mcp():
                try:
                    # Process single message
                    async for msg in read_stream:
                        # Handle the message based on method
                        method_name = msg.get("method", "")
                        msg_id = msg.get("id")
                        
                        # Handle notifications (no response needed)
                        if method_name.startswith("notifications/"):
                            # Notifications don't require a response, but n8n expects one
                            # Just acknowledge with empty result
                            if msg_id is not None:
                                response = {
                                    "jsonrpc": "2.0",
                                    "id": msg_id,
                                    "result": {}
                                }
                                await write_stream.send(response)
                            continue
                        
                        if method_name == "initialize":
                            # Return server capabilities
                            response = {
                                "jsonrpc": "2.0",
                                "id": msg_id,
                                "result": {
                                    "protocolVersion": "2024-11-05",
                                    "serverInfo": {
                                        "name": "odoo-mcp-server",
                                        "version": "1.0.0"
                                    },
                                    "capabilities": {
                                        "tools": {}
                                    }
                                }
                            }
                            await write_stream.send(response)
                        
                        elif method_name == "tools/list":
                            # Import the tool definitions directly from server module
                            from .server import list_tools as get_tools_func
                            tools = await get_tools_func()
                            tools_list = []
                            for tool in tools:
                                tools_list.append({
                                    "name": tool.name,
                                    "description": tool.description,
                                    "inputSchema": tool.inputSchema
                                })
                            response = {
                                "jsonrpc": "2.0",
                                "id": msg_id,
                                "result": {"tools": tools_list}
                            }
                            await write_stream.send(response)
                        
                        elif method_name == "tools/call":
                            # Call the tool
                            params = msg.get("params", {})
                            tool_name = params.get("name", "")
                            tool_args = params.get("arguments", {})
                            
                            try:
                                # Import call_tool from server module
                                from .server import call_tool as call_tool_func
                                result = await call_tool_func(tool_name, tool_args)
                                # Extract text from result
                                text_content = ""
                                for item in result:
                                    if hasattr(item, 'text'):
                                        text_content += item.text
                                
                                response = {
                                    "jsonrpc": "2.0",
                                    "id": msg_id,
                                    "result": {
                                        "content": [{"type": "text", "text": text_content}]
                                    }
                                }
                            except Exception as e:
                                response = {
                                    "jsonrpc": "2.0",
                                    "id": msg_id,
                                    "error": {"code": -32000, "message": str(e)}
                                }
                            await write_stream.send(response)
                        
                        else:
                            # Unknown method
                            response = {
                                "jsonrpc": "2.0",
                                "id": msg_id,
                                "error": {"code": -32601, "message": f"Method not found: {method_name}"}
                            }
                            await write_stream.send(response)
                
                except Exception as e:
                    print(f"[Streamable HTTP ERROR] {e}", file=sys.stderr)
                    import traceback
                    traceback.print_exc(file=sys.stderr)
            
            await run_mcp()
            
            # Get response
            if write_stream.messages:
                response_msg = write_stream.messages[0]
                print(f"[Streamable HTTP] Response: {json.dumps(response_msg)[:200]}", file=sys.stderr)
                return JSONResponse(response_msg)
            else:
                return JSONResponse({"jsonrpc": "2.0", "error": {"code": -32000, "message": "No response"}})
        
        except Exception as e:
            print(f"[Streamable HTTP ERROR] {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return JSONResponse(
                {"jsonrpc": "2.0", "error": {"code": -32000, "message": str(e)}},
                status_code=500
            )
    
    return JSONResponse({"error": "Method not allowed"}, status_code=405)


# Create HTTP application
http_app = Starlette(
    debug=True,
    routes=[
        Route("/", health_check),
        Route("/health", health_check),
        Mount("/sse", app=sse_router),
        Route("/mcp", handle_streamable_http, methods=["GET", "POST"]),
    ]
)


def main():
    """Run HTTP server"""
    port = int(os.getenv("MCP_PORT", "3000"))
    host = os.getenv("MCP_HOST", "0.0.0.0")

    print(f"Starting Odoo MCP HTTP Server on {host}:{port}")
    print(f"Health check: http://{host}:{port}/health")
    print(f"MCP SSE endpoint: http://{host}:{port}/sse")
    print(f"MCP Messages endpoint: http://{host}:{port}/messages/")

    uvicorn.run(
        http_app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
