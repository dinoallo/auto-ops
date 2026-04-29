# VM Disk Snapshot Recipe Plan

Status: implemented baseline

This document defines the initial implementation plan for adding recipes under `cloud-platform-recipes/` to create disk snapshots for virtual machine instances across multiple cloud providers.

## Goal

Add a consistent set of provider-specific recipes that can create snapshots for disks attached to one or more VM instances on:

- Aliyun
- GCP
- Tencent Cloud
- Volcengine

The recipes should follow one common user-facing concept:

- choose a provider
- provide target VM instance identifiers
- discover attached disks
- create snapshots for those disks
- optionally request a provider-native consistency group snapshot when supported
- return created snapshot identifiers

## Non-Goals

The first version should not include:

- snapshot retention cleanup
- scheduled execution
- cross-provider abstraction in a single playbook
- application-consistent backup orchestration inside the guest
- restore workflows

Those can be added later as separate recipes or follow-up enhancements.

## Design Decision

Implement one recipe per provider instead of one cross-provider playbook.

Reasoning:

- provider authentication differs
- disk discovery APIs differ
- snapshot creation APIs differ
- validation and troubleshooting stay simpler when each provider is isolated

## Proposed Layout

```text
cloud-platform-recipes/
  README.md
  README.zh-CN.md
  IMPLEMENTATION-PLAN.md
  aliyun/
    create-vm-disk-snapshots/
      playbook.yml
      README.md
      README.zh-CN.md
  gcp/
    create-vm-disk-snapshots/
      playbook.yml
      README.md
      README.zh-CN.md
  tencentcloud/
    create-vm-disk-snapshots/
      playbook.yml
      README.md
      README.zh-CN.md
  volcengine/
    create-vm-disk-snapshots/
      playbook.yml
      README.md
      README.zh-CN.md
```

## Shared Recipe Contract

Each provider recipe should keep the same high-level input model where possible.

### Required Variables

- `target_instances`: list of VM instance IDs
- `snapshot_name_prefix`: prefix used to build snapshot names
- provider-specific region or project/account context
- provider-specific authentication inputs or preconfigured credential source

### Optional Variables

- `target_hosts`: execution host group if the playbook needs an Ansible host target, default to `localhost`
- `include_boot_disk`: whether to snapshot the boot/system disk, default `true`
- `data_disk_ids`: optional list to limit snapshots to selected attached disks
- `use_consistency_group_snapshot`: whether to request a provider-native group-consistent snapshot workflow when supported, default `false`
- `wait_for_snapshot_ready`: whether to wait for completion, default `true`
- `snapshot_description`: free-form description
- `snapshot_tags`: provider-specific labels or tags when supported

### Expected Output

Each recipe should surface a normalized result structure with:

- instance ID
- disk ID
- disk role or type
- snapshot ID
- snapshot name
- consistency mode used
- consistency group ID when applicable
- provider region or zone
- final status

## v1 Behavior

The first implementation should:

1. require explicit instance identifiers
2. discover attached disks for each instance
3. create snapshots for all eligible attached disks by default
4. support `use_consistency_group_snapshot=true` when the provider supports native group-consistent disk snapshots
5. fail early when consistency group snapshot is requested on an unsupported provider or unsupported disk set
6. fail early on missing instances or unsupported inputs
7. wait for snapshot completion by default when the provider API supports it clearly
8. treat snapshots as crash-consistent at the guest level unless the provider explicitly guarantees more

## Consistency Model

The plan should distinguish three different levels of consistency:

- independent disk snapshots: each disk snapshot is created separately with no cross-disk consistency guarantee
- provider-native consistency group snapshots: the provider coordinates a multi-disk snapshot set when supported
- application-consistent snapshots: guest-side quiescing or backup hooks coordinate application state before snapshot creation

The first version should support the first two where the provider API allows it. It should not attempt guest-side application quiescing.

## Safety Constraints

To keep the first version predictable:

- do not support wildcard instance selection
- do not delete or rotate older snapshots
- do not assume application consistency even when a provider-native consistency group snapshot is used
- require the user to bring valid cloud credentials
- document any provider rate limits or snapshot quotas
- default `use_consistency_group_snapshot` to `false` so the behavior is explicit and user-controlled

If a provider cannot perform a meaningful dry run, the recipe README must say so explicitly.

## Verified Provider Capability Snapshot

Verified against official provider documentation on 2026-04-28:

- Aliyun: supported through snapshot-consistent groups for eligible cloud disks in the same zone
- GCP: not supported for standard disk snapshots; standard snapshots are per-disk and Google positions machine images for crash-consistent multi-disk backups
- Tencent Cloud: supported through snapshot groups, with the documented API constraint that the selected cloud disks must belong to the same CVM instance
- Volcengine: supported through snapshot consistency groups and related API operations

## Provider Implementation Pattern

Each provider recipe should follow the same task flow:

1. validate required inputs
2. validate provider authentication context
3. resolve instance metadata
4. collect attached disk metadata
5. determine whether provider-native consistency group snapshot is requested and supported
6. build snapshot request payloads
7. create snapshots
8. optionally wait for completion
9. print normalized results

## Provider-Specific Notes To Resolve

### GCP

- determine whether the recipe should use the Google Ansible collection or `gcloud`
- handle zonal disk snapshot creation cleanly
- treat `use_consistency_group_snapshot=true` as unsupported in this snapshot recipe
- evaluate whether a separate machine-image recipe is needed for crash-consistent multi-disk backups on GCP
- confirm label support and wait semantics

### Aliyun

- confirm ECS disk discovery and snapshot module support in Ansible
- implement snapshot-consistent group creation for eligible disks and zones
- verify region scoping and naming constraints
- document required RAM permissions

### Tencent Cloud

- implemented with a local Python SDK helper instead of an Ansible collection
- snapshot group creation is constrained to disks attached to the same CVM instance
- document current product availability caveats if the account or region still requires feature enablement
- verify snapshot wait and response fields
- document credential sourcing expectations

### Volcengine

- confirm whether official Ansible support is sufficient
- implement snapshot consistency group creation through the official API path if collection support is insufficient
- if not, use official CLI or API calls with documented prerequisites
- define a clean normalization layer for results

## Documentation Work

The implementation should add:

- `cloud-platform-recipes/README.md`
- `cloud-platform-recipes/README.zh-CN.md`
- per-provider English README files
- per-provider Chinese README files

Each README should include:

- what the recipe does
- prerequisites
- required and optional variables
- authentication assumptions
- whether provider-native consistency group snapshot is supported
- what `use_consistency_group_snapshot` changes on that provider
- example command lines
- warnings about mutating behavior
- validation notes for `--syntax-check` and `--check`

## Validation Plan

Minimum validation for each provider recipe:

1. run `ansible-playbook --syntax-check` on the new `playbook.yml`
2. test against a non-production cloud account or project
3. validate one single-instance run
4. validate one multi-instance run
5. when supported, validate one run with `use_consistency_group_snapshot=true`
6. verify that created snapshots are visible in the provider console or CLI

When `--check` is unsupported or misleading, document that limitation instead of pretending the recipe is safely dry-runnable.

## Recommended Delivery Order

1. create the collection-level docs and directory skeleton
2. implement `tencentcloud/create-vm-disk-snapshots`
3. use the Tencent Cloud recipe to refine the shared variable contract
4. implement `aliyun/create-vm-disk-snapshots`
5. implement `gcp/create-vm-disk-snapshots`
6. implement `volcengine/create-vm-disk-snapshots`
7. update the repository root README files to mention `cloud-platform-recipes`

## Milestones

### Milestone 1

- add `cloud-platform-recipes` READMEs
- add all provider recipe directories
- add stub `playbook.yml` files with variable validation
- add provider README placeholders

### Milestone 2

- finish Tencent Cloud recipe implementation
- validate commands and document usage examples

### Milestone 3

- finish Aliyun and Tencent Cloud recipes
- validate their provider-specific behavior

### Milestone 4

- finish GCP and Volcengine recipes
- normalize documentation across all providers

## Implementation Outcome

The baseline implementation now exists for all four providers:

- `aliyun/create-vm-disk-snapshots`
- `gcp/create-vm-disk-snapshots`
- `tencentcloud/create-vm-disk-snapshots`
- `volcengine/create-vm-disk-snapshots`

Current implementation notes:

- Tencent Cloud, Aliyun, and Volcengine support provider-native consistency-group creation through local Python SDK helpers.
- GCP rejects `use_consistency_group_snapshot=true` and stays on per-disk snapshots only.
- All recipes run locally, validate inputs, rely on provider credentials from the control node, and print normalized results.
- Functional validation without live cloud credentials is still limited to syntax checks and negative-path execution.

## Open Questions

- Should these recipes be pure Ansible, or is provider CLI usage acceptable where Ansible support is weak?
- Should snapshot labels or tags be mandatory to support later retention workflows?
- Should boot disk selection be enabled by default on every provider?
- Should consistency group snapshot support stay boolean, or move to a future `snapshot_consistency_mode` enum once more modes are needed?
- Should future cleanup and retention be a separate recipe family instead of extending create workflows?

## Next Implementation Step

The next practical change is live validation against non-production cloud accounts or projects for each provider, starting with one single-instance run per platform and one consistency-group run where supported.
