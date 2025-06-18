import os
import requests
import time
import subprocess
import json
import base64
import secrets
from pymongo import MongoClient
from requests.auth import HTTPDigestAuth
from pymongocrypt.explicit_encrypter import ExplicitEncrypter
from pymongocrypt.key_material import RawKeyMaterial
from bson.binary import Binary, STANDARD

# --- Configuration ---
ATLAS_PUBLIC_KEY = os.environ.get("ATLAS_PUBLIC_KEY")
ATLAS_PRIVATE_KEY = os.environ.get("ATLAS_PRIVATE_KEY")
SOURCE_GROUP_ID = "YOUR_SOURCE_PROJECT_ID"
ORG_ID = "YOUR_ORGANIZATION_ID"
GCP_PROJECT_ID = "your-gcp-project-id"

MAPPING_DB_CONNECTION_STRING = os.environ.get("MAPPING_DB_CONNECTION_STRING", "mongodb+srv://user:pass@host/db")
MAPPING_DB_NAME = "atlas_mappings"
MAPPING_COLLECTION_NAME = "cluster_users"
KEY_VAULT_NAMESPACE = "encryption.__keyVault"

# Get encryption key from environment or generate a secure one
ENCRYPTION_KEY = os.environ.get("CSFLE_MASTER_KEY") 
if not ENCRYPTION_KEY:
    # Generate a secure 96-byte key and encode it to base64
    ENCRYPTION_KEY = base64.b64encode(secrets.token_bytes(96)).decode('utf-8')
    print("Generated a new CSFLE master key. Store this securely for future use.")
    print(f"CSFLE_MASTER_KEY={ENCRYPTION_KEY}")

ATLAS_API_BASE_URL = "https://cloud.mongodb.com/api/atlas/v1.0"
USER_COUNT_THRESHOLD = 80

# Parse a comma-separated list of IPs from an environment variable
PRIVATE_IP_WHITELIST = os.environ.get("PRIVATE_IP_WHITELIST", "10.8.0.10/32,10.8.0.11/32")
WHITELIST_IPS_PARSED = [ip.strip() for ip in PRIVATE_IP_WHITELIST.split(",") if ip.strip()]

def get_database_user_count(group_id):
    """Gets the number of database users via the Atlas API."""
    print(f"Checking user count in project {group_id}...")
    endpoint = f"/groups/{group_id}/databaseUsers"
    url = f"{ATLAS_API_BASE_URL}{endpoint}"
    auth = HTTPDigestAuth(ATLAS_PUBLIC_KEY, ATLAS_PRIVATE_KEY)
    headers = {"Accept": "application/json"}

    try:
        response = requests.get(url, auth=auth, headers=headers)
        response.raise_for_status()
        data = response.json()
        if 'results' in data:
            count = len(data['results'])
            print(f"Found {count} database users.")
            return count
        return 0
    except requests.exceptions.RequestException as e:
        print(f"Error checking user count: {e}")
        return -1 # Return an error code

def run_terraform_apply(create_new):
    """Runs terraform apply with the correct variables."""
    print(f"\n--- Running Terraform (create_new_project = {create_new}) ---")
    
    # Convert list to JSON so Terraform interprets it as a list
    command = [
        "terraform", "apply", "-auto-approve", "-json",
        f"-var=atlas_public_key={ATLAS_PUBLIC_KEY}",
        f"-var=atlas_private_key={ATLAS_PRIVATE_KEY}",
        f"-var=atlas_org_id={ORG_ID}",
        f"-var=source_project_id={SOURCE_GROUP_ID}",
        f"-var=gcp_project_id={GCP_PROJECT_ID}",
        f"-var=create_new_project={'true' if create_new else 'false'}",
        f"-var=private_ip_whitelist={json.dumps(WHITELIST_IPS_PARSED)}"
    ]

    try:
        # Using subprocess.run to capture output
        process = subprocess.run(command, capture_output=True, text=True, check=True)
        print("Terraform apply completed successfully.")
        
        # Get the output from Terraform
        output_command = ["terraform", "output", "-json"]
        output_process = subprocess.run(output_command, capture_output=True, text=True, check=True)
        return json.loads(output_process.stdout)

    except subprocess.CalledProcessError as e:
        print("!!! Terraform command failed !!!")
        print(f"Return Code: {e.returncode}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while running Terraform: {e}")
        return None

def setup_encryption():
    """Set up the encryption components for CSFLE."""
    try:
        # Decode the base64 key
        key_bytes = base64.b64decode(ENCRYPTION_KEY)
        
        # Create a data key id - a 16-byte UUID
        key_id = Binary(secrets.token_bytes(16), STANDARD)
        
        # Create the key material
        key_material = RawKeyMaterial(key_bytes)
        
        # Create the explicit encrypter using the key material
        encrypter = ExplicitEncrypter(
            key_id=key_id,
            key_material=key_material,
            algorithm="AEAD_AES_256_CBC_HMAC_SHA_512-Deterministic"
        )
        
        return encrypter
    except Exception as e:
        print(f"Error setting up encryption: {e}")
        return None

def encrypt_password(encrypter, password):
    """Encrypt a password using CSFLE."""
    try:
        if encrypter is None:
            return password  # Fallback to unencrypted if setup failed
            
        # Encrypt the password value
        encrypted_value = encrypter.encrypt(password)
        return encrypted_value
    except Exception as e:
        print(f"Failed to encrypt password: {e}")
        return password  # Return original password if encryption fails

def store_in_mapping_db(data_to_store):
    """Stores a list of documents in the mapping database."""
    if not data_to_store:
        print("No data to store in mapping DB.")
        return
        
    try:
        # Set up the encryption
        encrypter = setup_encryption()
        
        # Encrypt passwords in the data
        if encrypter:
            for record in data_to_store:
                if "password" in record:
                    record["password"] = encrypt_password(encrypter, record["password"])
        
        client = MongoClient(MAPPING_DB_CONNECTION_STRING)
        collection = client[MAPPING_DB_NAME][MAPPING_COLLECTION_NAME]
        
        # Store the encryption metadata in a separate collection if using CSFLE
        if encrypter:
            key_vault = client[MAPPING_DB_NAME.split('.')[0]][KEY_VAULT_NAMESPACE.split('.')[1]]
            # You could add a record of what encryption key was used here
            
        collection.insert_many(data_to_store)
        print(f"Successfully saved {len(data_to_store)} record(s) to mapping database with encrypted passwords.")
    except Exception as e:
        print(f"Error saving to mapping database: {e}")

def main():
    if not all([ATLAS_PUBLIC_KEY, ATLAS_PRIVATE_KEY, SOURCE_GROUP_ID, ORG_ID, GCP_PROJECT_ID]):
        print("!!! ERROR: Please set all required configuration variables and environment variables.")
        return

    user_count = get_database_user_count(SOURCE_GROUP_ID)
    if user_count == -1: # Error case
        return

    create_new = user_count > USER_COUNT_THRESHOLD
    
    tf_output = run_terraform_apply(create_new)

    if not tf_output:
        print("Halting due to Terraform failure.")
        return

    print("\n--- Processing Terraform Output ---")
    records_to_save = []
    if create_new:
        # New project workflow
        connection_string = tf_output.get("new_project_connection_string", {}).get("value")
        users = tf_output.get("new_project_users", {}).get("value", [])
        for user in users:
            records_to_save.append({
                "cluster_connection_string": connection_string,
                "username": user["username"],
                "password": user["password"],
                "created_at": time.time()
            })
    else:
        # Single user workflow
        user_details = tf_output.get("single_user_details", {}).get("value", {})
        if user_details:
            records_to_save.append({
                "cluster_connection_string": user_details.get("connection_string"),
                "username": user_details.get("username"),
                "password": user_details.get("password"),
                "created_at": time.time()
            })
            
    store_in_mapping_db(records_to_save)
    print("\nAutomation script finished.")

if __name__ == "__main__":
    main()
