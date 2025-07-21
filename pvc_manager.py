import os
import subprocess
import sys
import toml
from collections import OrderedDict
import yaml
from config_loader import load_config

# Load configuration from the centralized config loader
config = load_config() 

NAMESPACE = config["constants"]["namespace"]

#  Updates the PVC YAML file with the specified storage class and size.
def update_pvc_yaml(pvc_config):
    try:
        with open(pvc_config["pvc_yaml_path"], 'r') as f:
            pvc = yaml.safe_load(f)
    except FileNotFoundError:
        sys.exit(f" PVC YAML file not found: {pvc_config['pvc_yaml_path']}")
    except Exception as e:
        sys.exit(f" Failed to read PVC YAML: {e}")

    # Validate the loaded PVC YAML content
    if pvc is None:
        sys.exit(f" PVC YAML file is empty: {pvc_config['pvc_yaml_path']}")

    if 'spec' not in pvc:
        sys.exit(f" PVC YAML missing 'spec' section: {pvc_config['pvc_yaml_path']}")

    pvc['spec']['storageClassName'] = pvc_config['storage_class']
    pvc['spec']['resources']['requests']['storage'] = pvc_config['storage_size']

    try:
        # Write the updated PVC YAML back to the file
        with open(pvc_config["pvc_yaml_path"], 'w') as f:
            yaml.dump(pvc, f)
        print(" PVC YAML updated successfully.")
    except Exception as e:
        sys.exit(f" Failed to write PVC YAML: {e}")

    try:
         # Apply the updated PVC YAML to the Kubernetes namespace
        subprocess.run(["kubectl", "apply", "-n", NAMESPACE, "-f", pvc_config["pvc_yaml_path"]], check=True)
        print(f" PVC applied to namespace '{NAMESPACE}'")
    except subprocess.CalledProcessError as e:
        sys.exit(f" Failed to apply PVC YAML: {e}")



# Creates a PVC in the specified Kubernetes namespace and ensures it is up to date.
def create_and_check_pvc(toml_path, namespace):
    config = toml.load(toml_path)
    pvc_yaml_path = config.get("paths", {}).get("workdir_pvc")

    if not pvc_yaml_path:
        raise ValueError("Missing 'workdir_pvc' path under [paths] in the TOML file.")

    print(f" Creating PVC from: {pvc_yaml_path} in namespace '{namespace}'...")
    try:
        subprocess.run(["kubectl", "create", "-f", pvc_yaml_path, "-n", namespace],
                       check=True, stderr=subprocess.PIPE)
        print(" PVC created.")
    except subprocess.CalledProcessError as e:
        stderr_output = e.stderr.decode() if e.stderr else ""
        
        if "AlreadyExists" in stderr_output:
            print(" PVC already exists. Applying the PVC YAML to ensure it's up to date...")
            try:
                subprocess.run(["kubectl", "apply", "-f", pvc_yaml_path, "-n", namespace], check=True)
                print(" PVC applied.")
            except subprocess.CalledProcessError as apply_err:
                print(" Failed to apply PVC:\n", apply_err)
                raise
        else:
            print(" Failed to create PVC:\n", stderr_output)
            raise
    # List all PVCs in the namespace for verification
    print(f" Listing PVCs in namespace '{namespace}'...")

    subprocess.run(["kubectl", "get", "pvc", "-n", namespace])

