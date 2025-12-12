"""
Tests for transport layer.
"""

import pytest
import json
from src.transport.json_rpc import (
    JsonRpcRequest,
    JsonRpcResponse,
    JsonRpcError,
    create_request,
    create_response,
    create_error_response,
    parse_message,
    JSONRPC_VERSION,
    PARSE_ERROR,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
)


class TestJsonRpcRequest:
    """Test JSON-RPC request handling."""
    
    def test_create_request(self):
        """Test request creation."""
        request = create_request("test_method", {"key": "value"})
        
        assert request.method == "test_method"
        assert request.params == {"key": "value"}
        assert request.id is not None
        assert request.jsonrpc == JSONRPC_VERSION
    
    def test_create_notification(self):
        """Test notification creation (no id)."""
        request = create_request("notify", notification=True)
        
        assert request.method == "notify"
        assert request.id is None
        assert request.is_notification
    
    def test_request_to_dict(self):
        """Test request serialization."""
        request = create_request("test", {"a": 1}, request_id="123")
        data = request.to_dict()
        
        assert data["jsonrpc"] == "2.0"
        assert data["method"] == "test"
        assert data["params"] == {"a": 1}
        assert data["id"] == "123"
    
    def test_request_to_json(self):
        """Test request JSON serialization."""
        request = create_request("test", request_id="123")
        json_str = request.to_json()
        
        parsed = json.loads(json_str)
        assert parsed["method"] == "test"
        assert parsed["id"] == "123"
    
    def test_request_from_dict(self):
        """Test request deserialization."""
        data = {
            "jsonrpc": "2.0",
            "method": "test",
            "params": {"x": 1},
            "id": "abc",
        }
        
        request = JsonRpcRequest.from_dict(data)
        
        assert request.method == "test"
        assert request.params == {"x": 1}
        assert request.id == "abc"


class TestJsonRpcResponse:
    """Test JSON-RPC response handling."""
    
    def test_create_success_response(self):
        """Test success response creation."""
        response = create_response("123", {"result": "ok"})
        
        assert response.id == "123"
        assert response.result == {"result": "ok"}
        assert response.error is None
        assert response.is_success
    
    def test_create_error_response(self):
        """Test error response creation."""
        error = JsonRpcError.method_not_found("unknown")
        response = create_error_response("123", error)
        
        assert response.id == "123"
        assert response.result is None
        assert response.error.code == METHOD_NOT_FOUND
        assert response.is_error
    
    def test_response_to_dict(self):
        """Test response serialization."""
        response = create_response("123", "hello")
        data = response.to_dict()
        
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "123"
        assert data["result"] == "hello"
        assert "error" not in data
    
    def test_error_response_to_dict(self):
        """Test error response serialization."""
        error = JsonRpcError.internal_error("oops")
        response = create_error_response("123", error)
        data = response.to_dict()
        
        assert data["id"] == "123"
        assert "error" in data
        assert data["error"]["code"] == -32603


class TestJsonRpcError:
    """Test JSON-RPC error handling."""
    
    def test_parse_error(self):
        """Test parse error creation."""
        error = JsonRpcError.parse_error()
        assert error.code == PARSE_ERROR
        assert "Parse error" in error.message
    
    def test_invalid_request(self):
        """Test invalid request error."""
        error = JsonRpcError.invalid_request("bad data")
        assert error.code == INVALID_REQUEST
    
    def test_method_not_found(self):
        """Test method not found error."""
        error = JsonRpcError.method_not_found("foo")
        assert error.code == METHOD_NOT_FOUND
        assert "foo" in error.message
    
    def test_error_to_dict(self):
        """Test error serialization."""
        error = JsonRpcError(code=-32000, message="Custom", data={"info": "x"})
        data = error.to_dict()
        
        assert data["code"] == -32000
        assert data["message"] == "Custom"
        assert data["data"] == {"info": "x"}


class TestParseMessage:
    """Test message parsing."""
    
    def test_parse_request(self):
        """Test parsing a request."""
        data = {
            "jsonrpc": "2.0",
            "method": "test",
            "id": "1"
        }
        
        result = parse_message(data)
        
        assert isinstance(result, JsonRpcRequest)
        assert result.method == "test"
    
    def test_parse_response(self):
        """Test parsing a response."""
        data = {
            "jsonrpc": "2.0",
            "result": "ok",
            "id": "1"
        }
        
        result = parse_message(data)
        
        assert isinstance(result, JsonRpcResponse)
        assert result.result == "ok"
    
    def test_parse_json_string(self):
        """Test parsing JSON string."""
        json_str = '{"jsonrpc": "2.0", "method": "test", "id": "1"}'
        
        result = parse_message(json_str)
        
        assert isinstance(result, JsonRpcRequest)
    
    def test_parse_invalid_json(self):
        """Test parsing invalid JSON."""
        result = parse_message("not json")
        
        assert isinstance(result, JsonRpcError)
        assert result.code == PARSE_ERROR
    
    def test_parse_missing_version(self):
        """Test parsing message without version."""
        result = parse_message({"method": "test"})
        
        assert isinstance(result, JsonRpcError)
        assert result.code == INVALID_REQUEST
    
    def test_parse_wrong_version(self):
        """Test parsing message with wrong version."""
        result = parse_message({"jsonrpc": "1.0", "method": "test"})
        
        assert isinstance(result, JsonRpcError)
        assert result.code == INVALID_REQUEST


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

