import os
import toml

# Define the path to the user_input.toml file
USER_INPUT_PATH = os.path.join(os.getcwd(), "user_input.toml")

# Ensure the file exists, If the file does not exist, raise an error to prevent further execution.
if not os.path.exists(USER_INPUT_PATH):
    raise FileNotFoundError(f"user_input.toml not found in {os.getcwd()}")

# Load the configuration once
config = toml.load(USER_INPUT_PATH)

# Returns the loaded configuration dictionary.
def load_config():
   
    return config

# Retrieves the profile list, yaml path configuration from the TOML file.
def load_profile_list_config():
  
    profile_cfg = config.get("profile_list", {})
    yaml_path = profile_cfg.get("yaml_path")

    if not yaml_path or not os.path.isfile(yaml_path):
        raise FileNotFoundError(f"YAML path not found or invalid in TOML: {yaml_path}")
    
    return yaml_path

#  Retrieves the profile configuration from the TOML file and Returns the metadata_name and pattern.
def load_profile_config():
   
    profile = config.get("profile", {})
    metadata_name = profile.get("metadata_name")
    pattern = profile.get("pattern")
    
    if not metadata_name or not pattern:
        raise ValueError("Both 'metadata_name' and 'pattern' must be set in [profile] section of the TOML.")
    
    return metadata_name, pattern

# Returns the download YAML path, image, and selected model ID.
def load_toml_config():
   
    download_yaml = config["download"]["download_yaml"]
    image = config["profile"]["image"]
    selected_model_id = config["profile"]["selected_model_id"]
    return download_yaml, image, selected_model_id

#  Reads runtime and deploy paths from the TOML file & Returns the runtime path and deploy path.
def read_paths_from_toml():
   
    runtime_path = config["paths"].get("runtime")
    deploy_path = config["paths"].get("deploy")
    return runtime_path, deploy_path