# Ansible Recipes

Chinese version: `README.zh-CN.md`

This directory contains executable Ansible recipes. Each recipe is usually a standalone directory with at least:

- `playbook.yml`: the executable playbook
- `README.md`: usage, variables, and examples

## Before You Start

Make sure you have:

1. `ansible-playbook` installed
2. A working inventory file such as `inventory.ini`
3. SSH access and the required permissions for the target hosts

The basic invocation pattern is:

```bash
ansible-playbook \
  -i inventory.ini \
  path/to/playbook.yml \
  -e key=value
```

## Available Recipes

### safely-copying-files

Path: `ansible-recipes/safely-copying-files/playbook.yml`

Purpose: copy a local file from the control machine to remote hosts, while asking for confirmation before replacing an existing file with different content.

Behavior:

1. Fail immediately if the local source file does not exist
2. Copy directly if the remote destination file does not exist
3. Skip if the remote destination file already matches the source
4. Ask whether to replace the file if the destination exists and differs from the source

Required variables:

- `source_file`: local path on the control machine
- `dest_file`: destination path on the remote host

Optional variables:

- `target_hosts`: target host group, defaults to `all`
- `checksum_algorithm`: checksum algorithm used for file comparison, defaults to `sha256`
- `backup_on_replace`: whether to create a backup before replacing the remote file, defaults to `false`
- `safe_copy_owner`: owner to set on the copied file
- `safe_copy_group`: group to set on the copied file
- `safe_copy_mode`: mode to set on the copied file

Example:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/safely-copying-files/playbook.yml \
  -e source_file=./files/app.conf \
  -e dest_file=/etc/myapp/app.conf \
  -e target_hosts=web
```

To keep a backup when replacing the remote file:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/safely-copying-files/playbook.yml \
  -e source_file=./files/app.conf \
  -e dest_file=/etc/myapp/app.conf \
  -e target_hosts=web \
  -e backup_on_replace=true
```

If the remote file already exists and differs from the source, the playbook prompts for confirmation. Only `yes` or `y` will proceed with the replacement.

For recipe-specific details, see `ansible-recipes/safely-copying-files/README.md`.
