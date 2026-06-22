# Generating a Staged Kubernetes Root CA and ServiceAccount Key Pair

Chinese version: `README.zh-CN.md`

This recipe generates staged Kubernetes root CA replacement material and a staged ServiceAccount signing key pair. It writes `ca-new-<renewal_id>.crt`, `ca-new-<renewal_id>.key`, `ca-bundle-<renewal_id>.crt`, `sa-new-<renewal_id>.key`, and `sa-new-<renewal_id>.pub` on one source control-plane host, then distributes the generated files to the remaining target hosts.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on control-plane hosts with privilege escalation.
2. Uses the first host in the play as the generation source by default.
3. Verifies that every target starts with the same active `ca.crt`.
4. Generates a new root CA private key and self-signed certificate.
5. Builds `ca-bundle-<renewal_id>.crt` from active `ca.crt` plus `ca-new-<renewal_id>.crt`.
6. Generates `sa-new-<renewal_id>.key` and derives `sa-new-<renewal_id>.pub`.
7. Distributes generated files to every target host with restrictive key permissions.
8. Prints the bundle certificate count and new root CA certificate details.

## Requirements

- Inventory group named `masters`, unless `target_hosts` is overridden
- Existing active root CA certificate under `/etc/kubernetes/pki/ca.crt`
- `openssl`, `grep`, and `cat` available on the target hosts
- SSH access with privilege escalation

## Optional Variables

- `target_hosts`: target host group, defaults to `masters`
- `k8s_ca_source_host`: generation source host, defaults to the first host in the play
- `pki_dir`: Kubernetes PKI directory, defaults to `'/etc/kubernetes/pki'`
- `renewal_id`: date-hour or custom ID for generated file names, defaults to `YYYYMMDDHH`
- `k8s_ca_valid_days`: new root CA validity period in days, defaults to `3650`
- `k8s_ca_subject`: new root CA subject, defaults to `'/CN=kubernetes-ca'`
- `service_account_key_bits`: ServiceAccount key size, defaults to `4096`

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/renew-k8s-ca/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-k8s-ca/playbook.yml
```

## Important Warnings

- This recipe creates root CA private key material and ServiceAccount signing private key material. Protect target hosts and backups accordingly.
- The generated files are staged only; this recipe does not change static pod manifests or active Kubernetes identity files.
- Test the complete rotation and rollback procedure on a non-production or fully recoverable cluster before relying on it.
