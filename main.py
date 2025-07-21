import base64
import os
from pathlib import Path
import subprocess
import toml
import sys
from logger import StreamToLogger 
from api_keys import export_env_vars
from config_loader import load_profile_list_config, load_profile_config, read_paths_from_toml, USER_INPUT_PATH
from pod_manager import create_pod, wait_for_pod_completion, fetch_profile_pod_logs_and_update_toml, delete_temp_pod_from_yaml, exec_into_genai_perf_pod
from pvc_manager import update_pvc_yaml, create_and_check_pvc
from runtime_manager import update_runtime_yaml, apply_runtime_yaml, wait_for_clusterservingruntime, update_runtime_in_deploy_yaml, create_or_apply_deploy_yaml
from toml_updater import update_cluster_ip_in_toml
from utils import run_download_flow, genai_pod_yaml, run_bench_script_from_pod, copy_artifacts_from_pod_using_toml
from config_loader import load_config
# import config_loader

config = load_config() 
NAMESPACE = config["constants"]["namespace"]

def main():

    print(" TOML Test Scheduler Started!\n")
   

    api_keys = config.get("api_keys", {})
   
    print(" Exporting API keys as environment variables...")
    ngc_api_key, ngc_token, hf_token = export_env_vars(api_keys)

    if not ngc_api_key:
        raise ValueError(" Missing 'ngc_api_key' in [api_keys]")
    if not hf_token:
        raise ValueError(" Missing 'hugging_face_token' in [api_keys]")

    print(f" Checking if namespace '{NAMESPACE}' exists...")
    ns_check = subprocess.run( ["kubectl", "get", "ns", NAMESPACE], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


    if ns_check.returncode != 0:
     print(f" Creating Kubernetes namespace '{NAMESPACE}'...")
     subprocess.run(["kubectl", "create", "ns", NAMESPACE], check=True)
    else:
     print(f" Namespace '{NAMESPACE}' already exists. Skipping creation.")



    print(f"Checking if Docker registry secret 'ngc-secret' exists in namespace '{NAMESPACE}'...")
    secret_check = subprocess.run(
    ["kubectl", "get", "secret", "ngc-secret", "-n", NAMESPACE],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

    if secret_check.returncode == 0:
      print("Deleting existing 'ngc-secret' to update it with new key...")
      subprocess.run(["kubectl", "delete", "secret", "ngc-secret", "-n", NAMESPACE], check=True)

    print("Creating Docker registry secret 'ngc-secret'...")
    subprocess.run([
    "kubectl", "create", "secret", "docker-registry", "ngc-secret",
    "-n", NAMESPACE,
    "--docker-server=nvcr.io",
    "--docker-username", "oauthtoken",
    "--docker-password", ngc_api_key
], check=True)

     
    print(f" Checking if secret 'nvidia-nim-secrets' exists in namespace '{NAMESPACE}'...")
    nim_secret_check = subprocess.run(
        ["kubectl", "get", "secret", "nvidia-nim-secrets", "-n", NAMESPACE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    if nim_secret_check.returncode == 0:
        print(" Secret 'nvidia-nim-secrets' already exists. Deleting it to recreate...")
        subprocess.run(["kubectl", "delete", "secret", "nvidia-nim-secrets", "-n", NAMESPACE], check=True)
    else:
        print(" 'nvidia-nim-secrets' does not exist. Proceeding to create it...")

    print(" Creating Kubernetes secret 'nvidia-nim-secrets'...")
    subprocess.run([
        "kubectl", "create", "secret", "generic", "nvidia-nim-secrets",
        "-n", NAMESPACE,
        f"--from-literal=token={hf_token}",
        f"--from-literal=api-key={ngc_api_key}"
    ], check=True)
   
    nim_secrets_yaml_path = config["paths"]["nim_secrets_yaml_path"]
    if not os.path.exists(nim_secrets_yaml_path):
     raise FileNotFoundError(f"YAML secret template not found: {nim_secrets_yaml_path}")
  
    print(" Encoding HF_TOKEN and NGC_API_KEY as base64...")
    hf_token_b64 = base64.b64encode(hf_token.encode()).decode()
    ngc_api_key_b64 = base64.b64encode(ngc_api_key.encode()).decode()

 
    print(f" Reading YAML secret template from: {nim_secrets_yaml_path}")
    with open(nim_secrets_yaml_path, "r") as f:
        yaml_content = f.read()

    print(" Replacing placeholders with encoded secrets...")
    yaml_content = yaml_content.replace("${HF_TOKEN}", hf_token_b64)
    yaml_content = yaml_content.replace("${NGC_API_KEY}", ngc_api_key_b64)

  
    print(f" Applying updated secret YAML to namespace '{NAMESPACE}'...")
    subprocess.run(
        ["kubectl", "apply", "-n", NAMESPACE, "-f", "-"], input=yaml_content, universal_newlines=True, check=True)
    print(f" Successfully applied secret to Kubernetes namespace '{NAMESPACE}'\n")

    result_label = subprocess.run(
    ["kubectl", "get", "ns", NAMESPACE, "--show-labels"],stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
    print(result_label.stdout)

    print(f" Labeling namespace '{NAMESPACE}'...")
    subprocess.run(["kubectl", "label", "ns", NAMESPACE, "hpe-ezua/ezmodels=true", "--overwrite"], check=True)

    pvc_config = config.get('pvc_details', {})
    update_pvc_yaml(pvc_config)

   
    print(" Starting pod creation and monitoring process...")

    pod_prefix, pattern = load_profile_config()

    yaml_path = load_profile_list_config()

    create_pod(yaml_path, NAMESPACE)

    print(f" Using pod prefix: {pod_prefix}  and pattern: {pattern}")

    fetch_profile_pod_logs_and_update_toml(NAMESPACE)
 
    run_download_flow(USER_INPUT_PATH, NAMESPACE)

    data = load_config()

    runtime_yaml = data["paths"]["runtime"]
    image = data["profile"]["image"]
    selected_model_id = data["profile"]["selected_model_id"]

    update_runtime_yaml(runtime_yaml, image, selected_model_id)
    apply_runtime_yaml(runtime_yaml, NAMESPACE)
    wait_for_clusterservingruntime(NAMESPACE)   

    runtime_yaml, deploy_yaml = read_paths_from_toml()

    runtime_path = Path(config["paths"]["runtime"])

    runtime_name = runtime_path.stem 
   
    update_runtime_in_deploy_yaml(deploy_yaml, runtime_name)
   
    deploy_yaml_path = config["paths"].get("deploy")
    
    create_or_apply_deploy_yaml(deploy_yaml_path, NAMESPACE)
    get_pods = subprocess.run(
            ["kubectl", "get", "pods", "-n",NAMESPACE, "-o", "jsonpath={.items[*].metadata.name}"],
            universal_newlines=True,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,)
    pods = get_pods.stdout.strip().split()
    target_pod = next((pod for pod in pods if pod.startswith("genai-perf")), None)
    if not target_pod:
         raise ValueError("No pod matching 'genai-perf' found.")
    update_cluster_ip_in_toml(NAMESPACE, USER_INPUT_PATH)  

    create_and_check_pvc(USER_INPUT_PATH, NAMESPACE)  

    genai_pod_yaml(USER_INPUT_PATH, NAMESPACE)

    exec_into_genai_perf_pod(NAMESPACE)

    run_bench_script_from_pod(USER_INPUT_PATH, target_pod, NAMESPACE)
    copy_artifacts_from_pod_using_toml(NAMESPACE,target_pod)
    delete_temp_pod_from_yaml(yaml_path, NAMESPACE)

if __name__ == "__main__":
    main()