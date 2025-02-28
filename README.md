# cosyne_vm

This repository stores the scripts that are locally available on every VM instance we spin up for the COSYNE 2024 conference. This repository is a submodule of the [gvc-vm-crd](https://github.com/talmolab/gcp-vm-crd) repo at the `vmassign/vm/local` directory.

## Testing Workflow Prerequisites

1. A Service Account in Google Cloud Platform (GCP) in `vmassign-dev` project. 
    - The service account should be created in the vmassign-dev project.
    - Grant appropriate IAM roles to enable authentication and Terraform execution.
2. A Workload Identity Federation in GCP.
    - The Workload Identity Federation should be created in the `vmassign-dev` project.
    - The Workload Identity Federation should be associated with the Service Account created in the prereq. 1.
3. It requires `vmassign-dev` project in GCP.

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
