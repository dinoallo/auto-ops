# Resize Multiple Cloud Disks on Tencent Cloud

Chinese version: `README.zh-CN.md`

Status: implemented

This recipe runs on the control node and expands multiple Tencent Cloud CBS
disks through the `ResizeDisk` API. It is provider-side capacity expansion only:
it does not log in to a CVM or resize partitions, LVM physical volumes, or file
systems inside the guest operating system.

The workflow is deliberately idempotent for the requested target sizes:

- disks already at the target size are reported as `already_at_target`
- disks smaller than the target are expanded
- disks larger than the target fail before any resize request is submitted
- capacity reduction is never attempted because Tencent Cloud disk capacity
  cannot be reduced

## Files

- `playbook.yml`: executable Ansible playbook
- `tencentcloud_resize_disks_recipe.py`: local Python workflow helper used by the playbook

## Requirements

- Ansible available on the control node
- Python access to the Tencent Cloud SDK packages in the same environment used by `ansible-playbook`
- Tencent Cloud credentials with permission to describe and resize CBS disks
- A non-production account or region for validation before broader use

Install the SDK packages into the Python environment that runs `ansible-playbook`:

```bash
python -m pip install \
  tencentcloud-sdk-python-common \
  tencentcloud-sdk-python-cbs
```

## Required Variables

Common target size for all disks:

- `disk_ids`: non-empty list of CBS disk IDs
- `target_disk_size_gb`: target size in GB for every disk in `disk_ids`

Or specify a different target for each disk:

- `disk_resize_requests`: non-empty list of objects with `disk_id` and `target_size_gb`

The following variable is always required:

- `tencentcloud_region`: target CBS region

Do not provide both input forms in the same run.

## Optional Variables

- `target_hosts`: execution host group, defaults to `localhost`
- `wait_for_disk_ready`: wait until each resize reaches the target size and leaves `EXPANDING`, defaults to `true`
- `disk_ready_timeout_seconds`: timeout for each workflow, defaults to `1800`
- `disk_poll_interval_seconds`: polling interval, defaults to `10`
- `tencentcloud_secret_id`: optional explicit credential override
- `tencentcloud_secret_key`: optional explicit credential override
- `tencentcloud_token`: optional temporary credential token

## Authentication

Recommended path: export credentials in the shell before running the playbook.

```bash
export TENCENTCLOUD_SECRET_ID=AKIDEXAMPLE
export TENCENTCLOUD_SECRET_KEY=SECRETEXAMPLE
```

For temporary credentials, also set:

```bash
export TENCENTCLOUD_TOKEN=TOKENEXAMPLE
```

The credential needs permission for these CBS APIs in the target region:

- `DescribeDisks`
- `ResizeDisk`

Keep access keys out of committed variable files.

## Usage

Syntax check:

```bash
ansible-playbook -i localhost, --syntax-check \
  cloud-platform-recipes/tencentcloud/resize-cloud-disks/playbook.yml
```

Expand several disks to the same target size:

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/tencentcloud/resize-cloud-disks/playbook.yml \
  -e '{"disk_ids":["disk-111","disk-222"],"target_disk_size_gb":200,"tencentcloud_region":"ap-guangzhou"}'
```

Expand disks to different target sizes:

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/tencentcloud/resize-cloud-disks/playbook.yml \
  -e '{"disk_resize_requests":[{"disk_id":"disk-111","target_size_gb":200},{"disk_id":"disk-222","target_size_gb":500}],"tencentcloud_region":"ap-guangzhou"}'
```

To submit the requests without waiting for the provider-side operation to
finish, set `wait_for_disk_ready=false`. The output then reports
`resize_submitted`; it does not claim that the disk has reached the target size.

## Output

The playbook prints a result structure containing:

- `requested_disk_count`
- `resized_count` and `skipped_count`
- `results[]` with disk ID, previous size, requested target, observed size, provider state, and request ID

## Guest Operating System Follow-up

After the CBS disk has expanded, the guest may need a separate operation to
rescan the device and grow its partition, LVM volume, or file system. This
recipe intentionally does not perform those guest-side changes.

## Validation Notes and Warnings

- `--syntax-check` is supported.
- `--check` is not supported because `ResizeDisk` changes cloud disk capacity.
- Disk expansion is irreversible; validate every target size before execution.
- Multiple API calls can partially complete if a later request fails. Query the
  disks before rerunning; the same target sizes cause disks that have already
  reached the target to be skipped.
- Validate first in a non-production account or region.
