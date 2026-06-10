# Backing Up Kubernetes PKI and Control-Plane Configuration

Chinese version: `README.zh-CN.md`

This recipe creates a timestamped remote backup of kubeadm-style Kubernetes control-plane files. It archives the Kubernetes PKI directory, kubeconfig files, and static pod manifests on hosts in the `masters` inventory group.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on hosts in the `masters` inventory group with privilege escalation.
2. Creates a timestamped backup directory, defaulting to `/root/k8s-pki-rotation-<timestamp>`.
3. Archives `/etc/kubernetes/pki` into `kubernetes-pki.tgz`.
4. Archives `/etc/kubernetes/*.conf` and `/etc/kubernetes/manifests` into `kubernetes-config.tgz`.
5. Writes SHA-256 checksums for the generated archives to `SHA256SUMS`.

## Requirements

- A kubeadm-managed Kubernetes control-plane node layout
- Inventory group named `masters`
- `/etc/kubernetes/pki` present on each target master node
- `/etc/kubernetes/*.conf` and `/etc/kubernetes/manifests` present on each target master node
- `tar` and `sha256sum` available on each target host
- SSH access with privilege escalation, because the default source and backup paths are root-owned

No extra variables are required when the defaults match your environment.

## Optional Variables

- `backup_dir`: remote directory for the generated archives, defaults to `'/root/k8s-pki-rotation-{{ ansible_date_time.iso8601_basic_short }}'`

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/backup-k8s-data/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/backup-k8s-data/playbook.yml
```

To write the backup to a custom remote directory:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/backup-k8s-data/playbook.yml \
  -e backup_dir=/var/backups/kubernetes/control-plane-files
```

To run with a specific SSH key:

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/backup-k8s-data/playbook.yml
```

## Important Warnings

- The generated archives include private keys and kubeconfig files. Store them securely and encrypt them when appropriate.
- This recipe stores backups on the remote target hosts only. Copy the archives to separate durable storage for real disaster recovery.
- This recipe does not create an etcd snapshot. Use `ansible-recipes/backup-etcd-data/playbook.yml` when you also need etcd data.
- Verify that the archived files can be restored before relying on this workflow during certificate rotation or disaster recovery.
