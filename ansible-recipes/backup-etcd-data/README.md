# Backing Up etcd Data

Chinese version: `README.zh-CN.md`

This recipe creates a point-in-time etcd snapshot with `etcdctl snapshot save`. By default it assumes a kubeadm-managed control plane where etcd listens on `https://127.0.0.1:2379` and the TLS files live under `/etc/kubernetes/pki/etcd`.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Ensures the play targets exactly one etcd member.
2. Verifies that `etcdctl` and the required TLS files are present on the target host.
3. Creates the remote backup directory when it does not already exist.
4. Saves a timestamped snapshot file with `ETCDCTL_API=3`.
5. Verifies that the snapshot file exists and is not empty.
6. Optionally fetches a copy of the snapshot back to the Ansible control node.

## Requirements

- Exactly one target host per run
- `etcdctl` available on the target host
- Network reachability from the target host to the configured etcd endpoint
- TLS CA, client certificate, and private key that can authenticate to etcd
- SSH access with privilege escalation when the certificate paths or backup directory require it

No additional variables are required when the kubeadm defaults match your environment.

## Optional Variables

- `target_hosts`: target host group, defaults to `all`
- `etcd_backup_dir`: remote directory that stores the snapshot, defaults to `'/var/backups/etcd'`
- `etcd_snapshot_basename`: prefix for the snapshot filename, defaults to `'etcd-snapshot'`
- `etcd_endpoint`: single etcd endpoint used for the snapshot, defaults to `'https://127.0.0.1:2379'`
- `etcdctl_command`: path or command name for `etcdctl`, defaults to `'etcdctl'`
- `etcd_cacert`: CA certificate path for etcd TLS, defaults to `'/etc/kubernetes/pki/etcd/ca.crt'`
- `etcd_cert`: client certificate path for etcd TLS, defaults to `'/etc/kubernetes/pki/etcd/healthcheck-client.crt'`
- `etcd_key`: client private key path for etcd TLS, defaults to `'/etc/kubernetes/pki/etcd/healthcheck-client.key'`
- `fetch_snapshot_to_controller`: whether to fetch the snapshot back to the Ansible control node, defaults to `false`
- `controller_snapshot_dir`: directory on the Ansible control node used when fetching snapshots, defaults to `'/tmp/etcd-snapshots'`

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/backup-etcd-data/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/backup-etcd-data/playbook.yml \
  -e target_hosts=cp1
```

To fetch the snapshot back to the Ansible control node:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/backup-etcd-data/playbook.yml \
  -e target_hosts=cp1 \
  -e fetch_snapshot_to_controller=true \
  -e controller_snapshot_dir=/tmp/etcd-snapshots
```

To use a non-kubeadm endpoint or different TLS paths:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/backup-etcd-data/playbook.yml \
  -e target_hosts=etcd1 \
  -e etcd_endpoint=https://10.0.0.11:2379 \
  -e etcd_cacert=/etc/etcd/pki/ca.crt \
  -e etcd_cert=/etc/etcd/pki/client.crt \
  -e etcd_key=/etc/etcd/pki/client.key
```

To run with a specific SSH key:

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/backup-etcd-data/playbook.yml \
  -e target_hosts=cp1
```

## Important Warnings

- The snapshot file contains sensitive cluster data. Store it securely and encrypt it when appropriate.
- This recipe intentionally snapshots one etcd member per run. One good snapshot is usually sufficient for the cluster.
- Keeping the snapshot only on the source host is not a durable backup strategy. Fetch or move it to separate storage.
- For kubeadm-managed clusters, consider backing up the etcd PKI material and static pod manifests alongside the snapshot so disaster recovery has the files it needs.
