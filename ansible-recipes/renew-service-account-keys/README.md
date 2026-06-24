# Generating a Staged Kubernetes ServiceAccount Key Pair

Chinese version: `README.zh-CN.md`

This recipe generates a staged Kubernetes ServiceAccount signing key pair. It writes `sa-new-<renewal_id>.key` and `sa-new-<renewal_id>.pub` on one source control-plane host, verifies the key pair, and distributes the files to the remaining target hosts.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on control-plane hosts with privilege escalation.
2. Uses the first host in the play as the generation source by default.
3. Verifies the active `sa.key` and `sa.pub` pair.
4. Generates a new ServiceAccount signing private key.
5. Derives the matching public key.
6. Distributes the staged key pair to every target host with restrictive private-key permissions.
7. Verifies the staged key pair on every target host.

## Requirements

- Inventory group named `masters`, unless `target_hosts` is overridden
- Existing active ServiceAccount files under `/etc/kubernetes/pki/sa.key` and `/etc/kubernetes/pki/sa.pub`
- `openssl` and `diff` available on the target hosts
- SSH access with privilege escalation

## Optional Variables

- `target_hosts`: target host group, defaults to `masters`
- `service_account_source_host`: generation source host, defaults to the first host in the play
- `pki_dir`: Kubernetes PKI directory, defaults to `'/etc/kubernetes/pki'`
- `renewal_id`: date-hour or custom ID for staged file names, defaults to `YYYYMMDDHH`
- `service_account_key_bits`: ServiceAccount key size, defaults to `4096`

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/renew-service-account-keys/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-service-account-keys/playbook.yml \
  -e renewal_id=${RENEWAL_ID}
```

## Important Warnings

- This recipe creates ServiceAccount signing private key material. Protect target hosts and backups accordingly.
- The generated files are staged only; this recipe does not change static pod manifests or active Kubernetes identity files.
- Test the complete rotation and rollback procedure on a non-production or fully recoverable cluster before relying on it.
