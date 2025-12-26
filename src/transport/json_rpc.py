"""
JSON-RPC 2.0 Implementation
===========================

Full implementation of JSON-RPC 2.0 specification.
https://www.jsonrpc.org/specification
"""

import json
import uuid
from dataclasses import dataclass, field
from typing import Any

# JSON-RPC 2.0 version
JSONRPC_VERSION = "2.0"

# Standard error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# Server errors: -32000 to -32099
SERVER_ERROR_START = -32099
SERVER_ERROR_END = -32000

ERROR_MESSAGES = {
    PARSE_ERROR: "Parse error",
    INVALID_REQUEST: "Invalid Request",
    METHOD_NOT_FOUND: "Method not found",
    INVALID_PARAMS: "Invalid params",
    INTERNAL_ERROR: "Internal error",
}


@dataclass
class JsonRpcError:
    """JSON-RPC 2.0 error object."""

    code: int
    message: str
    data: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        result = {"code": self.code, "message": self.message}
        if self.data is not None:
            result["data"] = self.data
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JsonRpcError":
        return cls(
            code=data["code"],
            message=data["message"],
            data=data.get("data"),
        )

    @classmethod
    def parse_error(cls, data: Any | None = None) -> "JsonRpcError":
        return cls(PARSE_ERROR, ERROR_MESSAGES[PARSE_ERROR], data)

    @classmethod
    def invalid_request(cls, data: Any | None = None) -> "JsonRpcError":
        return cls(INVALID_REQUEST, ERROR_MESSAGES[INVALID_REQUEST], data)

    @classmethod
    def method_not_found(cls, method: str) -> "JsonRpcError":
        return cls(METHOD_NOT_FOUND, f"Method not found: {method}")

    @classmethod
    def invalid_params(cls, details: str | None = None) -> "JsonRpcError":
        msg = ERROR_MESSAGES[INVALID_PARAMS]
        if details:
            msg = f"{msg}: {details}"
        return cls(INVALID_PARAMS, msg)

    @classmethod
    def internal_error(cls, details: str | None = None) -> "JsonRpcError":
        msg = ERROR_MESSAGES[INTERNAL_ERROR]
        if details:
            msg = f"{msg}: {details}"
        return cls(INTERNAL_ERROR, msg)

    @classmethod
    def server_error(cls, code: int, message: str, data: Any | None = None) -> "JsonRpcError":
        if not (SERVER_ERROR_START <= code <= SERVER_ERROR_END):
            raise ValueError(
                f"Server error code must be between {SERVER_ERROR_START} and {SERVER_ERROR_END}"
            )
        return cls(code, message, data)


@dataclass
class JsonRpcRequest:
    """JSON-RPC 2.0 request object."""

    method: str
    params: list | dict | None = None
    id: str | int | None = field(default_factory=lambda: str(uuid.uuid4()))
    jsonrpc: str = JSONRPC_VERSION

    @property
    def is_notification(self) -> bool:
        """Check if this is a notification (no id means no response expected)."""
        return self.id is None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"jsonrpc": self.jsonrpc, "method": self.method}
        if self.params is not None:
            result["params"] = self.params
        if self.id is not None:
            result["id"] = self.id
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JsonRpcRequest":
        return cls(
            method=data["method"],
            params=data.get("params"),
            id=data.get("id"),
            jsonrpc=data.get("jsonrpc", JSONRPC_VERSION),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "JsonRpcRequest":
        return cls.from_dict(json.loads(json_str))


@dataclass
class JsonRpcResponse:
    """JSON-RPC 2.0 response object."""

    id: str | int | None
    result: Any | None = None
    error: JsonRpcError | None = None
    jsonrpc: str = JSONRPC_VERSION

    @property
    def is_success(self) -> bool:
        """Check if response is successful."""
        return self.error is None

    @property
    def is_error(self) -> bool:
        """Check if response is an error."""
        return self.error is not None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error is not None:
            result["error"] = self.error.to_dict()
        else:
            result["result"] = self.result
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JsonRpcResponse":
        error = None
        if "error" in data:
            error = JsonRpcError.from_dict(data["error"])
        return cls(
            id=data.get("id"),
            result=data.get("result"),
            error=error,
            jsonrpc=data.get("jsonrpc", JSONRPC_VERSION),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "JsonRpcResponse":
        return cls.from_dict(json.loads(json_str))


@dataclass
class JsonRpcBatch:
    """JSON-RPC 2.0 batch request/response."""

    items: list[JsonRpcRequest | JsonRpcResponse]

    def to_dict(self) -> list[dict[str, Any]]:
        return [item.to_dict() for item in self.items]

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_list(cls, data: list[dict[str, Any]]) -> "JsonRpcBatch":
        items: list[JsonRpcRequest | JsonRpcResponse] = []
        for item in data:
            if "method" in item:
                items.append(JsonRpcRequest.from_dict(item))
            else:
                items.append(JsonRpcResponse.from_dict(item))
        return cls(items)


# ============================================================================
# Factory Functions
# ============================================================================


def create_request(
    method: str,
    params: list | dict | None = None,
    request_id: str | int | None = None,
    notification: bool = False,
) -> JsonRpcRequest:
    """
    Create a JSON-RPC request.

    Args:
        method: The method name to call
        params: Optional parameters (list for positional, dict for named)
        request_id: Optional request ID (auto-generated if not provided)
        notification: If True, creates a notification (no response expected)

    Returns:
        JsonRpcRequest object
    """
    if notification:
        return JsonRpcRequest(method=method, params=params, id=None)

    if request_id is None:
        request_id = str(uuid.uuid4())

    return JsonRpcRequest(method=method, params=params, id=request_id)


def create_response(
    request_id: str | int,
    result: Any | None = None,
) -> JsonRpcResponse:
    """
    Create a successful JSON-RPC response.

    Args:
        request_id: The ID from the original request
        result: The result data

    Returns:
        JsonRpcResponse object
    """
    return JsonRpcResponse(id=request_id, result=result)


def create_error_response(
    request_id: str | int | None,
    error: JsonRpcError,
) -> JsonRpcResponse:
    """
    Create an error JSON-RPC response.

    Args:
        request_id: The ID from the original request (or None for parse errors)
        error: The error object

    Returns:
        JsonRpcResponse object
    """
    return JsonRpcResponse(id=request_id, error=error)


def parse_message(
    data: str | bytes | dict | list,
) -> JsonRpcRequest | JsonRpcResponse | JsonRpcBatch | JsonRpcError:
    """
    Parse a JSON-RPC message.

    Args:
        data: Raw message data (string, bytes, or already parsed dict/list)

    Returns:
        Parsed message object, or JsonRpcError if parsing fails
    """
    # Parse JSON if needed
    if isinstance(data, (str, bytes)):
        try:
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            data = json.loads(data)
        except json.JSONDecodeError as e:
            return JsonRpcError.parse_error(str(e))

    # Handle batch
    if isinstance(data, list):
        if not data:
            return JsonRpcError.invalid_request("Empty batch")
        return JsonRpcBatch.from_list(data)

    # Validate structure
    if not isinstance(data, dict):
        return JsonRpcError.invalid_request("Message must be an object")

    # Check for required fields
    if "jsonrpc" not in data:
        return JsonRpcError.invalid_request("Missing 'jsonrpc' field")

    if data.get("jsonrpc") != JSONRPC_VERSION:
        return JsonRpcError.invalid_request(f"Invalid JSON-RPC version: {data.get('jsonrpc')}")

    # Determine if request or response
    if "method" in data:
        # It's a request
        if not isinstance(data["method"], str):
            return JsonRpcError.invalid_request("Method must be a string")
        return JsonRpcRequest.from_dict(data)
    elif "result" in data or "error" in data:
        # It's a response
        return JsonRpcResponse.from_dict(data)
    else:
        return JsonRpcError.invalid_request("Invalid message: neither request nor response")


# ============================================================================
# MCP-Specific Helpers
# ============================================================================


class MCPMethods:
    """Standard MCP method names."""

    # Initialize
    INITIALIZE = "initialize"
    INITIALIZED = "notifications/initialized"

    # Tools
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"

    # Resources
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    RESOURCES_SUBSCRIBE = "resources/subscribe"
    RESOURCES_UNSUBSCRIBE = "resources/unsubscribe"

    # Prompts
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"

    # Progress
    PROGRESS_NOTIFICATION = "notifications/progress"

    # Cancellation
    CANCELLED = "notifications/cancelled"


def create_mcp_request(
    method: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create an MCP-compliant JSON-RPC request.

    Args:
        method: MCP method name
        params: Method parameters

    Returns:
        Request as dictionary
    """
    return create_request(method, params).to_dict()


def create_initialize_request(
    client_name: str,
    client_version: str,
    capabilities: dict | None = None,
) -> dict[str, Any]:
    """Create MCP initialize request."""
    return create_mcp_request(
        MCPMethods.INITIALIZE,
        {
            "protocolVersion": "2024-11-05",
            "capabilities": capabilities or {},
            "clientInfo": {
                "name": client_name,
                "version": client_version,
            },
        },
    )


def create_tools_list_request() -> dict[str, Any]:
    """Create tools/list request."""
    return create_mcp_request(MCPMethods.TOOLS_LIST)


def create_tools_call_request(
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create tools/call request."""
    return create_mcp_request(
        MCPMethods.TOOLS_CALL,
        {
            "name": tool_name,
            "arguments": arguments or {},
        },
    )


def create_resources_list_request() -> dict[str, Any]:
    """Create resources/list request."""
    return create_mcp_request(MCPMethods.RESOURCES_LIST)


def create_resources_read_request(uri: str) -> dict[str, Any]:
    """Create resources/read request."""
    return create_mcp_request(MCPMethods.RESOURCES_READ, {"uri": uri})
