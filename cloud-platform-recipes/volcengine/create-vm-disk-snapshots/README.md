# Create VM Disk Snapshots on Volcengine

Chinese version: `README.zh-CN.md`

Status: implemented

This recipe runs on the control node, discovers disks attached to explicit ECS instances in one region, and creates Volcengine EBS snapshots for those disks.

Two modes are supported:

- independent disk snapshots with `use_consistency_group_snapshot=false`
- provider-native snapshot consistency groups with `use_consistency_group_snapshot=true`

The consistency-group path is intended for crash-consistent multi-disk capture within one ECS instance. It does not provide guest-side application consistency.

## Files

- `playbook.yml`: executable Volcengine snapshot playbook
- `volcengine_snapshot_recipe.py`: local Python workflow helper used by the playbook

## Requirements

- Ansible available on the control node
- Python access to the Volcengine SDK packages in the same Python environment Ansible uses
- Volcengine credentials with permission to query ECS instances and create EBS snapshots
- A non-production account or region for validation before broader use

Install the SDK packages into the Python environment that runs `ansible-playbook`:

```bash
python -m pip install volcengine-python-sdk
```

## Required Variables

- `target_instances`: non-empty list of ECS instance identifiers
- `snapshot_name_prefix`: non-empty snapshot name prefix
- `volcengine_region`: target region for the ECS instances

## Optional Variables

- `target_hosts`: execution host group, defaults to `localhost`
- `include_boot_disk`: whether to snapshot the boot disk, defaults to `true`
- `data_disk_ids`: list of attached data-disk IDs to include; disk name also matches when filtering
- `use_consistency_group_snapshot`: whether to create a Volcengine snapshot consistency group, defaults to `false`
- `wait_for_snapshot_ready`: whether to wait until snapshots finish, defaults to `true`
- `snapshot_description`: optional snapshot or snapshot-group description
- `snapshot_tags`: tag mapping like `{"env":"dev"}` or a list of `{Key, Value}` objects
- `snapshot_ready_timeout_seconds`: wait timeout for ready snapshots, defaults to `1800`
- `snapshot_poll_interval_seconds`: polling interval while waiting, defaults to `10`
- `volcengine_project_name`: optional Volcengine project name passed to ECS and EBS APIs
- `volcengine_access_key`: optional explicit credential override
- `volcengine_secret_key`: optional explicit credential override
- `volcengine_session_token`: optional temporary credential token

## Authentication

Recommended path: export credentials in the shell before running the playbook.

```bash
export VOLCENGINE_ACCESS_KEY=EXAMPLE
export VOLCENGINE_SECRET_KEY=EXAMPLE
```

If you are using temporary credentials, also set:

```bash
export VOLCENGINE_SESSION_TOKEN=TOKENEXAMPLE
```

You can also pass `volcengine_access_key`, `volcengine_secret_key`, and `volcengine_session_token` as playbook variables.

## Consistency Group Support

Support status: implemented.

Current behavior and constraints:

- `use_consistency_group_snapshot=true` uses Volcengine `CreateSnapshotGroup`
- the recipe enforces `target_instances | length == 1` for snapshot groups
- the result is guest crash consistency, not application consistency
- feature availability can still depend on account permissions and regional rollout state

## Usage

Syntax check:

```bash
ansible-playbook -i localhost, --syntax-check cloud-platform-recipes/volcengine/create-vm-disk-snapshots/playbook.yml
```

Create independent snapshots for all disks attached to one instance:

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/volcengine/create-vm-disk-snapshots/playbook.yml \
  -e '{"target_instances":["i-abc12345"],"snapshot_name_prefix":"daily-20260429","volcengine_region":"cn-beijing"}'
```

Create a snapshot consistency group for one instance and wait for completion:

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/volcengine/create-vm-disk-snapshots/playbook.yml \
  -e '{"target_instances":["i-abc12345"],"snapshot_name_prefix":"daily-20260429","volcengine_region":"cn-beijing","use_consistency_group_snapshot":true}'
```

Snapshot only selected attached data disks and skip the boot disk:

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/volcengine/create-vm-disk-snapshots/playbook.yml \
  -e '{"target_instances":["i-abc12345"],"snapshot_name_prefix":"daily-20260429","volcengine_region":"cn-beijing","include_boot_disk":false,"data_disk_ids":["vol-111","vol-222"]}'
```

## Output

The playbook prints a normalized result structure with fields such as:

- `provider`
- `region`
- `consistency_mode`
- `consistency_group_id`
- `created_snapshot_count`
- `results[]` containing instance ID, disk ID, snapshot ID, snapshot name, state, and zone

## Validation Notes

- `--syntax-check` is supported.
- `--check` is not supported because the recipe creates snapshots.
- Validate first in a non-production account or project.

## Warnings

- This recipe mutates Volcengine snapshot state.
- Snapshot retention and cleanup are out of scope.
- Provider-native snapshot groups do not imply guest-side application consistency.
