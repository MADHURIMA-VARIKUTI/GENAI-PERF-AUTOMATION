import datetime
import os
import subprocess
import toml
import yaml
from config_loader import load_toml_config


# Updates the download YAML file with the specified image and model profile.
def update_download_yaml(yaml_path, image, selected_model_id):
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)

    # Update the container image and arguments
    container = data["spec"]["template"]["spec"]["containers"][0]
    container["image"] = image
    container["args"] = ["download-to-cache", "--profile", selected_model_id]

    with open(yaml_path, 'w') as f:
        yaml.safe_dump(data, f)

    print(f"Updated YAML with image: {image} and profile: {selected_model_id}")


#   Creates a Kubernetes job using the specified YAML file.

def create_download_job(yaml_path, NAMESPACE):
    print(f"Creating download job from: {yaml_path}")
    result = subprocess.run(
        ["kubectl", "create", "-f", yaml_path, "-n", NAMESPACE],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
     
    # Handle job creation results
    if result.returncode != 0:
        if "AlreadyExists" in result.stderr:
            print("Job already exists. Skipping creation.")
        else:
            print(f"Failed to create job:\n{result.stderr}")
            raise RuntimeError("Job creation failed.")
    else:
        print(result.stdout.strip())

# Executes the download flow by updating the YAML file and creating the job.
def run_download_flow(toml_path, NAMESPACE):
    yaml_path, image, selected_model_id = load_toml_config()
    update_download_yaml(yaml_path, image, selected_model_id)
    create_download_job(yaml_path, NAMESPACE)

    job_basename = os.path.splitext(os.path.basename(yaml_path))[0].replace("download_", "")

#  Creates or updates the GenAI performance pod using the specified YAML file.
def genai_pod_yaml(toml_path, NAMESPACE):
    config = toml.load(toml_path)
    genai_yaml_path = config.get("paths", {}).get("genai_pod_yaml")

    if not genai_yaml_path:
        raise ValueError("Missing 'genai_pod_yaml' path under [paths] in the TOML file.")

    print(f"Creating {genai_yaml_path} in namespace {NAMESPACE}...")
    try:
        subprocess.run(["kubectl", "create", "-f", genai_yaml_path, "-n", NAMESPACE],
                       check=True, stderr=subprocess.PIPE)
        print("GenAI perf pod created successfully.")
    except subprocess.CalledProcessError as e:
        stderr_output = e.stderr.decode() if e.stderr else ""
        if "AlreadyExists" in stderr_output:
            print("GenAI perf pod already exists. Applying changes...")
            try:
                subprocess.run(["kubectl", "apply", "-f", genai_yaml_path, "-n", NAMESPACE],
                               check=True)
                print("GenAI perf pod applied.")
            except subprocess.CalledProcessError as apply_err:
                print("Failed to apply GenAI perf pod:\n", apply_err)
                raise
        else:
            print("Failed to create GenAI perf pod:\n", stderr_output)
            raise

    # List active pods in the namespace for verification
    print(f"Getting active pods in namespace '{NAMESPACE}'...")
    subprocess.run(["kubectl", "get", "pods", "-n", NAMESPACE])

def run_bench_script_from_pod(toml_path, pod_name, namespace):
    config = toml.load(toml_path)

    shell_script = config.get("paths", {}).get("shell_script")
    ip = config.get("values", {}).get("cluster_ip")
    config1 = config.get("final_exec", {})

    if not shell_script or not ip:
        raise ValueError("Missing 'shell_script' or 'cluster_ip' in TOML file.")

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Append the timestamp to the export file name
    export_file_name = f"{config1['export_file_name']}_{timestamp}"
    print( )
    chmod_cmd = [
        "kubectl", "exec", "-n", namespace, pod_name, "--",
        "chmod", "+x", shell_script
    ]
    subprocess.run(chmod_cmd, check=True)
    print(f" Made script executable: {shell_script}")

    exec_cmd = [
        "kubectl", "exec", "-n", namespace, pod_name, "--",
        "bash", shell_script,
        "--model", config1["model"],
        "--measurement-interval", config1["measurement_interval"],
        "--tokenizer", config1["tokenizer"],
        "--url", f"http://{ip}",
        "--export-file-name", export_file_name ,
        "--concurrency-values", config1["concurrency_values"],
        "--use-cases", config1["use_cases"],
        "--artifacts-dir", config1["artifacts_dir"]
    ]
   
    print(f" Running benchmark script inside pod '{pod_name}'...")
    subprocess.run(exec_cmd, check=True)
    print(" Benchmark script executed successfully.")    
  

def copy_artifacts_from_pod_using_toml(namespace: str, pod_name: str):
    USER_INPUT_PATH = os.path.join(os.getcwd(), "user_input.toml")
    with open(USER_INPUT_PATH, "r") as f:
        config = toml.load(f)

    pod_artifacts_path = config["paths"]["pod_artifacts_path"]
    destination_path = config["paths"]["destination_path"]

    os.makedirs(destination_path, exist_ok=True)

    print(f" Copying from pod '{pod_name}' → {pod_artifacts_path} to local → {destination_path}")

    subprocess.run([
        "kubectl", "cp",
        f"{namespace}/{pod_name}:{pod_artifacts_path}",
        destination_path
    ], check=True)

    print(f" Successfully copied artifacts to: {destination_path}")  