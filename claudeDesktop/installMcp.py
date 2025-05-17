import argparse
import sys
import json
import os
from functions.findMCP import find_and_display_mcp_servers
from functions.getConfig import get_mcp_config
from functions.addConfig import update_server_config

def install_mcp_server(query, interactive=False):
    """
    Find, retrieve configuration, and install an MCP server.
    
    Args:
        query (str): Search term to find server
        interactive (bool): Whether to run in interactive mode
    
    Returns:
        dict: Result of the operation
    """
    # Step 1: Find the MCP server
    results = find_and_display_mcp_servers(
        query=query,
        json_output=True,
        interactive=interactive
    )
    
    if not results:
        return {"error": "No matching MCP servers found"}
    
    # Use the most relevant server (first result)
    server = results[0]
    repository_url = server["repository"]
    
    print(f"\nFound server: {server['name']}")
    print(f"Repository: {repository_url}")
    
    # Step 2: Get the configuration from the repository
    print("\nRetrieving configuration...")
    config = get_mcp_config(repository_url)
    
    if "error" in config:
        return {"error": f"Failed to get configuration: {config['error']}"}
    
    if "mcpServers" not in config:
        return {"error": "Invalid configuration: 'mcpServers' section not found"}
    
    print(f"Found configuration with {len(config['mcpServers'])} server(s)")
    
    # Step 3: Add the configuration to server_config.json
    print("\nAdding configuration to server_config.json...")
    success = update_server_config(config)
    
    if not success:
        return {"error": "Failed to update server configuration"}
    
    return {
        "success": True,
        "server": server["name"],
        "repository": repository_url,
        "message": f"Successfully installed {server['name']} configuration"
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find and install MCP server configuration")
    parser.add_argument("query", nargs="?", default="", help="Server to search for")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
    
    args = parser.parse_args()
    
    # Run the installation process
    result = install_mcp_server(args.query, args.interactive)
    
    # Output the result
    if "error" in result:
        print(f"\nError: {result['error']}")
        sys.exit(1)
    else:
        print(f"\nSuccess: {result['message']}")
        print(f"Server '{result['server']}' configuration has been added to server_config.json")
        sys.exit(0) 