"""
MCP Server Implementation
=========================

Full Model Context Protocol server with support for:
- Tools (active operations)
- Resources (read-only data)
- Prompts (templates)
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Union, Awaitable
from datetime import datetime
import json
import uuid
from enum import Enum

from aiohttp import web

from ..common.logger import get_logger, PerformanceTracker
from ..common.exceptions import (
    MCPError,
    ValidationError,
    ProtocolError,
)
from ..transport.json_rpc import (
    JsonRpcRequest,
    JsonRpcResponse,
    JsonRpcError,
    parse_message,
    create_response,
    create_error_response,
    MCPMethods,
    JSONRPC_VERSION,
)

logger = get_logger(__name__)


# ============================================================================
# MCP Primitives
# ============================================================================

@dataclass
class Tool:
    """
    MCP Tool definition.
    
    Tools are active operations that perform actions and return results.
    """
    
    name: str
    description: str
    handler: Callable[..., Awaitable[Any]]
    input_schema: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema or {
                "type": "object",
                "properties": {},
            }
        }


@dataclass
class Resource:
    """
    MCP Resource definition.
    
    Resources are read-only data sources.
    """
    
    uri: str
    name: str
    description: str = ""
    mime_type: str = "application/json"
    handler: Optional[Callable[..., Awaitable[Any]]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP resource format."""
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


@dataclass
class Prompt:
    """
    MCP Prompt definition.
    
    Prompts are templates for agent interactions.
    """
    
    name: str
    description: str
    arguments: List[Dict[str, Any]] = field(default_factory=list)
    template: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MCP prompt format."""
        return {
            "name": self.name,
            "description": self.description,
            "arguments": self.arguments,
        }
    
    def render(self, **kwargs) -> str:
        """Render the prompt with arguments."""
        return self.template.format(**kwargs)


# ============================================================================
# MCP Server
# ============================================================================

class MCPServer:
    """
    Model Context Protocol Server.
    
    Implements the MCP specification with support for:
    - Tools (tools/list, tools/call)
    - Resources (resources/list, resources/read, subscriptions)
    - Prompts (prompts/list, prompts/get)
    - Progress notifications
    """
    
    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        host: str = "localhost",
        port: int = 8000,
    ):
        self.name = name
        self.version = version
        self.host = host
        self.port = port
        
        # MCP primitives
        self._tools: Dict[str, Tool] = {}
        self._resources: Dict[str, Resource] = {}
        self._prompts: Dict[str, Prompt] = {}
        
        # Subscriptions for resources
        self._subscriptions: Dict[str, set] = {}  # uri -> set of client IDs
        
        # Server state
        self._running = False
        self._start_time: Optional[datetime] = None
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        
        # Request handlers
        self._handlers: Dict[str, Callable] = {
            MCPMethods.INITIALIZE: self._handle_initialize,
            MCPMethods.TOOLS_LIST: self._handle_tools_list,
            MCPMethods.TOOLS_CALL: self._handle_tools_call,
            MCPMethods.RESOURCES_LIST: self._handle_resources_list,
            MCPMethods.RESOURCES_READ: self._handle_resources_read,
            MCPMethods.RESOURCES_SUBSCRIBE: self._handle_resources_subscribe,
            MCPMethods.RESOURCES_UNSUBSCRIBE: self._handle_resources_unsubscribe,
            MCPMethods.PROMPTS_LIST: self._handle_prompts_list,
            MCPMethods.PROMPTS_GET: self._handle_prompts_get,
        }
        
        logger.bind(server=name, port=port)
    
    # ========================================================================
    # Registration Methods
    # ========================================================================
    
    def register_tool(self, tool: Tool) -> None:
        """Register a tool with the server."""
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")
    
    def tool(
        self,
        name: str,
        description: str,
        input_schema: Optional[Dict] = None,
    ) -> Callable:
        """
        Decorator to register a tool.
        
        Usage:
            @server.tool("my_tool", "Does something")
            async def my_tool(params):
                return {"result": "done"}
        """
        def decorator(func: Callable) -> Callable:
            tool = Tool(
                name=name,
                description=description,
                handler=func,
                input_schema=input_schema or {},
            )
            self.register_tool(tool)
            return func
        return decorator
    
    def register_resource(self, resource: Resource) -> None:
        """Register a resource with the server."""
        self._resources[resource.uri] = resource
        logger.debug(f"Registered resource: {resource.uri}")
    
    def resource(
        self,
        uri: str,
        name: str,
        description: str = "",
        mime_type: str = "application/json",
    ) -> Callable:
        """
        Decorator to register a resource.
        
        Usage:
            @server.resource("game://state", "Game State")
            async def get_game_state(params):
                return {"state": "running"}
        """
        def decorator(func: Callable) -> Callable:
            resource = Resource(
                uri=uri,
                name=name,
                description=description,
                mime_type=mime_type,
                handler=func,
            )
            self.register_resource(resource)
            return func
        return decorator
    
    def register_prompt(self, prompt: Prompt) -> None:
        """Register a prompt with the server."""
        self._prompts[prompt.name] = prompt
        logger.debug(f"Registered prompt: {prompt.name}")
    
    def register_handler(self, method: str, handler: Callable) -> None:
        """Register a custom method handler."""
        self._handlers[method] = handler
    
    # ========================================================================
    # MCP Protocol Handlers
    # ========================================================================
    
    async def _handle_initialize(self, params: Optional[Dict]) -> Dict[str, Any]:
        """Handle initialize request."""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {"subscribe": True, "listChanged": True},
                "prompts": {"listChanged": True},
            },
            "serverInfo": {
                "name": self.name,
                "version": self.version,
            }
        }
    
    async def _handle_tools_list(self, params: Optional[Dict]) -> Dict[str, Any]:
        """Handle tools/list request."""
        return {
            "tools": [tool.to_dict() for tool in self._tools.values()]
        }
    
    async def _handle_tools_call(self, params: Optional[Dict]) -> Dict[str, Any]:
        """Handle tools/call request."""
        if not params:
            raise ValidationError("Missing params for tools/call")
        
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not tool_name:
            raise ValidationError("Missing tool name")
        
        tool = self._tools.get(tool_name)
        if not tool:
            raise ValidationError(f"Unknown tool: {tool_name}")
        
        # Execute tool
        with PerformanceTracker(f"tool.{tool_name}", logger):
            try:
                result = await tool.handler(arguments)
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result) if isinstance(result, dict) else str(result),
                        }
                    ]
                }
            except Exception as e:
                logger.error(f"Tool execution error: {e}", exc_info=True)
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error: {str(e)}",
                        }
                    ],
                    "isError": True,
                }
    
    async def _handle_resources_list(self, params: Optional[Dict]) -> Dict[str, Any]:
        """Handle resources/list request."""
        return {
            "resources": [res.to_dict() for res in self._resources.values()]
        }
    
    async def _handle_resources_read(self, params: Optional[Dict]) -> Dict[str, Any]:
        """Handle resources/read request."""
        if not params:
            raise ValidationError("Missing params for resources/read")
        
        uri = params.get("uri")
        if not uri:
            raise ValidationError("Missing resource URI")
        
        resource = self._resources.get(uri)
        if not resource:
            raise ValidationError(f"Unknown resource: {uri}")
        
        # Read resource
        if resource.handler:
            content = await resource.handler(params)
        else:
            content = {}
        
        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": resource.mime_type,
                    "text": json.dumps(content) if isinstance(content, dict) else str(content),
                }
            ]
        }
    
    async def _handle_resources_subscribe(self, params: Optional[Dict]) -> Dict[str, Any]:
        """Handle resources/subscribe request."""
        if not params:
            raise ValidationError("Missing params")
        
        uri = params.get("uri")
        if not uri:
            raise ValidationError("Missing resource URI")
        
        if uri not in self._resources:
            raise ValidationError(f"Unknown resource: {uri}")
        
        # Add subscription
        if uri not in self._subscriptions:
            self._subscriptions[uri] = set()
        
        # In a real implementation, we'd track the client
        # For now, just acknowledge
        return {"success": True}
    
    async def _handle_resources_unsubscribe(self, params: Optional[Dict]) -> Dict[str, Any]:
        """Handle resources/unsubscribe request."""
        if not params:
            raise ValidationError("Missing params")
        
        uri = params.get("uri")
        if not uri:
            raise ValidationError("Missing resource URI")
        
        return {"success": True}
    
    async def _handle_prompts_list(self, params: Optional[Dict]) -> Dict[str, Any]:
        """Handle prompts/list request."""
        return {
            "prompts": [prompt.to_dict() for prompt in self._prompts.values()]
        }
    
    async def _handle_prompts_get(self, params: Optional[Dict]) -> Dict[str, Any]:
        """Handle prompts/get request."""
        if not params:
            raise ValidationError("Missing params")
        
        name = params.get("name")
        if not name:
            raise ValidationError("Missing prompt name")
        
        prompt = self._prompts.get(name)
        if not prompt:
            raise ValidationError(f"Unknown prompt: {name}")
        
        # Get arguments for rendering
        arguments = params.get("arguments", {})
        
        try:
            rendered = prompt.render(**arguments)
        except KeyError as e:
            raise ValidationError(f"Missing prompt argument: {e}")
        
        return {
            "description": prompt.description,
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": rendered,
                    }
                }
            ]
        }
    
    # ========================================================================
    # HTTP Server
    # ========================================================================
    
    async def _handle_http_request(self, request: web.Request) -> web.Response:
        """Handle incoming HTTP request."""
        try:
            # Read body
            body = await request.read()
            
            # Parse JSON-RPC message
            message = parse_message(body)
            
            if isinstance(message, JsonRpcError):
                response = create_error_response(None, message)
                return web.json_response(response.to_dict())
            
            if isinstance(message, JsonRpcRequest):
                response = await self._process_request(message)
                
                # Don't respond to notifications
                if message.is_notification:
                    return web.Response(status=204)
                
                return web.json_response(response.to_dict())
            
            # Invalid message
            error = JsonRpcError.invalid_request("Expected request")
            response = create_error_response(None, error)
            return web.json_response(response.to_dict())
            
        except Exception as e:
            logger.exception(f"Request handling error: {e}")
            error = JsonRpcError.internal_error(str(e))
            response = create_error_response(None, error)
            return web.json_response(response.to_dict(), status=500)
    
    async def _process_request(self, request: JsonRpcRequest) -> JsonRpcResponse:
        """Process a single JSON-RPC request."""
        method = request.method
        params = request.params
        
        logger.debug(f"Processing request: {method}", request_id=request.id)
        
        # Find handler
        handler = self._handlers.get(method)
        
        if handler is None:
            error = JsonRpcError.method_not_found(method)
            return create_error_response(request.id, error)
        
        try:
            # Execute handler
            result = await handler(params)
            return create_response(request.id, result)
            
        except ValidationError as e:
            error = JsonRpcError.invalid_params(str(e))
            return create_error_response(request.id, error)
        except MCPError as e:
            error = JsonRpcError(-32000, str(e), e.to_dict())
            return create_error_response(request.id, error)
        except Exception as e:
            logger.exception(f"Handler error: {e}")
            error = JsonRpcError.internal_error(str(e))
            return create_error_response(request.id, error)
    
    async def _handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        uptime = 0.0
        if self._start_time:
            uptime = (datetime.now() - self._start_time).total_seconds()
        
        return web.json_response({
            "status": "healthy",
            "server": self.name,
            "version": self.version,
            "uptime_seconds": uptime,
            "tools_count": len(self._tools),
            "resources_count": len(self._resources),
        })
    
    # ========================================================================
    # Server Lifecycle
    # ========================================================================
    
    async def start(self) -> None:
        """Start the MCP server."""
        if self._running:
            logger.warning("Server already running")
            return
        
        # Create aiohttp app
        self._app = web.Application()
        self._app.router.add_post("/mcp", self._handle_http_request)
        self._app.router.add_get("/health", self._handle_health)
        
        # Create runner
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        
        # Create site
        site = web.TCPSite(self._runner, self.host, self.port)
        await site.start()
        
        self._running = True
        self._start_time = datetime.now()
        
        logger.info(
            f"MCP Server started",
            host=self.host,
            port=self.port,
            url=f"http://{self.host}:{self.port}/mcp"
        )
    
    async def stop(self) -> None:
        """Stop the MCP server."""
        if not self._running:
            return
        
        if self._runner:
            await self._runner.cleanup()
        
        self._running = False
        logger.info("MCP Server stopped")
    
    async def run_forever(self) -> None:
        """Start server and run until interrupted."""
        await self.start()
        
        try:
            # Keep running
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()
    
    @property
    def url(self) -> str:
        """Get server URL."""
        return f"http://{self.host}:{self.port}/mcp"
    
    @property
    def is_running(self) -> bool:
        """Check if server is running."""
        return self._running


# ============================================================================
# Helper Functions
# ============================================================================

def create_tool(
    name: str,
    description: str,
    handler: Callable,
    parameters: Optional[Dict[str, Any]] = None,
) -> Tool:
    """Create a tool with proper schema."""
    schema = {
        "type": "object",
        "properties": parameters or {},
    }
    
    return Tool(
        name=name,
        description=description,
        handler=handler,
        input_schema=schema,
    )


def create_resource(
    uri: str,
    name: str,
    handler: Callable,
    description: str = "",
    mime_type: str = "application/json",
) -> Resource:
    """Create a resource."""
    return Resource(
        uri=uri,
        name=name,
        description=description,
        mime_type=mime_type,
        handler=handler,
    )


def create_prompt(
    name: str,
    description: str,
    template: str,
    arguments: Optional[List[Dict]] = None,
) -> Prompt:
    """Create a prompt template."""
    return Prompt(
        name=name,
        description=description,
        template=template,
        arguments=arguments or [],
    )

