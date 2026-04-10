# Safely Copying Files

Chinese version: `README.zh-CN.md`

This recipe copies a local file from the control machine to remote hosts using the following rules:

1. Check whether the local source file exists and fail immediately if it does not.
2. Copy directly if the remote destination file does not exist.
3. Do nothing if the remote destination file already matches the source.
4. Ask the user whether to replace the file if the destination exists and differs from the source.

Because this recipe prompts for confirmation, it runs one host at a time to avoid overlapping interactive prompts.

## Files

- `playbook.yml`: the recipe playbook

## Required Variables

- `source_file`: local path on the control machine
- `dest_file`: destination path on the remote host

## Optional Variables

- `target_hosts`: target host group, defaults to `all`
- `checksum_algorithm`: checksum algorithm used to compare file contents, defaults to `sha256`
- `backup_on_replace`: whether to create a backup before replacing the remote file, defaults to `false`
- `safe_copy_owner`: owner to set on the copied file
- `safe_copy_group`: group to set on the copied file
- `safe_copy_mode`: mode to set on the copied file

## Usage

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/safely-copying-files/playbook.yml \
  -e source_file=./files/app.conf \
  -e dest_file=/etc/myapp/app.conf \
  -e target_hosts=web
```

To run the recipe with a specific SSH key:

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/safely-copying-files/playbook.yml \
  -e source_file=./files/app.conf \
  -e dest_file=/etc/myapp/app.conf \
  -e target_hosts=web
```

If the destination file already exists and has different content, the playbook prompts like this:

```text
host.example.com already has /etc/myapp/app.conf with different contents.
Replace it with ./files/app.conf? Type 'yes' to continue
```

Only `yes` or `y` will replace the file. Any other input will skip the replacement.
