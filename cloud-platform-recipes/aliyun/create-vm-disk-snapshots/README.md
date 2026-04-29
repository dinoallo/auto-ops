# Create VM Disk Snapshots on Aliyun

Chinese version: `README.zh-CN.md`

Status: implemented

This recipe runs on the control node, discovers disks attached to explicit ECS instances in one region, and creates Aliyun ECS snapshots for those disks.

Two modes are supported:

- independent disk snapshots with `use_consistency_group_snapshot=false`
- provider-native snapshot-consistent groups with `use_consistency_group_snapshot=true`

The snapshot-group path is intended for crash-consistent multi-disk capture within one ECS instance. It does not provide guest-side application consistency.

## Files

- `playbook.yml`: executable Aliyun snapshot playbook
- `aliyun_snapshot_recipe.py`: local Python workflow helper used by the playbook

## Requirements

- Ansible available on the control node
- Python access to the Aliyun ECS SDK packages in the same Python environment Ansible uses
- Aliyun credentials with permission to query ECS instances and create snapshots
- A non-production account or region for validation before broader use

Install the SDK packages into the Python environment that runs `ansible-playbook`:

```bash
python -m pip install \
  alibabacloud_ecs20140526 \
  alibabacloud_credentials \
  alibabacloud_tea_openapi \
  alibabacloud_tea_util \
  Tea
```

## Required Variables

- `target_instances`: non-empty list of ECS instance identifiers
- `snapshot_name_prefix`: non-empty snapshot name prefix
- `aliyun_region`: target region for the ECS instances

## Optional Variables

- `target_hosts`: execution host group, defaults to `localhost`
- `include_boot_disk`: whether to snapshot the system disk, defaults to `true`
- `data_disk_ids`: list of attached data-disk IDs to include; when omitted, all attached data disks are included
- `use_consistency_group_snapshot`: whether to create an Aliyun snapshot-consistent group, defaults to `false`
- `wait_for_snapshot_ready`: whether to wait until snapshots finish, defaults to `true`
- `snapshot_description`: optional snapshot or snapshot-group description
- `snapshot_tags`: tag mapping like `{"env":"dev"}` or a list of `{Key, Value}` objects
- `snapshot_ready_timeout_seconds`: wait timeout for ready snapshots, defaults to `1800`
- `snapshot_poll_interval_seconds`: polling interval while waiting, defaults to `10`
- `aliyun_access_key_id`: optional explicit credential override
- `aliyun_access_key_secret`: optional explicit credential override
- `aliyun_security_token`: optional temporary credential token

## Authentication

Recommended path: export credentials in the shell before running the playbook.

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID=EXAMPLE
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=EXAMPLE
```

If you are using temporary credentials, also set:

```bash
export ALIBABA_CLOUD_SECURITY_TOKEN=TOKENEXAMPLE
```

You can also pass `aliyun_access_key_id`, `aliyun_access_key_secret`, and `aliyun_security_token` as playbook variables.

## Consistency Group Support

Support status: implemented.

Current behavior and constraints:

- `use_consistency_group_snapshot=true` uses Aliyun `CreateSnapshotGroup`
- the recipe enforces `target_instances | length == 1` for snapshot groups
- the selected disks must be eligible cloud disks attached to that ECS instance
- the result is guest crash consistency, not application consistency
- feature availability can still depend on account permissions and regional rollout state

## Usage

Syntax check:

```bash
ansible-playbook -i localhost, --syntax-check cloud-platform-recipes/aliyun/create-vm-disk-snapshots/playbook.yml
```

Create independent snapshots for all disks attached to one instance:

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/aliyun/create-vm-disk-snapshots/playbook.yml \
  -e '{"target_instances":["i-abc12345"],"snapshot_name_prefix":"daily-20260429","aliyun_region":"cn-hangzhou"}'
```

Create a snapshot-consistent group for one instance and wait for completion:

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/aliyun/create-vm-disk-snapshots/playbook.yml \
  -e '{"target_instances":["i-abc12345"],"snapshot_name_prefix":"daily-20260429","aliyun_region":"cn-hangzhou","use_consistency_group_snapshot":true}'
```

Snapshot only selected attached data disks and skip the boot disk:

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/aliyun/create-vm-disk-snapshots/playbook.yml \
  -e '{"target_instances":["i-abc12345"],"snapshot_name_prefix":"daily-20260429","aliyun_region":"cn-hangzhou","include_boot_disk":false,"data_disk_ids":["d-111","d-222"]}'
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

- This recipe mutates Aliyun snapshot state.
- Snapshot retention and cleanup are out of scope.
- Provider-native snapshot groups do not imply guest-side application consistency.
