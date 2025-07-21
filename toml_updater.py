
import subprocess
import toml

#   # Check the status of pods in the namespace
def update_cluster_ip_in_toml(namespace, toml_file_path):
    try:
         # Run the kubectl command to get the list of services in the namespace
        result = subprocess.run(
            ["kubectl", "get", "svc", "-n", namespace],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            check=True
        )
        lines = result.stdout.strip().split('\n')

         # Extract the header row to determine column indices
        headers = lines[0].split()
        name_index = headers.index("NAME")
        cluster_ip_index = headers.index("CLUSTER-IP")

        # Iterate through the service rows to find the target service
        for line in lines[1:]:
            columns = line.split()
            name = columns[name_index]
            if name.endswith("private") and "8b-bf16-tp1-pp1" in name:
                cluster_ip = columns[cluster_ip_index]
                print(f" Found cluster IP for service '{name}': {cluster_ip}")

                toml_data = toml.load(toml_file_path)
                if "values" not in toml_data:
                    toml_data["values"] = {}
                    #  Update the 'cluster_ip' value
                toml_data["values"]["cluster_ip"] = cluster_ip

                with open(toml_file_path, 'w') as f:
                    toml.dump(toml_data, f)

                print(f" Updated 'cluster_ip' in '{toml_file_path}'")
                return
        print(" No service ending with 'private' and containing '8b-bf16-tp1-pp1' found.")
    except subprocess.CalledProcessError as e:
        print(" Error executing kubectl command:", e.stderr)
    except Exception as e:
        print(" Unexpected error:", str(e))
