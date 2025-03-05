# cosyne_vm

This repository stores the scripts that are locally available on every VM instance we spin up for the COSYNE 2024 conference. This repository is a submodule of the [gvc-vm-crd](https://github.com/talmolab/gcp-vm-crd) repo at the `vmassign/vm/local` directory.

## Testing Workflow Prerequisites

1. A Service Account in Google Cloud Platform (GCP) in `vmassign-dev` project. 
    - The service account should be created in the vmassign-dev project.
    - Grant appropriate IAM roles to enable authentication and Terraform execution. The required roles are the following:
      - `roles/iam.serviceAccountUser`
      - `roles/iam.serviceAccountTokenCreator`
      - `roles/spanner.admin`
    - The name of the Service Account must be "github-actions-testing" in order to match the Service Account name in the GitHub Actions workflow.

2. A Workload Identity Federation (WIF) in GCP.
    - The Workload Identity Federation should be created in the `vmassign-dev` project.
    - The Workload Identity Federation should be associated with the Service Account created in the prerequisite above.

3. It requires `vmassign-dev` project in GCP and the Service Account and the WIF mentioned above are required under that project.

> Note: Workload Identity Federation (WIF) is used in this workflow because this does not require a service account key to be stored in the repository. Instead, the service account is associated with the WIF and the WIF is used to authenticate the service account. This is a more secure way to authenticate the service account.

For more information, read the [documentation for Google Auth](https://github.com/google-github-actions/auth)

## Steps to Take Before Testing the Workflow
1. Run the following command to setup the WIF in the `vmassign-dev` project. First, create the Workload Identity Pool:
  ```bash
  gcloud iam workload-identity-pools create "github-actions" \
    --project="${PROJECT_ID}" \
    --location="global" \
    --display-name="GitHub Actions Pool"
  ```

  Note: `${PROJECT_ID}` is the project ID of the `vmassign-dev` project.

  Run the following command to check the full name of the Workload Identity Pool:
  ```bash
  gcloud iam workload-identity-pools describe "github-actions" \
    --project="${PROJECT_ID}" \
    --location="global" \
    --format="value(name)"
  ```

2. Create the Workload Identity Pool Provider:
  ```bash
  gcloud iam workload-identity-pools providers create-oidc "my-repo" \
    --project="${PROJECT_ID}" \
    --location="global" \
    --workload-identity-pool="github" \
    --display-name="My GitHub repo Provider" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
    --attribute-condition="assertion.repository_owner == '${GITHUB_ORG}'" \
    --issuer-uri="https://token.actions.githubusercontent.com"
  ```

4. Create a new Service Account specifically for GitHub Actions Testing Workflow.
   ```bash
    gcloud iam service-accounts create github-actions-testing \
      --description="SA for GitHub Actions Testing Workflow" \
      --display-name="GitHub Actions Testing" \
      --project="vmassign-dev"
   ```

   Give the Service Account the required roles:

   To create a Spanner Database using Terraform, the Service Account needs the `roles/spanner.admin` role.
   ```bash
    gcloud projects add-iam-policy-binding vmassign-dev \
      --member="serviceAccount:github-actions-testing@vmassign-dev.iam.gserviceaccount.com" \
      --role="roles/spanner.admin"
    ```

    To authenticate the Service Account using Workload Identity Federation, the Service Account needs the `roles/iam.serviceAccountUser` and `roles/iam.workloadIdentityUser` roles.
    
    ```bash
    gcloud projects add-iam-policy-binding vmassign-dev \
      --member="serviceAccount:github-actions-testing@vmassign-dev.iam.gserviceaccount.com" \
      --role="roles/iam.serviceAccountUser"
    ```

    ```bash
    gcloud projects add-iam-policy-binding vmassign-dev \
      --member="serviceAccount:github-actions-testing@vmassign-dev.iam.gserviceaccount.com" \
      --role="roles/iam.workloadIdentityUser"
    ```

5. Associate the Service Account with the Workload Identity Pool Provider:
  ```bash
  gcloud iam service-accounts add-iam-policy-binding "github-actions-testing@${PROJECT_ID}.iam.gserviceaccount.com" \
    --project="${PROJECT_ID}" \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/${WORKLOAD_IDENTITY_POOL_ID}/attribute.repository/${REPO}"
  ```

## Testing Workflow

The workflow is triggered when a pull request is opened or updated. The workflow runs the following steps:
1. Checkout the repository.
2. Authenticate with Google Cloud using Workload Identity Federation.
3. Install Terraform.
4. Initialize Terraform.
5. Plan the Terraform changes.
6. Apply the Terraform changes to create the temporary database for testing in GCP under `vmassign-dev`. 
7. Run Pytest codes under `./tests` directory.
8. Destroy the temporary database after the tests are completed.

## Dependencies

While the VMs will just install these dependencies globally, developers should use a venv. For developers:
1. Open terminal in project root directory
2. Create a virtual environment

```python
python3 -m venv vm
```

3. Activate the virtual environment

```python3
source vm/bin/activate
```

4. Install dependencies:

```python
pip install -e .
```

## Removing your venv

1. Deactivate the virtual environment

```python
deactivate
```

2. Delete the entire venv folder named "gvc" (assuming you followed our naming convention in creating the venv).
