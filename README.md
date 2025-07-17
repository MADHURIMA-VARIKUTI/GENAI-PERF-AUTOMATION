# GENAI-PERF-AUTOMATION


### Overview
GenAI-Perf is NVIDIA’s open-source benchmarking command-line tool for measuring the throughput and latency of generative AI models. These metrics are critical for evaluating the performance of large language models (LLMs) and other generative AI systems.

This project automates the process of deploying and managing Kubernetes resources for GenAI-Perf benchmarking. It includes functionality for creating namespaces, secrets, pods, PVCs, and running benchmark scripts.

### Key Metrics Captured
For large language models (LLMs), GenAI-Perf provides the following metrics:
- **Time to First Token**: The time taken to generate the first token.
- **Time to Second Token**: The time taken to generate the second token after the first.
- **Inter-Token Latency**: The latency between generating consecutive tokens.
- **Output Token Throughput**: The rate at which tokens are generated.
- **Request Throughput**: The number of requests processed per unit time.

These metrics helps to evaluate the efficiency and scalability of generative AI models.

### Features
- Kubernetes namespace management
- Secret creation and management
- Pod creation and monitoring
- PVC configuration and deployment
- Runtime YAML Configurations
- Benchmark execution and artifact collection and logging

### Installation
- Clone the NIM Deployment Repository 
   ```bash
   git clone https://github.com/NVIDIA/nim-deploy.git
   cd nim-deploy/kserve/
   git clone MADHURIMA-VARIKUTI/GENAI-PERF-AUTOMATION
   cd GENAI-PERF-AUTOMATION
   
### Prerequisites
Before using this project, ensure you have the following installed:
- Python 3.6 or higher
- `kubectl` CLI / Access to a Kubernetes cluster
- Once you have the requirements.txt file, install the dependencies using pip:  pip install -r requirements.txt

### Configuration: `user_input.toml`
The `user_input.toml` file is the main configuration file for this project. It contains all the necessary parameters for execution.
Each section and field is described in detail to help users understand and modify the configuration as needed.

##### [constants]
Defines constant values used throughout the script.
namespace: Kubernetes namespace for deploying resources 
 ###### EXAMPLE:
namespace = "genai-perf-automation" , change if required

##### [api_keys]
Stores API keys and tokens for external services.

1.	hugging_face_token: Token for accessing Hugging Face APIs.  "<your_hugging_face_token",
2.	ngc_api_key: API key for NVIDIA GPU Cloud (NGC). "your_ngc_api_key",
3.	ngc_token: Token for authenticating with NGC. "your_ngc_token"
4.	Hugging Face Token Creation & NGC Key Creation:
   
	a.	Go to Hugging Face.
	b.	Log in or create an account.
	c.	Navigate to Settings > Access Tokens.
	d.	Create a new token, choose scope (Read/Write), and save it.

	a.	Go to NVIDIA NGC.
	b.	Log in or create an account.
	c.	Navigate to Setup > Generate API Key and save it.
 

##### [pvc_details]
Configuration for Persistent Volume Claims (PVC).

1.	pvc_yaml_path: Path to the PVC YAML file, "./yaml/pv.yaml"
2.	storage_class: Storage class for PVC, "gl4f-filesystem", change if required or use default as provided
3.	storage_size: Size of the storage for PVC, "1024Gi", change as per requirement

   
 ##### [profile]
Configuration for pod profiles.

1.	pod_prefix: Prefix for pod names (e.g., list-profiles-llama-31-8b).
2.	pattern: Pattern for pod configuration (e.g., l40s-bf16-tp1-pp1-throughput).
3.	image: Container image to be used in the pod.
4.	selected_model_id: ID of the model to be used. [user don’t have to change this]


 ###### EXAMPLE:
1.	pod_prefix = "list-profiles-llama-31-8b", Developer use only, same as metadata name and will be used in yaml file ./yaml/llama-3.1-8b-instruct.yaml
2.	pattern = "l40s-bf16-tp1-pp1-throughput",  Developer use only, change as per requirement and provide similar kind of pattern as shown seperated by -
3.	image = "10.14.75.21/ezmeral-common/nvcr.io/nim/meta/llama-3.1-8b-instruct-pb24h2:1.3.2",  Developer use only, change as per requirement
4.	selected_model_id = "8af967d80ae8f30f4635a59b2140fdc2b38d3004e16e66c9667fa032e56497fd", it will get overwritten by script


 ##### [final_exec]
Configuration for final execution and benchmarking.

1.	model: Model name for execution 
2.	measurement_interval: Interval for performance measurement in ms
3.	tokenizer: Tokenizer configuration for the model.
4.	export_file_name: Name of the file to export results 
5.	concurrency_values: Concurrency levels for benchmarking 
6.	use_cases: Use cases for the model 
7.	artifacts_dir: Directory to store artifacts.

 ###### EXAMPLE:
1.model = "meta/llama-3.1-8b-instruct" ,  change if required

2.measurement_interval = "300000", change if required

3.tokenizer = "meta-llama/Llama-3.1-8B-Instruct",  change if required and place the exact name as you see in hugging face, it is case-sensitive.

4.export_file_name = "test1-export", change if required

5.concurrency_values = "1,2,4,8,16,32,64,128,256,512,1024", change if required

6.use_cases = "Search,Translation,Summarization", change if required

7.artifacts_dir = "artifacts", change if required

 ##### [profile_list]
Path to the YAML file for pod profiles.

1.	yaml_path: Path to the YAML file for pod profiles.

 ###### EXAMPLE:
yaml_path = "./yaml/llama-3.1-8b-instruct.yaml"

 ##### [download]
 Path to the YAML file for downloading resources.

1.	download_yaml: Path to the YAML file for downloading resources.

 ###### EXAMPLE:
download_yaml = "./yaml/download_l40s-tp1-pp1.yaml"

 ##### [paths]
Paths to various YAML files and scripts.

1.	runtime: Path to the runtime YAML file.
2.	deploy: Path to the deployment YAML file.
3.	workdir_pvc: Path to the work directory PVC YAML file.
4.	genai_pod_yaml: Path to the GenAI pod YAML file.
5.	shell_script: Path to the shell script for benchmarking.
6.	nim_secrets_yaml_path: Path to the YAML file for NVIDIA secrets.
7.	pod_artifacts_path: Path to the artifact’s directory inside the pod.
8.	destination_path: Path to store artifacts after copying from the pod.

 ###### EXAMPLE:
1.runtime = "./yaml/runtime-l40s-tp1-pp1.yaml"

2.deploy = "./yaml/deploy-l40s-tp1-pp1.yaml"

3.workdir_pvc = "./yaml/workdir_pvc.yaml"

4.genai_pod_yaml = "./yaml/genai-perf-pod.yaml"

5.shell_script = "/workdir/llama-3.1-70b-instruct/nim_1.3.2/throughput-bf16-tp1-pp1/bench.sh", change if required

6.nim_secrets_yaml_path = "./yaml/nvidia-nim-secrets.yaml"

7.pod_artifacts_path = "/opt/tritonserver/artifacts", Developer use only, change if required

8.destination_path = "/home/pcadmin/cloudai/nim-deploy/kserve/modules_changes/artifacts_results",  change if required

 ## [values]
Stores additional values used in the script like cluster ip
cluster_ip: IP address of the cluster. 

 ###### EXAMPLE:
 cluster_ip = "10.102.196.71", user don’t have to change this and it will get overwritten by script

________________________________________
 ### Instructions for Users
1.	Do not modify sections marked as "Developer use only" unless you understand the implications.
2.	Ensure all paths and configurations are correct to avoid execution errors.
3.	Verify API Keys:
	Ensure the hugging_face_token, ngc_api_key, and ngc_token are valid.
4.	Provided YAML Files:
	Store the YAML files in the yaml folder only.
5.	Set Namespace:
	Update the namespace field in [constants] to match your Kubernetes setup.


 ### Run the main script:
1.	Python3 main.py
2.	Monitor the logs in log folder for progress and errors with timestamp.


 ### Contribution
Contributions are welcome! Please submit a pull request or open an issue for any bugs or feature requests.


### Contact
For questions or support, contact madhurima.varikuti@hpe.com



