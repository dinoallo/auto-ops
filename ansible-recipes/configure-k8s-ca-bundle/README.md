# Configuring Kubernetes CA Bundle Arguments

Chinese version: `README.zh-CN.md`

This recipe updates kubeadm-style kube-apiserver and kube-controller-manager static pod manifests to use the Kubernetes root CA bundle while keeping both current and new ServiceAccount public keys trusted by kube-apiserver.

By default, it configures kube-apiserver with:

```text
--client-ca-file=/etc/kubernetes/pki/ca-bundle.crt
--service-account-key-file=/etc/kubernetes/pki/sa.pub
--service-account-key-file=/etc/kubernetes/pki/sa-new.pub
--service-account-signing-key-file=/etc/kubernetes/pki/sa.key
```

It configures kube-controller-manager with:

```text
--root-ca-file=/etc/kubernetes/pki/ca-bundle.crt
--cluster-signing-cert-file=/etc/kubernetes/pki/ca.crt
--cluster-signing-key-file=/etc/kubernetes/pki/ca.key
--service-account-private-key-file=/etc/kubernetes/pki/sa.key
```

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on control-plane nodes with privilege escalation, one host at a time by default.
2. Verifies that the required Kubernetes PKI files and static pod manifests exist.
3. Backs up the kube-apiserver and kube-controller-manager static pod manifests under `/etc/kubernetes/manifest-backups` by default.
4. Rewrites the managed kube-apiserver command arguments, preserving two `--service-account-key-file` entries.
5. Rewrites the managed kube-controller-manager command arguments.
6. Verifies that every managed argument appears exactly as expected.
7. Optionally waits for kube-apiserver and kube-controller-manager to become Ready after touching manifests.

By default, this recipe does not touch manifest timestamps after editing. Kubelet normally detects manifest content changes and restarts static pods. Set `restart_static_pods=true` if you want the playbook to touch the manifests after verification.

## Requirements

- kubeadm-style static pod manifests under `/etc/kubernetes/manifests`
- Inventory group named `masters`, unless `target_hosts` is overridden
- Existing PKI files under `/etc/kubernetes/pki`: `ca-bundle.crt`, `ca.crt`, `ca.key`, `sa.pub`, `sa-new.pub`, and `sa.key`
- Python 3 available on each target host
- SSH access with privilege escalation, because Kubernetes manifests and PKI files are normally root-owned

## Optional Variables

- `target_hosts`: target host group, defaults to `masters`
- `k8s_ca_bundle_rollout_serial`: number of hosts to process at a time, defaults to `1`
- `manifest_dir`: static pod manifest directory, defaults to `'/etc/kubernetes/manifests'`
- `pki_dir`: Kubernetes PKI directory, defaults to `'/etc/kubernetes/pki'`
- `ca_bundle_path`: root CA bundle path, defaults to `pki_dir + '/ca-bundle.crt'`
- `ca_cert_path`: root CA certificate path, defaults to `pki_dir + '/ca.crt'`
- `ca_key_path`: root CA private key path, defaults to `pki_dir + '/ca.key'`
- `service_account_public_key_path`: current ServiceAccount public key path, defaults to `pki_dir + '/sa.pub'`
- `service_account_new_public_key_path`: new ServiceAccount public key path, defaults to `pki_dir + '/sa-new.pub'`
- `service_account_signing_key_path`: ServiceAccount signing key path, defaults to `pki_dir + '/sa.key'`
- `service_account_private_key_path`: controller-manager ServiceAccount private key path, defaults to `service_account_signing_key_path`
- `kube_apiserver_manifest`: kube-apiserver manifest path, defaults to `manifest_dir + '/kube-apiserver.yaml'`
- `kube_controller_manager_manifest`: kube-controller-manager manifest path, defaults to `manifest_dir + '/kube-controller-manager.yaml'`
- `manifest_backup_dir`: directory for manifest backups, defaults to `'/etc/kubernetes/manifest-backups'`
- `manifest_backup_suffix`: backup suffix, defaults to the current Ansible timestamp plus `.bak`
- `restart_static_pods`: whether to touch updated manifests after verification, defaults to `false`
- `wait_static_pods`: whether to wait for restarted static pods, defaults to `restart_static_pods`
- `kubeconfig`: kubeconfig used for readiness checks, defaults to `'/etc/kubernetes/admin.conf'`
- `python_interpreter`: Python interpreter used on target hosts, defaults to `'/usr/bin/python3'`

Example inventory layout:

```ini
[masters]
cp1
cp2
cp3
```

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/configure-k8s-ca-bundle/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-k8s-ca-bundle/playbook.yml
```

To explicitly touch the manifests after verification:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-k8s-ca-bundle/playbook.yml \
  -e restart_static_pods=true
```

After every API server trusts `ca-bundle.crt` and both ServiceAccount public keys, use the same playbook to switch future certificate and token signing to the staged new material while keeping trust compatible:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-k8s-ca-bundle/playbook.yml \
  -e ca_cert_path=/etc/kubernetes/pki/ca-new.crt \
  -e ca_key_path=/etc/kubernetes/pki/ca-new.key \
  -e service_account_signing_key_path=/etc/kubernetes/pki/sa-new.key \
  -e service_account_private_key_path=/etc/kubernetes/pki/sa-new.key \
  -e restart_static_pods=true
```

## Important Warnings

- This recipe changes control-plane static pod manifests. Test it on a non-production or fully recoverable cluster before relying on it.
- Back up Kubernetes PKI files before changing CA and ServiceAccount trust settings.
- Ensure the CA bundle contains every root CA required during your rotation window.
- Ensure `sa-new.pub` exists before running this playbook.
- Roll out one control-plane node at a time unless you have validated a broader rollout strategy.
