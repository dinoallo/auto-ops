# Activating a Staged etcd CA

Chinese version: `README.zh-CN.md`

This recipe promotes staged etcd CA files to the active CA filenames on each etcd member. By default it assumes a kubeadm-managed control plane where etcd CA files live under `/etc/kubernetes/pki/etcd`.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on the target hosts with privilege escalation, one host at a time by default.
2. Validates that the configured active, staged, and backup filenames are non-empty and distinct.
3. Checks that the active CA certificate and key, plus the staged CA certificate and key, exist under the configured etcd PKI directory.
4. Moves the active CA certificate and key to backup filenames.
5. Moves the staged CA certificate and key to the active filenames.
6. Prints the certificate count, subject, issuer, validity dates, and SHA256 fingerprint for the active CA certificate.

## Requirements

- A kubeadm-managed Kubernetes control plane with local etcd CA files, or equivalent etcd PKI layout
- Inventory group named `etcd_members`, unless `target_hosts` is overridden
- Existing active etcd CA certificate and key under the configured PKI directory
- Staged replacement etcd CA certificate and key under the configured PKI directory
- `mv`, `grep`, and `openssl` available on each target host
- SSH access with privilege escalation, because the PKI files are normally root-owned

No extra variables are required when the kubeadm defaults and staged CA filenames match your environment.

## Optional Variables

- `target_hosts`: target host group, defaults to `etcd_members`
- `etcd_ca_rollout_serial`: number of hosts to process at a time, defaults to `1`
- `etcd_pki_dir`: etcd PKI directory, defaults to `'/etc/kubernetes/pki/etcd'`
- `etcd_ca_active_cert`: active CA certificate filename, defaults to `'ca.crt'`
- `etcd_ca_active_key`: active CA private key filename, defaults to `'ca.key'`
- `etcd_ca_staged_cert`: staged CA certificate filename, defaults to `'ca-new.crt'`
- `etcd_ca_staged_key`: staged CA private key filename, defaults to `'ca-new.key'`
- `etcd_ca_backup_cert`: backup CA certificate filename, defaults to `'ca-old.crt'`
- `etcd_ca_backup_key`: backup CA private key filename, defaults to `'ca-old.key'`
- `etcd_ca_verify_cert`: certificate filename to verify after activation, defaults to the active CA certificate filename
- `etcd_ca_certificate_marker`: marker counted during certificate verification, defaults to `'BEGIN CERTIFICATE'`
- `file_move_command`: path or command name for moving files, defaults to `'mv'`
- `grep_command`: path or command name for `grep`, defaults to `'grep'`
- `openssl_command`: path or command name for `openssl`, defaults to `'openssl'`

Example inventory layout:

```ini
[etcd_members]
cp1
cp2
cp3
```

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/activate-etcd-ca/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-etcd-ca/playbook.yml
```

To use custom staged and backup filenames:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-etcd-ca/playbook.yml \
  -e etcd_ca_staged_cert=etcd-ca-2026.crt \
  -e etcd_ca_staged_key=etcd-ca-2026.key \
  -e etcd_ca_backup_cert=etcd-ca-previous.crt \
  -e etcd_ca_backup_key=etcd-ca-previous.key
```

To use a custom PKI directory:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-etcd-ca/playbook.yml \
  -e etcd_pki_dir=/etc/etcd/pki
```

To run with a specific SSH key:

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/activate-etcd-ca/playbook.yml
```

## Important Warnings

- This recipe moves certificate authority private key material. Protect target hosts, logs, and backups accordingly.
- This recipe changes which etcd CA files are active. Run it only as part of a tested certificate rotation procedure.
- This recipe does not restart etcd, kube-apiserver, or kubelet. Plan any required service restarts separately.
- This recipe does not create the staged CA files. Generate and distribute them before running this playbook.
- Choose backup filenames carefully. The underlying move command may replace existing backup files.
- Run it only after backing up etcd data and Kubernetes PKI files.
- Test the full activation and rollback procedure on a non-production or fully recoverable cluster before relying on it.
