# Cloud Platform Recipes

Chinese version: `README.zh-CN.md`

This directory contains cloud-platform-focused recipes for operations that run against provider APIs instead of logging into guest operating systems over SSH.

Current scope:

- create disk snapshots for explicit VM instance targets
- keep one provider-specific recipe per cloud platform
- support provider-native consistency group snapshots when the platform supports them and the recipe implements that path

Current status:

- `aliyun/create-vm-disk-snapshots` is implemented
- `gcp/create-vm-disk-snapshots` is implemented
- `tencentcloud/create-vm-disk-snapshots` is implemented
- `volcengine/create-vm-disk-snapshots` is implemented

## Layout

- `IMPLEMENTATION-PLAN.md`: working implementation notes for the recipe family
- `aliyun/create-vm-disk-snapshots/`: Aliyun ECS snapshot recipe
- `gcp/create-vm-disk-snapshots/`: GCP Compute Engine snapshot recipe
- `tencentcloud/create-vm-disk-snapshots/`: Tencent Cloud CVM/CBS snapshot recipe
- `volcengine/create-vm-disk-snapshots/`: Volcengine ECS/EBS snapshot recipe

## Common Execution Model

These recipes are expected to:

1. run on the control node, usually with `localhost`
2. authenticate to the cloud provider using a supported local credential source
3. resolve explicit target VM instances
4. discover attached disks
5. create per-disk snapshots, or a provider-native consistency group snapshot when requested and supported
6. return normalized snapshot results

## Shared Variables

The provider implementations are aligned around this common contract:

- `target_instances`: non-empty list of target instance identifiers or references
- `snapshot_name_prefix`: non-empty prefix used to build snapshot names
- `include_boot_disk`: optional, defaults to `true`
- `data_disk_ids`: optional list to limit the snapshot scope
- `use_consistency_group_snapshot`: optional, defaults to `false`
- `wait_for_snapshot_ready`: optional, defaults to `true`
- `snapshot_description`: optional free-form description
- `snapshot_tags`: optional provider-specific labels or tags

Each provider recipe also requires provider-specific context such as region, project, or account scope.

## Consistency Group Support

Verified against official provider documentation on 2026-04-28:

- `aliyun`: supported for eligible same-instance cloud disks
- `gcp`: not supported for standard disk snapshots
- `tencentcloud`: supported through snapshot groups for disks attached to the same CVM instance
- `volcengine`: supported through snapshot consistency groups

For `gcp`, this snapshot recipe rejects `use_consistency_group_snapshot=true`. If multi-disk crash-consistent backup support is needed on GCP, that likely belongs in a separate machine-image recipe instead of a disk-snapshot recipe.

## Validation

Every provider recipe should support at least:

```bash
ansible-playbook -i localhost, --syntax-check cloud-platform-recipes/<provider>/create-vm-disk-snapshots/playbook.yml
```

Use non-production cloud accounts or projects for functional validation.

## Notes

- Provider-native consistency group snapshots are distinct from guest-side application-consistent backups.
- Snapshot retention and cleanup are out of scope for this recipe family.
- GCP target instance references can be plain names, `zone/name`, or full self-links.
