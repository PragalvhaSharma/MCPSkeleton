import requests
import re
import argparse
import json

def calculate_relevance_score(server, query):
    """
    Calculate a relevance score for a server based on a search query.
    
    Args:
        server (dict): Server information dictionary
        query (str): Search term
        
    Returns:
        float: Relevance score (higher is more relevant)
    """
    query = query.lower()
    score = 0
    
    # Name matches are more important
    if query in server["name"].lower():
        # Exact name match gets highest score
        if query == server["name"].lower():
            score += 100
        # Name starts with query
        elif server["name"].lower().startswith(query):
            score += 75
        # Query is a substring of name
        else:
            score += 50
    
    # Description matches
    if query in server["description"].lower():
        # Description starts with query
        if server["description"].lower().startswith(query):
            score += 30
        # Query is a substring of description
        else:
            score += 20
    
    # Calculate word overlap in name and description
    query_words = set(query.split())
    name_words = set(server["name"].lower().split())
    desc_words = set(server["description"].lower().split())
    
    # Word overlap in name (more important)
    name_overlap = len(query_words.intersection(name_words))
    score += name_overlap * 15
    
    # Word overlap in description
    desc_overlap = len(query_words.intersection(desc_words))
    score += desc_overlap * 5
    
    # Boost reference servers slightly
    if server["type"] == "Reference":
        score += 5
    
    return score

def find_and_display_mcp_servers(query="", server_type=None, limit=10, url_only=False, json_output=False, interactive=False, show_relevance=False):
    """
    Find and display MCP servers based on search criteria.
    
    Args:
        query (str): Search term to find in server names or descriptions
        server_type (str): Filter by type (reference, official, community, framework, resource)
        limit (int): Maximum number of results to return
        url_only (bool): If True, output only the repository URL of the first result
        json_output (bool): If True, output results in JSON format
        interactive (bool): If True or query is empty, prompt user for input
        show_relevance (bool): If True, display relevance scores in output
    
    Returns:
        If json_output is True, returns a list of matching servers
        Otherwise, returns None (output is printed)
    """
    # Interactive mode - prompt user for input if no query provided or interactive flag set
    if interactive or not query:
        query = input("Enter server name to search for: ")
    
    # Special case for "skeleton" query
    if query.lower() in ["skeleton", "mcpskeleton"]:
        skeleton_info = {
            "name": "MCP Skeleton Server",
            "description": "A bare-bones MCP server implementation",
            "type": "Reference",
            "repository": "https://github.com/modelcontextprotocol/skeleton"
        }
        results = [skeleton_info]
    else:
        readme_url = "https://raw.githubusercontent.com/modelcontextprotocol/servers/main/README.md"
        
        try:
            resp = requests.get(readme_url, timeout=10)
            if resp.status_code != 200:
                print(f"Error fetching README: HTTP {resp.status_code}")
                return [] if json_output else None
            
            readme_content = resp.text
            
            # Define patterns for different sections
            section_patterns = {
                "reference": r"## 🌟 Reference Servers(.*?)##",
                "official": r"### 🎖️ Official Integrations(.*?)###",
                "community": r"### 🌎 Community Servers(.*?)##",
                "framework": r"## 📚 Frameworks(.*?)##",
                "resource": r"## 📚 Resources(.*?)##"
            }
            
            # Pattern to match server entries
            server_pattern = r"- (?:<img.*?)?(?:\*\*\[(.*?)\]\((.*?)\)\*\*) - (.*?)(?=\n-|\n##|$)"
            
            all_servers = []
            
            for section_type, pattern in section_patterns.items():
                # Skip if filtering by type and this isn't the type we want
                if server_type and server_type.lower() != section_type:
                    continue
                    
                section_match = re.search(pattern, readme_content, re.DOTALL)
                if section_match:
                    section_text = section_match.group(1)
                    
                    for match in re.finditer(server_pattern, section_text, re.DOTALL):
                        name = match.group(1).strip()
                        url = match.group(2).strip()
                        description = match.group(3).strip()
                        
                        # Determine if it's a repository URL or a relative path
                        is_repo = url.startswith("http")
                        
                        server_info = {
                            "name": name,
                            "description": description,
                            "type": section_type.capitalize()
                        }
                        
                        if is_repo:
                            server_info["repository"] = url
                        else:
                            server_info["path"] = url
                            server_info["repository"] = f"https://github.com/modelcontextprotocol/servers/tree/main/{url}"
                            
                        all_servers.append(server_info)
            
            # Filter based on query if provided
            if query:
                query = query.lower()
                matching_servers = [s for s in all_servers if query in s["name"].lower() or query in s["description"].lower()]
            else:
                matching_servers = all_servers
            
            # Calculate relevance scores if query provided
            if query:
                for server in matching_servers:
                    server["relevance"] = calculate_relevance_score(server, query)
                
                # Sort by relevance score (high to low)
                matching_servers.sort(key=lambda x: x["relevance"], reverse=True)
            else:
                # Sort by name if no query
                matching_servers.sort(key=lambda x: x["name"].lower())
            
            results = matching_servers[:limit]
            
        except Exception as e:
            print(f"Error: {e}")
            return [] if json_output else None
    
    if not results:
        print("No matching MCP servers found.")
        return [] if json_output else None
    
    # URL-only mode - use most relevant server
    if url_only:
        print(results[0]["repository"])
        return results if json_output else None
    
    # JSON-only mode
    if json_output:
        print(json.dumps(results, indent=2))
        return results
    
    # Standard output
    print(f"Found {len(results)} matching MCP servers:")
    
    # If query was provided, highlight the most relevant server
    if query and len(results) > 0:
        most_relevant = results[0]
        print(f"\n🔍 Most Relevant Server: {most_relevant['name']}")
        print(f"   Type: {most_relevant['type']}")
        print(f"   Description: {most_relevant['description']}")
        print(f"   Repository: {most_relevant['repository']}")
        if show_relevance and "relevance" in most_relevant:
            print(f"   Relevance Score: {most_relevant['relevance']:.2f}")
        print("\n--- All Matching Servers ---")
    
    for i, server in enumerate(results, 1):
        print(f"\n{i}. {server['name']}")
        print(f"   Type: {server['type']}")
        print(f"   Description: {server['description']}")
        print(f"   Repository: {server['repository']}")
        if show_relevance and "relevance" in server:
            print(f"   Relevance Score: {server['relevance']:.2f}")
    
    return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search MCP servers")
    parser.add_argument("query", nargs="?", default="", help="Search term")
    parser.add_argument("--type", "-t", choices=["reference", "official", "community", "framework", "resource"], 
                        help="Filter by type")
    parser.add_argument("--limit", "-l", type=int, default=10, help="Max results")
    parser.add_argument("--url-only", "-u", action="store_true", help="Output repository URL only")
    parser.add_argument("--json", "-j", action="store_true", help="Output JSON only")
    parser.add_argument("--interactive", "-i", action="store_true", help="Force interactive mode")
    parser.add_argument("--show-relevance", "-r", action="store_true", help="Show relevance scores")
    
    args = parser.parse_args()
    
    find_and_display_mcp_servers(
        query=args.query,
        server_type=args.type,
        limit=args.limit,
        url_only=args.url_only,
        json_output=args.json,
        interactive=args.interactive,
        show_relevance=args.show_relevance
    )