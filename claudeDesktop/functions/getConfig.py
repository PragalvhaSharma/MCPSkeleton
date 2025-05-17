import requests
import re
import json
import urllib.parse

def getConfig(github_url):
    """
    Extract mcpServers configuration from a GitHub repository README.
    
    Args:
        github_url: URL to a GitHub repository
    
    Returns:
        dict: The mcpServers configuration extracted from the README
    """
    # Clean up and parse GitHub URL to get the repository path
    # Remove any query parameters or fragments
    cleaned_url = github_url.split('?')[0].split('#')[0]
    
    # Handle direct raw GitHub URLs
    if "raw.githubusercontent.com" in cleaned_url:
        # Extract repo owner, repo name, and branch from raw URL
        parts = re.match(r"https://raw.githubusercontent.com/([^/]+)/([^/]+)/([^/]+)/(.+)", cleaned_url)
        if parts:
            owner, repo, branch, path = parts.groups()
            repo_path = f"{owner}/{repo}"
            branch_name = branch
            
            # If the path ends with README.md, use it directly
            if path.endswith("README.md"):
                readme_path = path
                raw_readme_url = cleaned_url
            else:
                # Assume we need to append README.md to the path
                readme_path = f"{path}/README.md" if path else "README.md"
                readme_path = readme_path.lstrip('/')
                raw_readme_url = f"https://raw.githubusercontent.com/{repo_path}/{branch_name}/{readme_path}"
            
            print(f"Using Raw GitHub URL: {raw_readme_url}")
        else:
            print(f"Invalid raw GitHub URL: {github_url}")
            return {"mcpServers": {}}
    
    # Handle GitHub tree URLs
    elif "/tree/" in cleaned_url:
        # Extract repo owner, repo name, and branch
        parts = re.match(r"https://github.com/([^/]+)/([^/]+)/tree/([^/]+)/?(.+)?", cleaned_url)
        if parts:
            owner, repo, branch, extra_path = parts.groups()
            repo_path = f"{owner}/{repo}"
            branch_name = branch
            subdir = extra_path.lstrip('/') if extra_path else ""
            
            # Construct the path to the README.md file
            readme_path = f"{subdir}/README.md" if subdir else "README.md"
            readme_path = readme_path.lstrip('/')
            raw_readme_url = f"https://raw.githubusercontent.com/{repo_path}/{branch_name}/{readme_path}"
            
            print(f"Constructed Raw README URL from tree URL: {raw_readme_url}")
        else:
            print(f"Invalid GitHub repository URL with tree path: {github_url}")
            return {"mcpServers": {}}
    
    # Handle standard GitHub repository URLs
    else:
        repo_path = cleaned_url.replace("https://github.com/", "").rstrip('/')
        branch_name = "main"  # Default branch to try first
        
        # Handle case where URL might be malformed
        if not repo_path or '/' not in repo_path:
            print(f"Invalid GitHub repository URL: {github_url}")
            return {"mcpServers": {}}
            
        readme_path = "README.md"
        raw_readme_url = f"https://raw.githubusercontent.com/{repo_path}/{branch_name}/{readme_path}"
        print(f"Trying Raw README URL: {raw_readme_url}")
    
    try:
        # Fetch the README content
        response = requests.get(raw_readme_url)
        response.raise_for_status()
        readme_content = response.text
    except requests.exceptions.HTTPError:
        # If we're not already using an alternative branch, try another one
        if "raw.githubusercontent.com" in cleaned_url:
            print(f"Error fetching README directly from raw URL: {raw_readme_url}")
            return {"mcpServers": {}}
            
        # Try fallback branch
        if branch_name != "main":
            fallback_branch = "main"
        else:
            fallback_branch = "master"
            
        raw_readme_url = f"https://raw.githubusercontent.com/{repo_path}/{fallback_branch}/{readme_path}"
        print(f"{branch_name} branch not found. Trying: {raw_readme_url}")
        try:
            response = requests.get(raw_readme_url)
            response.raise_for_status()
            readme_content = response.text
        except Exception as e:
            print(f"Error fetching README from both {branch_name} and {fallback_branch} branches: {str(e)}")
            return {"mcpServers": {}}
    except Exception as e:
        print(f"Error fetching or parsing README: {str(e)}")
        return {"mcpServers": {}}
    
    # First look for code blocks that might contain complete JSON configurations
    json_code_blocks = re.findall(r'```(?:json)?\s*\n(\{\s*"mcpServers"\s*:[\s\S]*?)\n```', readme_content)
    
    if json_code_blocks:
        for block in json_code_blocks:
            try:
                # Try to parse the JSON code block directly
                config = json.loads(block)
                if "mcpServers" in config and isinstance(config["mcpServers"], dict):
                    print(f"Found mcpServers configuration in code block")
                    return config
            except json.JSONDecodeError:
                # Clean up the block and try again
                try:
                    # Remove comments
                    clean_block = re.sub(r'(?m)^\s*//.*\n?', '', block)
                    # Ensure it's properly formatted
                    if not clean_block.strip().startswith('{'):
                        clean_block = '{' + clean_block + '}'
                    config = json.loads(clean_block)
                    if "mcpServers" in config and isinstance(config["mcpServers"], dict):
                        print(f"Found mcpServers configuration in cleaned code block")
                        return config
                except:
                    continue
    
    # If we couldn't find a valid JSON configuration in code blocks,
    # fallback to server-specific pattern matching
    # Look for configs for any MCP server (not just "git")
    server_pattern = r'"([^"]+)"\s*:\s*\{\s*"command"\s*:\s*"([^"]+)",\s*"args"\s*:\s*\[(.*?)\]\s*\}'
    server_matches = re.findall(server_pattern, readme_content)
    
    if server_matches:
        config = {"mcpServers": {}}
        for match in server_matches:
            server_name, command, args_str = match
            config["mcpServers"][server_name] = {
                "command": command,
                "args": []
            }
            
            # Parse args if they exist
            if args_str:
                args_str = args_str.replace("'", '"')
                try:
                    # Try to parse as a JSON array
                    args = json.loads('[' + args_str + ']')
                    config["mcpServers"][server_name]["args"] = args
                except:
                    # Try simple string splitting
                    args = [arg.strip().strip('"\'') for arg in args_str.split(',')]
                    config["mcpServers"][server_name]["args"] = args
        
        print(f"Extracted configuration for {len(config['mcpServers'])} MCP servers")
        return config
    
    # Last resort: try to find an entire mcpServers block
    mcpserver_block = re.search(r'{\s*"mcpServers"\s*:\s*{[^{}]*{[^{}]*}[^{}]*}\s*}', readme_content)
    if mcpserver_block:
        try:
            # Try to parse the entire block
            config = json.loads(mcpserver_block.group(0))
            print(f"Found complete mcpServers block")
            return config
        except json.JSONDecodeError:
            pass
    
    # If all else fails, return empty configuration
    print("Could not extract mcpServers configuration from README")
    return {"mcpServers": {}}

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        github_url = sys.argv[1]
    else:
        github_url = input("Enter GitHub repository URL: ")
    
    # For testing with direct content
    if github_url.startswith("{") or "mcpServers" in github_url:
        # Parse direct JSON input
        try:
            config = json.loads(github_url)
            print(json.dumps(config, indent=2))
            sys.exit(0)
        except:
            readme_content = github_url
            # Extract configuration manually
            pattern = r'"mcpServers"\s*:\s*\{(.+?)\}'
            matches = re.findall(pattern, readme_content, re.DOTALL)
            if matches:
                config_str = '{"mcpServers": {' + matches[0] + '}}'
                try:
                    config = json.loads(config_str)
                    print(json.dumps(config, indent=2))
                    sys.exit(0)
                except:
                    pass
    
    config = getConfig(github_url)
    print(json.dumps(config, indent=2))
