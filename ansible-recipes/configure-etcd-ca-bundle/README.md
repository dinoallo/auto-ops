# Configuring the etcd CA Bundle

Chinese version: `README.zh-CN.md`

This recipe updates kubeadm-style static pod manifests so kube-apiserver and etcd trust the staged etcd CA bundle at `/etc/kubernetes/pki/etcd/ca-bundle-<renewal_id>.crt`.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on control-plane nodes with privilege escalation, one host at a time by default.
2. Verifies that the etcd CA bundle and the kube-apiserver and etcd manifests exist.
3. Backs up both static pod manifests.
4. Configures kube-apiserver with `--etcd-cafile=/etc/kubernetes/pki/etcd/ca-bundle-<renewal_id>.crt`.
5. Configures etcd with `--trusted-ca-file=/etc/kubernetes/pki/etcd/ca-bundle-<renewal_id>.crt`.
6. Configures etcd with `--peer-trusted-ca-file=/etc/kubernetes/pki/etcd/ca-bundle-<renewal_id>.crt`.
7. Verifies that each managed argument appears exactly once with the expected value.

By default, this recipe does not touch the manifest timestamps after editing. Kubelet normally detects manifest content changes and restarts the static pods. Set `restart_static_pods=true` if you want the playbook to touch the manifests after verification.

## Requirements

- kubeadm-style static pod manifests under `/etc/kubernetes/manifests`
- Inventory group named `masters`, unless `target_hosts` is overridden
- Existing etcd CA bundle at `/etc/kubernetes/pki/etcd/ca-bundle-<renewal_id>.crt`
- `awk` available on each target host
- SSH access with privilege escalation, because Kubernetes manifests and PKI files are normally root-owned

## Optional Variables

- `target_hosts`: target host group, defaults to `masters`
- `etcd_ca_bundle_rollout_serial`: number of hosts to process at a time, defaults to `1`
- `manifest_dir`: static pod manifest directory, defaults to `'/etc/kubernetes/manifests'`
- `renewal_id`: date-hour or custom ID for staged files, defaults to `YYYYMMDDHH`
- `etcd_ca_bundle_path`: etcd CA bundle path, defaults to `'/etc/kubernetes/pki/etcd/ca-bundle-<renewal_id>.crt'`
- `kube_apiserver_manifest`: kube-apiserver manifest path, defaults to `manifest_dir + '/kube-apiserver.yaml'`
- `etcd_manifest`: etcd manifest path, defaults to `manifest_dir + '/etcd.yaml'`
- `manifest_backup_dir`: directory for manifest backups, defaults to `'/etc/kubernetes/manifest-backups'`
- `manifest_backup_suffix`: backup suffix, defaults to the current Ansible timestamp plus `.bak`
- `restart_static_pods`: whether to touch updated manifests after verification, defaults to `false`

Example inventory layout:

```ini
[masters]
cp1
cp2
cp3
```

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/configure-etcd-ca-bundle/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-etcd-ca-bundle/playbook.yml
```

To use a custom CA bundle path:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-etcd-ca-bundle/playbook.yml \
  -e etcd_ca_bundle_path=/etc/kubernetes/pki/etcd/custom-ca-bundle.crt
```

To explicitly touch the manifests after verification:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-etcd-ca-bundle/playbook.yml \
  -e restart_static_pods=true
```

## Important Warnings

- This recipe changes control-plane static pod manifests. Test it on a non-production or fully recoverable cluster before relying on it.
- Back up etcd data and Kubernetes PKI files before changing etcd trust settings.
- Backups are written outside the kubelet static pod manifest directory so kubelet does not treat backup files as extra pods.
- Ensure the CA bundle contains every CA required during your etcd CA rotation window.
- Roll out one control-plane node at a time unless you have validated a broader rollout strategy.
