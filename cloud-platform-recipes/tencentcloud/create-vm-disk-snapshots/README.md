# Create VM Disk Snapshots on Tencent Cloud

Chinese version: `README.zh-CN.md`

Status: implemented

This recipe runs on the control node, discovers disks attached to explicit CVM instances in one region, and creates Tencent Cloud CBS snapshots for those disks.

Two modes are supported:

- independent disk snapshots with `use_consistency_group_snapshot=false`
- provider-native snapshot groups with `use_consistency_group_snapshot=true`

The snapshot-group path is intended for crash-consistent multi-disk capture within one CVM instance. It does not provide guest-side application consistency.

## Files

- `playbook.yml`: executable Tencent Cloud snapshot playbook
- `tencentcloud_snapshot_recipe.py`: local Python workflow helper used by the playbook

## Requirements

- Ansible available on the control node
- Python access to the Tencent Cloud SDK packages in the same Python environment Ansible uses
- Tencent Cloud credentials with permission to query CVM instances and create CBS snapshots
- A non-production account or region for validation before broader use

Install the SDK packages into the Python environment that runs `ansible-playbook`:

```bash
python -m pip install \
  tencentcloud-sdk-python-common \
  tencentcloud-sdk-python-cvm \
  tencentcloud-sdk-python-cbs
```

## Required Variables

- `target_instances`: non-empty list of CVM instance identifiers
- `snapshot_name_prefix`: non-empty snapshot name prefix
- `tencentcloud_region`: target region for the CVM instances

## Optional Variables

- `target_hosts`: execution host group, defaults to `localhost`
- `include_boot_disk`: whether to snapshot the system disk, defaults to `true`
- `data_disk_ids`: list of attached data-disk IDs to include; when omitted, all attached data disks are included
- `use_consistency_group_snapshot`: whether to create a Tencent Cloud snapshot group, defaults to `false`
- `wait_for_snapshot_ready`: whether to wait until snapshots reach `NORMAL`, defaults to `true`
- `snapshot_tags`: tag mapping like `{"env":"dev"}` or a list of `{Key, Value}` objects
- `snapshot_ready_timeout_seconds`: wait timeout for ready snapshots, defaults to `1800`
- `snapshot_poll_interval_seconds`: polling interval while waiting, defaults to `10`
- `tencentcloud_secret_id`: optional explicit credential override
- `tencentcloud_secret_key`: optional explicit credential override
- `tencentcloud_token`: optional temporary credential token

## Unsupported Variables

- `snapshot_description`: Tencent Cloud snapshot APIs used by this recipe do not support it, so the playbook rejects it.

## Authentication

Recommended path: export credentials in the shell before running the playbook.

```bash
export TENCENTCLOUD_SECRET_ID=AKIDEXAMPLE
export TENCENTCLOUD_SECRET_KEY=SECRETEXAMPLE
```

If you are using temporary credentials, also set:

```bash
export TENCENTCLOUD_TOKEN=TOKENEXAMPLE
```

You can also pass `tencentcloud_secret_id`, `tencentcloud_secret_key`, and `tencentcloud_token` as playbook variables, but shell environment variables are usually the cleaner option for local execution.

## Consistency Group Support

Support status: implemented.

Current behavior and constraints:

- `use_consistency_group_snapshot=true` uses Tencent Cloud `CreateSnapshotGroup`
- the selected disks must belong to the same CVM instance
- the recipe enforces `target_instances | length == 1` for snapshot groups
- the result is still guest crash consistency, not application consistency
- feature availability can still depend on Tencent Cloud account or regional rollout state

## Usage

Syntax check:

```bash
ansible-playbook -i localhost, --syntax-check cloud-platform-recipes/tencentcloud/create-vm-disk-snapshots/playbook.yml
```

Create independent snapshots for all disks attached to one instance:

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/tencentcloud/create-vm-disk-snapshots/playbook.yml \
  -e '{"target_instances":["ins-abc12345"],"snapshot_name_prefix":"daily-20260428","tencentcloud_region":"ap-guangzhou"}'
```

Create a snapshot group for one instance and wait for completion:

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/tencentcloud/create-vm-disk-snapshots/playbook.yml \
  -e '{"target_instances":["ins-abc12345"],"snapshot_name_prefix":"daily-20260428","tencentcloud_region":"ap-guangzhou","use_consistency_group_snapshot":true}'
```

Snapshot only selected attached data disks and skip the boot disk:

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/tencentcloud/create-vm-disk-snapshots/playbook.yml \
  -e '{"target_instances":["ins-abc12345"],"snapshot_name_prefix":"daily-20260428","tencentcloud_region":"ap-guangzhou","include_boot_disk":false,"data_disk_ids":["disk-111","disk-222"]}'
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

- This recipe mutates Tencent Cloud snapshot state.
- Snapshot retention and cleanup are out of scope.
- Provider-native snapshot groups do not imply guest-side application consistency.
