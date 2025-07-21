
import subprocess
import time
import os
import re

import toml
from config_loader import load_config, load_profile_config, USER_INPUT_PATH   # Import centralized functions

# Load configuration once
config = load_config()
NAMESPACE = config["constants"]["namespace"]

# Creates a pod in the specified Kubernetes namespace using the provided YAML file.
def create_pod(yaml_path, NAMESPACE):
    print(f"Creating pod from YAML: {yaml_path} in namespace '{NAMESPACE}'")
    result = subprocess.run(
        ["kubectl", "create", "-f", yaml_path, "-n", NAMESPACE],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    if result.returncode != 0:
        if "AlreadyExists" in result.stderr:
            print("Pod already exists. Skipping creation.")
            return
        else:
            print(f"Failed to create pod:\n{result.stderr}")
            raise RuntimeError("kubectl create failed")
    print(result.stdout.strip())


# Waits for a pod to reach the 'Completed' status within the specified timeout.
def wait_for_pod_completion(NAMESPACE, timeout=300):
    # Use etadata_name from the centralized configuration
    metadata_name, _ = load_profile_config()
    print(f"\nWaiting for pod '{metadata_name}' to reach 'Completed' status...")
    end_time = time.time() + timeout

    while time.time() < end_time:
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", NAMESPACE, "--no-headers"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
        )
        if result.returncode != 0:
            print(f"Error getting pods: {result.stderr}")
            time.sleep(5)
            continue

        lines = [line for line in result.stdout.splitlines() if metadata_name in line]
        if not lines:
            print("Waiting for pod to appear...")
        else:
            line = lines[0]
            pod_name = line.split()[0]
            pod_status = line.split()[2]
            print(f"Current pod '{pod_name}' status: {pod_status}")

            if pod_status == "Completed":
                print(f" Pod '{pod_name}' has completed successfully!")
                return pod_name  
            elif pod_status in ("Error", "CrashLoopBackOff"):
                raise RuntimeError(f" Pod '{pod_name}' failed with status: {pod_status}")
        
        time.sleep(5)

    raise TimeoutError(f" Timeout: Pod '{metadata_name}' did not complete within {timeout} seconds.")


# Fetches logs from the profile pod and updates the TOML file with the selected model ID.
def fetch_profile_pod_logs_and_update_toml(namespace):
    try:
        # Use pattern from the centralized configuration
        _, pattern = load_profile_config()
        if not pattern:
            print(" No pattern found under [profile] in TOML.")
            return

        print(f"\n Using regex pattern from TOML: '{pattern}'")
       
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", namespace, "--no-headers"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            check=True
        )

        pods = result.stdout.strip().split('\n')
        profile_pod = None
        for line in pods:
            pod_name = line.split()[0]
            if "profile" in pod_name.lower():
                profile_pod = pod_name
                break

        if not profile_pod:
            print(" No pod found with 'profile' in its name.")
            return

        print(f"\n Found profile pod: {profile_pod}")

        logs_result = subprocess.run(
            ["kubectl", "logs", profile_pod, "-n", namespace],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        if logs_result.returncode != 0:
            print(f" Failed to get logs:\n{logs_result.stderr}")
            return
        
        regex = re.compile(pattern, re.IGNORECASE)
        matches = [line for line in logs_result.stdout.splitlines() if regex.search(line)]

        print("\n Matching log lines:")
        for line in matches:
            print(line)

        match_id = matches[0].split(":")[0].strip()
        
        config["profile"]["selected_model_id"] = match_id

        with open(USER_INPUT_PATH, "w") as f:
            toml.dump(config, f)

        print(f"\nUpdated TOML with selected_model_id = {match_id}")

    except subprocess.CalledProcessError as e:
        print(f" Error executing kubectl command:\n{e.stderr}")
    except Exception as e:
        print(f" Unexpected error: {str(e)}")


#  Deletes a temporary pod defined in the specified YAML file.
def delete_temp_pod_from_yaml(yaml_path, NAMESPACE):
    print(f"\nDeleting temporary pod defined in YAML: {yaml_path} from namespace '{NAMESPACE}'...")
    result = subprocess.run(
        ["kubectl", "delete", "-f", yaml_path, "-n", NAMESPACE],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )

    if result.returncode != 0:
        print(f"Failed to delete pod:\n{result.stderr}")
        return

    print(result.stdout.strip())

    time.sleep(3)
    confirm = subprocess.run(
        ["kubectl", "get", "pods", "-n", NAMESPACE],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    print("\nRemaining pods:")
    print(confirm.stdout.strip())


#  Executes commands inside the 'genai-perf' pod and performs setup tasks.
def exec_into_genai_perf_pod(namespace):
    cluster_ip = config.get("cluster", {}).get("ip")
    get_pods = subprocess.run(
        ["kubectl", "get", "pods", "-n", namespace, "-o", "jsonpath={.items[*].metadata.name}"],
        universal_newlines=True,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    pods = get_pods.stdout.strip().split()
    target_pod = next((pod for pod in pods if pod.startswith("genai-perf")), None)

    if not target_pod:
        print(f" No pod starting with 'genai-perf' found in namespace '{namespace}'.")
        return

    local_shell_script_path = os.path.join(os.getcwd(), "bench.sh")
    if not os.path.exists(local_shell_script_path):
        print(f"bench.sh not found at {local_shell_script_path}")
        return

    model = config["final_exec"]["model"]
    pattern = config["profile"]["pattern"]

    full_path = f"/workdir/{model}/{pattern}"

    setup_cmd = f"mkdir -p {full_path}"

    print(f" Executing into pod: {target_pod}")
    subprocess.run([
        "kubectl", "exec", "-n", namespace, target_pod, "--",
        "bash", "-c", setup_cmd
    ], check=True)

    subprocess.run([
        "kubectl", "cp", local_shell_script_path,
        f"{namespace}/{target_pod}:{full_path}/bench.sh"
    ], check=True)

    print(f" bench.sh copied to pod: {full_path}/bench.sh")

    hf_token = config.get("api_keys", {}).get("hugging_face_token")

    if not hf_token:
        print(" 'hugging_face_token' not found in TOML config.")
        return

    login_cmd = f"huggingface-cli login --token {hf_token}"

    subprocess.run(["kubectl", "exec", "-n", NAMESPACE, target_pod, "--", "bash", "-c", login_cmd], check=True)

    print(" Hugging Face CLI login completed.")

    cluster_ip = config.get("values", {}).get("cluster_ip")

    if not cluster_ip:
        print(" Cluster IP not found in TOML config.")
        return

    url = f"http://{cluster_ip}/v1/models"
    print(f" Checking model serving at: {url}")

    try:
        result = subprocess.run(["curl", "-X", "GET", url], universal_newlines=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        print(" Response:\n", result.stdout)
    except subprocess.CalledProcessError as e:
        print(" Failed to fetch model status:\n", e.stderr)