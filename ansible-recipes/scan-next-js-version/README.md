# Scan Next.js Process Versions

Chinese version: `README.zh-CN.md`

This recipe scans Linux processes whose first command-line argument looks like
`next-server (v14.2.35)`. It extracts the value inside the parentheses as the
Next.js version, reads the process cgroup, and uses `crictl` to resolve the
cgroup's Kubernetes Pod UID to a namespace and Pod name.

## What It Does

1. Reads `/proc/<pid>/cmdline` on each target host.
2. Matches the first argument against `<process name> (<version>)`.
3. Reads `/proc/<pid>/cgroup` and extracts a Kubernetes Pod UID from cgroup v1
   or cgroup v2 paths.
4. Runs `crictl pods --output=json` once when a Pod UID is found, then maps the
   UID to `namespace/name`.
5. Prints only `namespace`, `pod`, and `version` for each matching process.

The scan succeeds when a matching process is not running, when the process is
not in a Kubernetes Pod, or when the optional Pod lookup is unavailable. In
those cases, `namespace` and `pod` are printed as `-`.

## Requirements

- Linux target hosts with `/proc` mounted
- Python 3 on each target host
- Root privileges so the playbook can inspect every process
- `crictl` configured to access the node's CRI runtime when Pod names should be resolved

## Variables

- `target_hosts`: inventory pattern, defaults to `'all'`
- `next_js_process_name`: process title prefix, defaults to `'next-server'`
- `next_js_proc_root`: proc filesystem path, defaults to `'/proc'`
- `next_js_python_interpreter`: Python path on target hosts, defaults to `'/usr/bin/python3'`
- `next_js_lookup_cri_pods`: whether to resolve Pod UIDs through `crictl`, defaults to `true`
- `next_js_crictl_command`: crictl command or path, defaults to `'crictl'`
- `next_js_output_file`: absolute file path on the Ansible control node, defaults to empty; when set, results from all target hosts are combined and the file is overwritten on each run

## Usage

Validate the playbook syntax:

```bash
ansible-playbook --syntax-check ansible-recipes/scan-next-js-version/playbook.yml
```

Scan all inventory hosts:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/scan-next-js-version/playbook.yml
```

Write the combined result to a file on the Ansible control node:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/scan-next-js-version/playbook.yml \
  -e next_js_output_file=/var/tmp/next-js-versions.txt
```

Scan only worker nodes and skip the CRI Pod lookup:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/scan-next-js-version/playbook.yml \
  -e target_hosts=workers \
  -e next_js_lookup_cri_pods=false
```

Example output:

```text
namespace=demo pod=web-7c9d6d8f6f-abcde version=v14.2.35
```

The combined content is written to `next_js_output_file` on the control node when that variable is set. The file contains no target-host column; each result line still contains only `namespace`, `pod`, and `version`.
