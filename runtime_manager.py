import os
import subprocess
import time
import yaml

# Updates the runtime YAML file with the specified image and model ID. 
def update_runtime_yaml(runtime_yaml_path, image, selected_model_id):
    with open(runtime_yaml_path, "r") as f:
        runtime_yaml = yaml.safe_load(f)

    
    # Update the container image
    runtime_yaml['spec']['containers'][0]['image'] = image

    # Update the environment variable for the model profile
    for env_var in runtime_yaml['spec']['containers'][0]['env']:
        if env_var['name'] == "NIM_MODEL_PROFILE":
            env_var['value'] = selected_model_id
            break

    with open(runtime_yaml_path, "w") as f:
        yaml.safe_dump(runtime_yaml, f)

    print(" Runtime YAML updated.")


#  Applies the runtime YAML file to the specified Kubernetes namespace.
def apply_runtime_yaml(runtime_yaml_path, NAMESPACE):
    print(f" Applying runtime YAML in namespace '{NAMESPACE}'...")
    try:
        subprocess.run(
            ["kubectl", "create", "-f", runtime_yaml_path, "-n", NAMESPACE],
            universal_newlines=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        print(" Created runtime successfully.")
    except subprocess.CalledProcessError as e:
        if "AlreadyExists" in e.stderr.decode():
            print("  Runtime already exists. Applying update instead...")
            subprocess.run(
                ["kubectl", "apply", "-f", runtime_yaml_path, "-n", NAMESPACE],
                universal_newlines=True
            )
            print(" Applied update to existing runtime.")
        else:
            raise  


#  Waits for the ClusterServingRuntime to become available in the specified namespace.
def wait_for_clusterservingruntime(NAMESPACE, timeout=180):
    print(f" Waiting for ClusterServingRuntime in namespace '{NAMESPACE}'...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            result = subprocess.check_output(
                ["kubectl", "get", "clusterservingruntime", "-n", NAMESPACE],
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            if "nim" in result or "llama" in result:
                print(" ClusterServingRuntime found:\n", result)
                return
        except subprocess.CalledProcessError:
            pass
        time.sleep(5)
    raise TimeoutError("ClusterServingRuntime not found in time.")


#  Updates the runtime name in the deploy YAML file.
def update_runtime_in_deploy_yaml(deploy_yaml_path, runtime_name):
    with open(deploy_yaml_path, 'r') as f:
        deploy_config = yaml.safe_load(f)

      # Update the runtime name in the deploy configuration
    deploy_config['spec']['predictor']['model']['runtime'] = runtime_name

    with open(deploy_yaml_path, 'w') as f:
        yaml.safe_dump(deploy_config, f)

    print(f" Updated runtime to '{runtime_name}' in {deploy_yaml_path}")


#  Creates or applies the deploy YAML file in the specified Kubernetes namespace.
def create_or_apply_deploy_yaml(deploy_yaml_path, namespace):
    if not deploy_yaml_path or not os.path.isfile(deploy_yaml_path):
        print(f"Deploy YAML path not found or invalid: {deploy_yaml_path}")
        return

    print(f" Creating deploy YAML in namespace '{namespace}' from '{deploy_yaml_path}'...")

    try:
        subprocess.run(
            ["kubectl", "create", "-f", deploy_yaml_path, "-n", namespace],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print(" Deploy YAML created successfully.")

    except subprocess.CalledProcessError as e:
        stderr_output = e.stderr.decode() if e.stderr else ""
        print(f" Create failed with error:\n{stderr_output}")

        if "AlreadyExists" in stderr_output:
            print(" InferenceService already exists. Applying update instead...")
            try:
                subprocess.run(
                    ["kubectl", "apply", "-f", deploy_yaml_path, "-n", namespace],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                print(" Deploy YAML applied successfully.")
            except subprocess.CalledProcessError as apply_err:
                print(" Failed to apply updated InferenceService:\n", apply_err.stderr.decode())
                raise
        else:
            raise

    # Check the status of pods in the namespace
    print(f" Checking pod status in namespace '{namespace}'...")
    try:
        subprocess.run(["kubectl", "get", "pods", "-n", namespace], check=True)
    except subprocess.CalledProcessError as e:
        print(" Failed to get pods:\n", e.stderr.decode() if e.stderr else str(e))

