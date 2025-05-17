import json
import os

def update_server_config(new_config_data):
    """
    Update the server_config.json file with new JSON data.
    
    Args:
        new_config_data (dict): The new configuration data to merge with existing config
    
    Returns:
        bool: True if update was successful, False otherwise
    """
    # Use the local server_config.json in the project root
    config_path = "server_config.json"
    
    try:
        # Read the existing config
        with open(config_path, 'r') as file:
            existing_config = json.load(file)
        
        # Deep merge the configurations
        def deep_merge(source, destination):
            for key, value in source.items():
                if key in destination and isinstance(destination[key], dict) and isinstance(value, dict):
                    deep_merge(value, destination[key])
                else:
                    destination[key] = value
            return destination
        
        # Update the config by merging
        updated_config = deep_merge(new_config_data, existing_config)
        
        # Write the updated config back to file
        with open(config_path, 'w') as file:
            json.dump(updated_config, file, indent=4)
        
        print(f"Successfully updated {config_path}")
        return True
        
    except Exception as e:
        print(f"Error updating server config: {e}")
        return False

# Example usage:
if __name__ == "__main__":
    # Example of adding the Gmail server configuration
    new_config = {
        "mcpServers": {
            "gmail": {
                "command": "npx",
                "args": [
                    "@gongrzhe/server-gmail-autoauth-mcp"
                ]
            }
        }
    }
    
    update_server_config(new_config)
