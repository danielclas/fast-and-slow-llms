import yaml
from pathlib import Path
from typing import Dict, Any, List


def load_openapi_specs(api_spec_dir: str = "api_spec") -> Dict[str, Any]:
    """
    Load OpenAPI specifications as context for agents.
    
    Args:
        api_spec_dir: Directory containing OpenAPI YAML files
        
    Returns:
        Dictionary containing API specifications and summaries
    """
    spec_dir = Path(api_spec_dir)
    api_context = {
        "apis": {},
        "summary": []
    }
    
    # Files to load
    spec_files = [
        "accounts-payable.openapi.yaml",
        "accounts-receivable.openapi.yaml", 
        "general-ledger.openapi.yaml"
    ]
    
    for spec_file in spec_files:
        spec_path = spec_dir / spec_file
        if spec_path.exists():
            try:
                # Load the OpenAPI spec
                with open(spec_path, 'r') as f:
                    raw_spec = yaml.safe_load(f)
                
                api_name = spec_file.replace(".openapi.yaml", "").replace("-", "_")
                
                # Extract useful information for the agent
                api_info = extract_api_summary(raw_spec, api_name)
                api_context["apis"][api_name] = api_info
                api_context["summary"].extend(api_info["endpoints"])
                
                print(f"Loaded API context for {api_name}: {len(api_info['endpoints'])} endpoints")
                
            except Exception as e:
                print(f"Failed to load {spec_file}: {e}")
    
    return api_context


def extract_api_summary(spec: Dict[str, Any], api_name: str) -> Dict[str, Any]:
    """
    Extract a concise summary of API endpoints for agent context.
    
    Args:
        spec: The OpenAPI specification
        api_name: Name of the API
        
    Returns:
        Dictionary with API summary information
    """
    info = spec.get("info", {})
    servers = spec.get("servers", [])
    base_url = servers[0].get("url", "") if servers else ""
    
    endpoints = []
    paths = spec.get("paths", {})
    
    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method.lower() in ["get", "post", "put", "patch", "delete"]:
                endpoint_info = {
                    "method": method.upper(),
                    "path": path,
                    "operation_id": operation.get("operationId", ""),
                    "summary": operation.get("summary", ""),
                    "description": operation.get("description", ""),
                    "api": api_name
                }
                endpoints.append(endpoint_info)
    
    return {
        "api_name": api_name,
        "title": info.get("title", ""),
        "description": info.get("description", ""),
        "base_url": base_url,
        "version": info.get("version", ""),
        "endpoints": endpoints
    }


def format_api_context_for_agent(api_context: Dict[str, Any]) -> str:
    """
    Format the API context as a string for inclusion in agent prompts.
    
    Args:
        api_context: The API context from load_openapi_specs()
        
    Returns:
        Formatted string describing available APIs
    """
    if not api_context.get("apis"):
        return "No API specifications available."
    
    context_lines = ["Available APIs:"]
    
    for api_name, api_info in api_context["apis"].items():
        context_lines.append(f"\n## {api_info['title']} ({api_name})")
        if api_info["description"]:
            context_lines.append(f"Description: {api_info['description']}")
        if api_info["base_url"]:
            context_lines.append(f"Base URL: {api_info['base_url']}")
        
        context_lines.append(f"Endpoints ({len(api_info['endpoints'])} total):")
        
        # Show ALL endpoints so the agent has complete API visibility
        for endpoint in api_info['endpoints']:
            context_lines.append(
                f"  {endpoint['method']} {endpoint['path']} - {endpoint['summary']}"
            )
    
    return "\n".join(context_lines)
