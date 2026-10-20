# Synchronize SSH Authorized Keys

Chinese version: `README.zh-CN.md`

This recipe converges the SSH authorized keys for one account to the same key
set on every selected target host. The key set can be supplied inline or read
from a file on the Ansible control node.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Validates that exactly one authorized-key source was provided.
2. Reads and normalizes the source key set on the Ansible control node when a
   local source file is used.
3. Creates the target user's `.ssh` directory when needed.
4. Synchronizes the authorized keys on each target host one host at a time.

By default, `authorized_keys_exclusive` is `true`, so keys that are not in the
provided set are removed. Set it to `false` when the recipe should only ensure
that the provided keys are present.

## Requirements

- Ansible with the `ansible.posix` collection
- SSH access to the target hosts
- Privilege escalation when managing another user's authorized keys, such as
  the default `root` account
- A newline-separated file of OpenSSH public keys, or an inline string/list of
  public keys

## Variables

- `target_hosts`: inventory pattern, defaults to `'all'`
- `authorized_keys`: one OpenSSH public key string or a list of public keys;
  mutually exclusive with `authorized_keys_file`
- `authorized_keys_file`: local path on the Ansible control node containing the
  authorized keys, mutually exclusive with `authorized_keys`
- `authorized_key_user`: account whose authorized keys are managed, defaults to
  `'root'`
- `authorized_keys_path`: optional explicit remote path; when omitted,
  `ansible.posix.authorized_key` uses the target user's default path
- `authorized_keys_exclusive`: remove keys not in the supplied set, defaults to
  `true`
- `authorized_keys_manage_dir`: create the target user's `.ssh` directory when
  needed, defaults to `true`

## Usage

Validate the playbook syntax:

```bash
ansible-playbook --syntax-check ansible-recipes/sync-authorized-keys/playbook.yml
```

Recommended: keep the public keys in a local file on the Ansible control node,
with one key per line:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/sync-authorized-keys/playbook.yml \
  -e target_hosts=all \
  -e authorized_keys_file=./files/cluster-authorized_keys
```

Manage a non-root account:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/sync-authorized-keys/playbook.yml \
  -e target_hosts=workers \
  -e authorized_key_user=deploy \
  -e authorized_keys_file=./files/deploy-authorized_keys
```

Pass a small key set inline:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/sync-authorized-keys/playbook.yml \
  -e '{"authorized_keys":["ssh-ed25519 AAAA... operator@example"]}'
```

Only add the supplied keys and keep other existing keys:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/sync-authorized-keys/playbook.yml \
  -e authorized_keys_file=./files/additional-authorized_keys \
  -e authorized_keys_exclusive=false
```

## Important Warnings

- Keep the SSH key used for the current Ansible connection in the synchronized
  key set, or the next connection may fail after an exclusive synchronization.
- `authorized_keys_file` is read from the Ansible control node, not from the
  target hosts.
- This recipe manages public keys only; it does not generate, copy, or remove
  private keys.
- Review the key file before running with `authorized_keys_exclusive=true`,
  because unmanaged access can be removed.
