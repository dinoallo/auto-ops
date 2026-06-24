# ensure-etcdctl

Ensure `etcdctl` exists on every master node. The playbook first checks for
`etcdctl` in each target node's `PATH`; nodes that already have it are only
kept when they pass `ETCDCTL_API=3 etcdctl version`.

Missing nodes can be repaired in either of two ways:

- `copy`: copy a known-good `etcdctl` from `etcdctl_host` through the Ansible
  controller. This is the default and is usually run with `etcdctl_host=master0`.
- `download`: download an upstream etcd release archive on each missing node and
  install the bundled `etcdctl` binary.

## Usage

Copy from a source master:

```bash
ansible-playbook -i inventory.ini ansible-recipes/ensure-etcdctl/playbook.yml \
  -e etcdctl_install_method=copy \
  -e etcdctl_host=master0
```

Download from the internet:

```bash
ansible-playbook -i inventory.ini ansible-recipes/ensure-etcdctl/playbook.yml \
  -e etcdctl_install_method=download \
  -e etcdctl_download_version=v3.5.17
```

## Common Variables

| Variable | Default | Description |
| --- | --- | --- |
| `target_hosts` | `masters` | Inventory group or host pattern to manage. |
| `etcdctl_command` | `etcdctl` | Command name used when checking the existing `PATH`. |
| `etcdctl_api` | `3` | `ETCDCTL_API` value used for source and target version checks. |
| `etcdctl_install_method` | `copy` | Installation source for missing nodes: `copy` or `download`. |
| `etcdctl_install_path` | `/usr/local/bin/etcdctl` | Destination path used when installing a missing binary. |

## Copy Variables

| Variable | Default | Description |
| --- | --- | --- |
| `etcdctl_host` | first host in `masters` | Source host that already has `etcdctl`. |
| `etcdctl_source_path` | empty | Explicit source binary path. If empty, the playbook runs `command -v etcdctl` on `etcdctl_host`. |
| `etcdctl_controller_cache_dir` | `/tmp/ansible-etcdctl` | Temporary cache directory on the Ansible controller. |

## Download Variables

| Variable | Default | Description |
| --- | --- | --- |
| `etcdctl_download_version` | `v3.5.17` | Upstream etcd release version. |
| `etcdctl_download_url` | derived from version, OS, and arch | Override URL for mirrors or internal artifact stores. |
| `etcdctl_download_checksum` | empty | Optional checksum passed to `get_url`, for example `sha256:<digest>`. |
| `etcdctl_download_os` | remote `ansible_system | lower` | Archive OS component. |
| `etcdctl_download_arch` | mapped from `ansible_architecture` | Archive architecture component. |
| `etcdctl_download_tmp_dir` | `/tmp/ansible-etcdctl-download` | Temporary directory on each target node. |
| `etcdctl_download_cleanup` | `true` | Remove the temporary download directory after installation. |
