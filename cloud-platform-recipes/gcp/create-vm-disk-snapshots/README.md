# Create VM Disk Snapshots on GCP

Chinese version: `README.zh-CN.md`

Status: implemented

This recipe runs on the control node, discovers disks attached to explicit Compute Engine instances in one project, and creates GCP disk snapshots for those disks.

Only one mode is supported:

- independent disk snapshots with `use_consistency_group_snapshot=false`

GCP standard disk snapshots do not expose a provider-native consistency group snapshot feature. If you need multi-disk crash-consistent capture on GCP, that belongs in a separate machine-image workflow instead of this disk-snapshot recipe.

## Files

- `playbook.yml`: executable GCP snapshot playbook
- `gcp_snapshot_recipe.py`: local Python workflow helper used by the playbook

## Requirements

- Ansible available on the control node
- Python access to the Google Cloud Compute SDK packages in the same Python environment Ansible uses
- Google Cloud credentials with permission to query Compute Engine instances and create snapshots
- A non-production project for validation before broader use

Install the SDK packages into the Python environment that runs `ansible-playbook`:

```bash
python -m pip install google-cloud-compute google-auth
```

## Required Variables

- `target_instances`: non-empty list of instance references
- `snapshot_name_prefix`: non-empty snapshot name prefix
- `gcp_project_id`: target Google Cloud project ID

Supported `target_instances` formats:

- instance name, when unique across zones in the project
- `zone/name`
- full instance self-link

## Optional Variables

- `target_hosts`: execution host group, defaults to `localhost`
- `include_boot_disk`: whether to snapshot the boot disk, defaults to `true`
- `data_disk_ids`: list of attached data-disk identifiers to include; disk name, numeric disk ID, and self-link all match
- `wait_for_snapshot_ready`: whether to wait until snapshots reach `READY`, defaults to `true`
- `snapshot_description`: optional snapshot description
- `snapshot_tags`: mapping or list of `{Key, Value}` objects; this recipe applies them as GCP snapshot labels
- `snapshot_ready_timeout_seconds`: wait timeout for ready snapshots, defaults to `1800`
- `snapshot_poll_interval_seconds`: polling interval while waiting, defaults to `10`
- `gcp_credentials_file`: optional path to a service-account credentials JSON file

## Unsupported Variables

- `use_consistency_group_snapshot`: this recipe rejects `true` because GCP standard snapshots do not support provider-native group snapshots

## Authentication

Recommended path: use Application Default Credentials.

```bash
gcloud auth application-default login
```

For service-account-based local execution, point `GOOGLE_APPLICATION_CREDENTIALS` to the JSON file:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

You can also pass `gcp_credentials_file` as a playbook variable.

## Scope Notes

Current behavior and constraints:

- the recipe creates one snapshot per selected disk
- both zonal and regional attached persistent disks are supported
- attached disks without a persistent disk source are ignored
- the result is per-disk snapshot output only; there is no native multi-disk consistency group mode

## Usage

Syntax check:

```bash
ansible-playbook -i localhost, --syntax-check cloud-platform-recipes/gcp/create-vm-disk-snapshots/playbook.yml
```

Create independent snapshots for all disks attached to one instance by name:

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/gcp/create-vm-disk-snapshots/playbook.yml \
  -e '{"target_instances":["app-1"],"snapshot_name_prefix":"daily-20260429","gcp_project_id":"example-project"}'
```

Create independent snapshots using a zonal reference:

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/gcp/create-vm-disk-snapshots/playbook.yml \
  -e '{"target_instances":["us-central1-a/app-1"],"snapshot_name_prefix":"daily-20260429","gcp_project_id":"example-project"}'
```

Snapshot only selected attached data disks and skip the boot disk:

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/gcp/create-vm-disk-snapshots/playbook.yml \
  -e '{"target_instances":["app-1"],"snapshot_name_prefix":"daily-20260429","gcp_project_id":"example-project","include_boot_disk":false,"data_disk_ids":["data-disk-1","data-disk-2"]}'
```

## Output

The playbook prints a normalized result structure with fields such as:

- `provider`
- `project`
- `consistency_mode`
- `created_snapshot_count`
- `results[]` containing instance ID, disk ID, snapshot ID, snapshot name, state, and zone

## Validation Notes

- `--syntax-check` is supported.
- `--check` is not supported because the recipe creates snapshots.
- Validate first in a non-production project.

## Warnings

- This recipe mutates GCP snapshot state.
- Snapshot retention and cleanup are out of scope.
- GCP machine images are a separate feature and are not implemented by this recipe.
