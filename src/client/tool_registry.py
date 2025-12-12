"""
Tool Registry
=============

Unified registry for tools from multiple MCP servers.
Handles namespace management and collision prevention.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import asyncio

from ..common.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ToolInfo:
    """
    Information about a registered tool.
    
    Namespace format: server_name.tool_name
    """
    
    name: str  # Original tool name
    server_name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    registered_at: datetime = field(default_factory=datetime.utcnow)
    call_count: int = 0
    last_called: Optional[datetime] = None
    
    @property
    def namespaced_name(self) -> str:
        """Get namespaced tool name (server_name.tool_name)."""
        return f"{self.server_name}.{self.name}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (for LLM tool list)."""
        return {
            "name": self.namespaced_name,
            "description": f"[{self.server_name}] {self.description}",
            "inputSchema": self.input_schema,
        }
    
    def to_original_dict(self) -> Dict[str, Any]:
        """Convert to original tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }
    
    def record_call(self) -> None:
        """Record a tool call."""
        self.call_count += 1
        self.last_called = datetime.utcnow()


class ToolRegistry:
    """
    Unified registry for tools from multiple MCP servers.
    
    Features:
    - Namespace management (server_name.tool_name)
    - Collision prevention
    - Tool discovery and listing
    - Usage statistics
    """
    
    def __init__(self):
        # Tools indexed by namespaced name
        self._tools: Dict[str, ToolInfo] = {}
        
        # Tools grouped by server
        self._by_server: Dict[str, Dict[str, ToolInfo]] = {}
        
        # Original names (for collision detection)
        self._original_names: Dict[str, List[str]] = {}  # name -> [server_names]
        
        self._lock = asyncio.Lock()
    
    async def register_tool(
        self,
        server_name: str,
        tool_data: Dict[str, Any],
    ) -> ToolInfo:
        """
        Register a tool from a server.
        
        Args:
            server_name: Name of the server providing the tool
            tool_data: Tool data from MCP tools/list response
            
        Returns:
            Registered ToolInfo
        """
        async with self._lock:
            name = tool_data.get("name", "")
            description = tool_data.get("description", "")
            input_schema = tool_data.get("inputSchema", {})
            
            tool_info = ToolInfo(
                name=name,
                server_name=server_name,
                description=description,
                input_schema=input_schema,
            )
            
            namespaced = tool_info.namespaced_name
            
            # Register in main registry
            self._tools[namespaced] = tool_info
            
            # Register by server
            if server_name not in self._by_server:
                self._by_server[server_name] = {}
            self._by_server[server_name][name] = tool_info
            
            # Track original name for collision detection
            if name not in self._original_names:
                self._original_names[name] = []
            if server_name not in self._original_names[name]:
                self._original_names[name].append(server_name)
            
            logger.debug(f"Registered tool: {namespaced}")
            
            return tool_info
    
    async def register_tools_from_server(
        self,
        server_name: str,
        tools: List[Dict[str, Any]],
    ) -> List[ToolInfo]:
        """
        Register multiple tools from a server.
        
        Args:
            server_name: Name of the server
            tools: List of tool data from MCP tools/list
            
        Returns:
            List of registered ToolInfo objects
        """
        registered = []
        for tool_data in tools:
            tool_info = await self.register_tool(server_name, tool_data)
            registered.append(tool_info)
        
        logger.info(f"Registered {len(registered)} tools from {server_name}")
        return registered
    
    async def unregister_server_tools(self, server_name: str) -> int:
        """
        Remove all tools from a server.
        
        Args:
            server_name: Name of the server
            
        Returns:
            Number of tools removed
        """
        async with self._lock:
            if server_name not in self._by_server:
                return 0
            
            count = 0
            for tool in list(self._by_server[server_name].values()):
                namespaced = tool.namespaced_name
                if namespaced in self._tools:
                    del self._tools[namespaced]
                    count += 1
                
                # Update original names
                if tool.name in self._original_names:
                    if server_name in self._original_names[tool.name]:
                        self._original_names[tool.name].remove(server_name)
                    if not self._original_names[tool.name]:
                        del self._original_names[tool.name]
            
            del self._by_server[server_name]
            
            logger.info(f"Unregistered {count} tools from {server_name}")
            return count
    
    async def get_tool(self, namespaced_name: str) -> Optional[ToolInfo]:
        """
        Get a tool by namespaced name.
        
        Args:
            namespaced_name: Full name (server_name.tool_name)
            
        Returns:
            ToolInfo or None
        """
        async with self._lock:
            return self._tools.get(namespaced_name)
    
    async def get_tool_by_name(
        self,
        tool_name: str,
        server_name: Optional[str] = None,
    ) -> Optional[ToolInfo]:
        """
        Get a tool by original name.
        
        If multiple servers have the same tool, server_name must be specified.
        
        Args:
            tool_name: Original tool name
            server_name: Optional server name for disambiguation
            
        Returns:
            ToolInfo or None
        """
        async with self._lock:
            if server_name:
                # Direct lookup
                if server_name in self._by_server:
                    return self._by_server[server_name].get(tool_name)
                return None
            
            # Check for collisions
            servers = self._original_names.get(tool_name, [])
            
            if not servers:
                return None
            
            if len(servers) > 1:
                logger.warning(
                    f"Tool name collision: '{tool_name}' exists on servers: {servers}. "
                    f"Use namespaced name or specify server_name."
                )
                return None
            
            # Single server - safe to return
            return self._by_server[servers[0]].get(tool_name)
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        Get unified tool list for LLM.
        
        Returns tools in a format suitable for LLM function calling.
        """
        async with self._lock:
            return [tool.to_dict() for tool in self._tools.values()]
    
    async def list_tools_by_server(
        self,
        server_name: str,
    ) -> List[Dict[str, Any]]:
        """Get tools from a specific server."""
        async with self._lock:
            if server_name not in self._by_server:
                return []
            return [tool.to_dict() for tool in self._by_server[server_name].values()]
    
    async def get_collisions(self) -> Dict[str, List[str]]:
        """
        Get all tool name collisions.
        
        Returns:
            Dict of tool_name -> [server_names] for colliding tools
        """
        async with self._lock:
            return {
                name: servers
                for name, servers in self._original_names.items()
                if len(servers) > 1
            }
    
    async def resolve_tool_name(self, name: str) -> Optional[str]:
        """
        Resolve a tool name to its namespaced version.
        
        Handles both namespaced and non-namespaced names.
        
        Args:
            name: Tool name (either "server.tool" or "tool")
            
        Returns:
            Namespaced name or None if not found
        """
        async with self._lock:
            # Check if already namespaced
            if name in self._tools:
                return name
            
            # Try to resolve non-namespaced
            servers = self._original_names.get(name, [])
            
            if len(servers) == 1:
                return f"{servers[0]}.{name}"
            
            return None
    
    def __len__(self) -> int:
        """Get total tool count."""
        return len(self._tools)
    
    @property
    def tool_count(self) -> int:
        """Get total tool count."""
        return len(self._tools)
    
    @property
    def server_count(self) -> int:
        """Get number of servers with registered tools."""
        return len(self._by_server)


class ToolExecutor:
    """
    Executes tools through MCP client.
    
    Handles:
    - Name resolution
    - Request routing
    - Error handling
    - Statistics tracking
    """
    
    def __init__(self, registry: ToolRegistry, client: Any):
        self.registry = registry
        self.client = client
    
    async def execute(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        server_name: Optional[str] = None,
    ) -> Any:
        """
        Execute a tool.
        
        Args:
            tool_name: Tool name (namespaced or not)
            arguments: Tool arguments
            server_name: Optional server name for disambiguation
            
        Returns:
            Tool execution result
        """
        # Resolve tool name
        if "." in tool_name:
            # Already namespaced
            namespaced = tool_name
        else:
            # Need to resolve
            if server_name:
                namespaced = f"{server_name}.{tool_name}"
            else:
                namespaced = await self.registry.resolve_tool_name(tool_name)
                if not namespaced:
                    raise ValueError(f"Cannot resolve tool: {tool_name}")
        
        # Get tool info
        tool_info = await self.registry.get_tool(namespaced)
        if not tool_info:
            raise ValueError(f"Tool not found: {namespaced}")
        
        # Record call
        tool_info.record_call()
        
        # Execute through client
        return await self.client.call_tool(
            server_name=tool_info.server_name,
            tool_name=tool_info.name,
            arguments=arguments or {},
        )

