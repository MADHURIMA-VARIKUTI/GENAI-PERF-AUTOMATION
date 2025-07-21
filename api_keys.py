import os

#  Exports API keys as environment variables for use in the application.
def export_env_vars(api_keys):
    # Retrieve API keys from the dictionary
    ngc_api_key = api_keys.get("ngc_api_key")
    ngc_token = api_keys.get("ngc_token")
    hf_token = api_keys.get("hugging_face_token")
   
    # Ensure the KUBECONFIG environment variable is set
    # This is required for Kubernetes operations
    if "KUBECONFIG" not in os.environ:
     os.environ["KUBECONFIG"] = "/etc/kubernetes/admin.conf"

    if ngc_api_key:
        os.environ["NGC_API_KEY"] = ngc_api_key
        print(f'export NGC_API_KEY="{ngc_api_key}"')
    else:
        print(" Warning: 'ngc_api_key' missing in [api_keys]")

    if ngc_token:
        os.environ["NGC_TOKEN"] = ngc_token
        print(f'export NGC_TOKEN="{ngc_token}"')

    if hf_token:
        os.environ["HF_TOKEN"] = hf_token
        print(f'export HF_TOKEN="{hf_token}"')
    else:
        print(" Warning: 'hugging_face_token' missing in [api_keys]")

    return ngc_api_key, ngc_token, hf_token
