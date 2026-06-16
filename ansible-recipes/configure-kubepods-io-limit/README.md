# Configure kubepods IO Limit

Chinese version: `README.zh-CN.md`

This recipe installs a persistent cgroup v2 IO limit for `kubepods.slice`. It writes a limit such as `252:0 rbps=104857600 wbps=52428800` to `/sys/fs/cgroup/kubepods.slice/io.max` after the file exists.

The playbook uses a `systemd.path` unit to watch for `kubepods.slice/io.max`, then triggers a one-shot service that applies the limit. This avoids the race where a udev rule runs before kubelet or systemd has created `kubepods.slice`.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Accepts either a block device path such as `/dev/vda` or an explicit `major:minor` value such as `252:0`.
2. Resolves the block device path to `major:minor` on each target host when `io_limit_device` is used.
3. Installs `/usr/local/sbin/set-kubepods-io-limit.sh`.
4. Installs `kubepods-io-limit.service`. The service uses `RemainAfterExit=true` so it stays active after a successful one-shot run and is not repeatedly retriggered by `PathExists`.
5. Installs and enables `kubepods-io-limit.path`, which waits for `/sys/fs/cgroup/kubepods.slice/io.max` to appear before running the service.

## Requirements

- Linux hosts using cgroup v2
- A systemd-managed Kubernetes node where kubelet creates `kubepods.slice`
- SSH access with privilege escalation
- `bash`, `stat`, `logger`, and `systemd` on the target hosts

## Required Variables

Set one of these variables:

- `io_limit_device`: block device path on the target host, for example `/dev/vda`
- `io_limit_major_minor`: explicit cgroup device selector, for example `252:0`

If both are set, `io_limit_major_minor` takes precedence.

## Optional Variables

- `target_hosts`: inventory host pattern, defaults to `all`
- `io_limit_rbps`: read limit in bytes per second, defaults to `104857600`
- `io_limit_wbps`: write limit in bytes per second, defaults to `52428800`
- `io_limit_cgroup_io_max`: cgroup control file, defaults to `/sys/fs/cgroup/kubepods.slice/io.max`
- `io_limit_script_path`: installed script path, defaults to `/usr/local/sbin/set-kubepods-io-limit.sh`
- `io_limit_systemd_unit_name`: systemd unit basename, defaults to `kubepods-io-limit`
- `io_limit_run_immediately`: also start the one-shot service during the playbook run, defaults to `false`

## Usage

Validate syntax before running:

```bash
ansible-playbook --syntax-check ansible-recipes/configure-kubepods-io-limit/playbook.yml
```

Run with a block device path:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-kubepods-io-limit/playbook.yml \
  -e io_limit_device=/dev/vda
```

Run with an explicit `major:minor` selector:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-kubepods-io-limit/playbook.yml \
  -e io_limit_major_minor=252:0
```

Override IO limits:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-kubepods-io-limit/playbook.yml \
  -e io_limit_device=/dev/vda \
  -e io_limit_rbps=104857600 \
  -e io_limit_wbps=52428800
```

## Notes

- The script writes to `io.max` with `>` rather than `>>`, because cgroup control files consume each write as a configuration command.
- `io_limit_run_immediately` defaults to `false` so the playbook does not wait up to 300 seconds on nodes where `kubepods.slice` has not been created yet.
- The playbook clears any previous `start-limit-hit` state for `kubepods-io-limit.service` with `systemctl reset-failed`.
- Prefer stable device paths such as `/dev/disk/by-id/...` when device names may change across reboots.
