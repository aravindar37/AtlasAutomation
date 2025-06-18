# MongoDB Atlas Automation Tool

********************************************
****************** WIP *********************
********************************************

This tool automates the creation of MongoDB Atlas resources based on user count thresholds. It can either:
1. Create a new Atlas project with a cluster and multiple users when the user count exceeds a threshold
2. Add a single user to an existing project when below the threshold

## Prerequisites

### Software Requirements
- Python 3.8+
- Terraform 1.0.0+
- Git (for cloning the repository)
- pip (Python package manager)

### Accounts and Access
- MongoDB Atlas account with Organization Owner permissions
- GCP account with Project Owner permissions
- A MongoDB Atlas cluster to store mapping data (can be a free tier cluster)

## Dependencies

### Python Libraries
Install the required Python packages:

```bash
pip install pymongo requests pymongocrypt
```

### Terraform Providers
The following Terraform providers are automatically installed when running Terraform:
- MongoDB Atlas Provider (1.15.1+)
- Google Cloud Provider (5.34.0+)
- Random Provider (3.6.2+)

## Environment Setup

Set the following environment variables:

```bash
# MongoDB Atlas API Keys
export ATLAS_PUBLIC_KEY="your_atlas_public_key"
export ATLAS_PRIVATE_KEY="your_atlas_private_key"

# Connection string for the mapping database
export MAPPING_DB_CONNECTION_STRING="mongodb+srv://user:password@your-cluster-url/database"

# Optional: Pre-defined encryption key (will be auto-generated if not provided)
export CSFLE_MASTER_KEY="your_base64_encryption_key"
```

## Configuration

1. Clone the repository:

```bash
git clone <repository-url>
cd Emergent
```

2. Edit the configuration variables in `run_automation.py`:

```python
SOURCE_GROUP_ID = "YOUR_SOURCE_PROJECT_ID"  # ID of your existing Atlas project
ORG_ID = "YOUR_ORGANIZATION_ID"             # MongoDB Atlas Organization ID
GCP_PROJECT_ID = "your-gcp-project-id"      # GCP Project ID for network peering
```

3. Optionally, modify Terraform variables in a new `terraform.tfvars` file:

```
new_atlas_project_name = "Automated Project"
new_atlas_cluster_name = "main-cluster"
new_cluster_tier = "M10"
gcp_region = "us-east1"
```

## Running the Automation

1. Initialize Terraform:

```bash
terraform init
```

2. Run the automation script:

```bash
python run_automation.py
```

## How It Works

1. The script checks the current user count in the specified Atlas project
2. If the user count exceeds the threshold (default: 80):
   - A new Atlas project is created
   - Network peering is established with your GCP VPC
   - A new cluster is provisioned
   - 10 database users are created
3. If the user count is below the threshold:
   - A single new user is created in the existing project
4. User details (with encrypted passwords) are stored in the mapping database

## Understanding the Output

After running the automation, you will see:
- Terraform outputs showing created resources
- Connection strings and user credentials
- Confirmation of data saved to the mapping database

The encryption master key (if auto-generated) will be displayed during the first run. Save this key securely for future use.

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify your Atlas API keys are correct
   - Ensure the keys have the required permissions

2. **Terraform Errors**
   - Run `terraform plan` to see if there are any configuration issues
   - Check for existing resources that might conflict with creation

3. **Encryption Issues**
   - If you see encryption errors, verify the CSFLE_MASTER_KEY format is correct
   - The key should be properly base64-encoded

4. **Network Peering Issues**
   - Ensure your GCP account has the necessary permissions
   - Verify there are no overlapping CIDR blocks in your network

## Security Notes

- Passwords are encrypted before being stored in the mapping database
- The encryption key should be stored securely, separately from the database
- Consider using a secrets manager for production deployments

