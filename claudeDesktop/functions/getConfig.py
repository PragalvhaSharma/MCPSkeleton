import json
import re
import requests

def convert_github_url_to_raw(github_url):
    """
    Convert a GitHub repository URL to its raw README URL.
    
    Args:
        github_url (str): GitHub repository URL
        
    Returns:
        str: URL to the raw README.md file
    """
    # Remove trailing slash if present
    github_url = github_url.rstrip('/')
    
    # Check if URL points to a subdirectory
    if '/tree/' in github_url:
        # Extract path components from URL with subdirectory
        pattern = r'https://github.com/([^/]+)/([^/]+)/tree/([^/]+)/(.*)'
        match = re.match(pattern, github_url)
        
        if match:
            owner, repo, branch, path = match.groups()
            # Construct the raw URL for the README.md file in the subdirectory
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}/README.md"
            
            # Check if the README exists
            response = requests.head(raw_url)
            if response.status_code == 200:
                return raw_url
    else:
        # Extract owner and repo from the URL (original behavior for repo root)
        pattern = r'https://github.com/([^/]+)/([^/]+)'
        match = re.match(pattern, github_url)
        
        if match:
            owner, repo = match.groups()
            # Construct the raw URL for the README.md file
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md"
            
            # First try main branch
            response = requests.head(raw_url)
            if response.status_code == 200:
                return raw_url
                
            # If main doesn't exist, try master branch
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/master/README.md"
            response = requests.head(raw_url)
            if response.status_code == 200:
                return raw_url
    
    # If we can't determine the raw URL, return the original URL
    return github_url

def get_mcp_config(url_or_config):
    """
    Function to retrieve and extract MCP Server configuration from a README or direct JSON.
    
    Args:
        url_or_config (str): URL to the GitHub repository or direct JSON string
        
    Returns:
        dict: The extracted MCP configuration as a dictionary.
    """
    try:
        # Check if input is already a valid JSON string
        try:
            config = json.loads(url_or_config)
            # If it's already a valid JSON, check if it's an MCP configuration
            if "mcpServers" in config:
                return config
            elif "mcp" in config and "servers" in config["mcp"]:
                # Convert to the format our application expects
                return {
                    "mcpServers": config["mcp"]["servers"]
                }
            return {"error": "Valid JSON but no MCP configuration found"}
        except json.JSONDecodeError:
            # Not valid JSON, continue with URL processing
            pass
        
        # Check if it's a local file path
        if url_or_config.startswith('./') or url_or_config.startswith('/') or ':' not in url_or_config:
            try:
                with open(url_or_config, 'r') as f:
                    config = json.load(f)
                    if "mcpServers" in config:
                        return config
                    elif "mcp" in config and "servers" in config["mcp"]:
                        return {
                            "mcpServers": config["mcp"]["servers"]
                        }
                return {"error": "No MCP configuration found in local file"}
            except (FileNotFoundError, json.JSONDecodeError):
                # Not a valid local file or contains invalid JSON
                pass
        
        # Assume it's a GitHub URL and proceed with the original logic
        # Convert GitHub URL to raw README URL
        raw_url = convert_github_url_to_raw(url_or_config)
        
        # Fetch the README from the raw URL
        response = requests.get(raw_url)
        readme_text = response.text
        
        # Find all code blocks that might contain JSON configuration
        json_blocks = re.findall(r'```(?:json)?\s*(\{[^`]*\})\s*```', readme_text, re.DOTALL)
        
        # Look for MCP configurations in all found blocks
        for block in json_blocks:
            # Clean up the block (remove potential markdown artifacts)
            clean_block = block.strip()
            
            try:
                # Try to parse as JSON
                config = json.loads(clean_block)
                
                # Check if it's an MCP configuration - check both formats
                if "mcpServers" in config:
                    return config
                elif "mcp" in config and "servers" in config["mcp"]:
                    # Convert to the format our application expects
                    return {
                        "mcpServers": config["mcp"]["servers"]
                    }
                    
            except json.JSONDecodeError:
                continue
        
        # If we get here, we didn't find a valid MCP configuration in code blocks
        # Try to find any JSON objects that contain either format
        patterns = [
            r'\{\s*"mcpServers"\s*:\s*\{[^{}]*(?:\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}[^{}]*)*\}\s*\}',
            r'\{\s*"mcp"\s*:\s*\{\s*"servers"\s*:\s*\{[^{}]*(?:\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}[^{}]*)*\}\s*\}\s*\}'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, readme_text, re.DOTALL)
            if match:
                try:
                    config = json.loads(match.group(0))
                    # Check which format it is and normalize
                    if "mcpServers" in config:
                        return config
                    elif "mcp" in config and "servers" in config["mcp"]:
                        return {
                            "mcpServers": config["mcp"]["servers"]
                        }
                except json.JSONDecodeError:
                    pass
                
        # Fall back to a default configuration
        return {"error": "No MCP configuration found in README"}
            
    except requests.RequestException as e:
        return {"error": f"Failed to fetch README: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}

def extract_specific_server_config(config_source, server_name):
    """
    Extract configuration for a specific server from the config source.
    
    Args:
        config_source (str): URL to the GitHub repository, path to file, or JSON string
        server_name (str): Name of the server to extract config for
        
    Returns:
        dict: The extracted configuration for the specific server
    """
    full_config = get_mcp_config(config_source)
    
    if "error" in full_config:
        return full_config
        
    if "mcpServers" in full_config and server_name in full_config["mcpServers"]:
        return {
            "mcpServers": {
                server_name: full_config["mcpServers"][server_name]
            }
        }
    else:
        return {"error": f"Server '{server_name}' not found in the configuration"}

def update_server_config_file(config_file_path, config_source, server_name=None):
    """
    Update the server_config.json file with configurations from a source.
    
    Args:
        config_file_path (str): Path to the server_config.json file
        config_source (str): URL to the GitHub repository, path to file, or JSON string
        server_name (str, optional): Name of the specific server to extract.
                                    If None, all servers are extracted.
    
    Returns:
        dict: The updated configuration or an error message
    """
    try:
        # Get the configuration from the source
        if server_name:
            new_config = extract_specific_server_config(config_source, server_name)
        else:
            new_config = get_mcp_config(config_source)
        
        # Check if there was an error getting the config
        if "error" in new_config:
            return new_config
        
        # Read the existing config file
        try:
            with open(config_file_path, 'r') as f:
                existing_config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # If file doesn't exist or is invalid, create a new one with default structure
            existing_config = {"mcpServers": {}}
        
        # Handle different config formats
        if "mcpServers" not in existing_config:
            # Convert from mcp.servers format if needed
            if "mcp" in existing_config and "servers" in existing_config["mcp"]:
                existing_config = {"mcpServers": existing_config["mcp"]["servers"]}
            else:
                # Create the structure if it doesn't exist
                existing_config = {"mcpServers": {}}
        
        # Merge the new configuration with the existing one
        if "mcpServers" in new_config:
            for server, config in new_config["mcpServers"].items():
                existing_config["mcpServers"][server] = config
        
        # Write the updated configuration back to the file
        with open(config_file_path, 'w') as f:
            json.dump(existing_config, f, indent=4, sort_keys=False)
        
        return {"success": True, "message": f"Server configuration successfully updated with {len(new_config.get('mcpServers', {}))} servers"}
    
    except FileNotFoundError:
        return {"error": f"Config file not found: {config_file_path}"}
    except json.JSONDecodeError:
        return {"error": "Invalid JSON in the configuration file"}
    except Exception as e:
        return {"error": f"Failed to update configuration: {str(e)}"}

# Example usage
if __name__ == "__main__":
    # Example: Get MCP configuration from the specified repo
    repo_url = "https://github.com/githejie/mcp-server-calculator"
    print(f"Converting URL: {repo_url}")
    raw_url = convert_github_url_to_raw(repo_url)
    print(f"Raw URL: {raw_url}")
    
    # Test with the hardcoded example first
    test_json = """
    {
      "mcp": {
        "servers": {
          "git": {
            "command": "uvx",
            "args": ["mcp-server-git"]
          }
        }
      }
    }
    """
    
    print("Testing with hardcoded JSON:")
    try:
        config = json.loads(test_json)
        if "mcp" in config and "servers" in config["mcp"]:
            normalized_config = {
                "mcpServers": config["mcp"]["servers"]
            }
            print(json.dumps(normalized_config, indent=2))
        else:
            print("No MCP configuration found in test JSON")
    except json.JSONDecodeError as e:
        print(f"Error parsing test JSON: {e}")
    
    # Then try to get from the repo
    print("\nTrying to get config from repository:")
    config = get_mcp_config(repo_url)
    print("MCP configuration from repository:")
    print(json.dumps(config, indent=2))
    
    # Example: Use direct JSON string as input
    direct_json = """{
      "mcpServers": {
        "everything": {
          "command": "npx",
          "args": [
            "-y",
            "@modelcontextprotocol/server-everything"
          ]
        }
      }
    }"""
    
    print("\nTrying to process direct JSON input:")
    config = get_mcp_config(direct_json)
    print("MCP configuration from direct JSON:")
    print(json.dumps(config, indent=2))
    
    # Example: Create a config file
    print("\nCreating a sample config file:")
    with open("sample_config.json", "w") as f:
        f.write(direct_json)
    
    # Example: Read from a local file
    print("\nReading from local file:")
    config = get_mcp_config("sample_config.json")
    print("MCP configuration from local file:")
    print(json.dumps(config, indent=2))
    
    # Example: Update a config file with a specific server
    print("\nUpdating config file with a specific server:")
    result = update_server_config_file("server_config.json", direct_json, "everything")
    print(result)
