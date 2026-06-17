# Configuring front-proxy Client Certificates

Chinese version: `README.zh-CN.md`

This recipe updates the kube-apiserver static pod manifest so the Kubernetes aggregation front-proxy client certificate and key point to the renewed front-proxy client files.

By default, it configures kube-apiserver with:

```text
--proxy-client-cert-file=/etc/kubernetes/pki/front-proxy-client-new.crt
--proxy-client-key-file=/etc/kubernetes/pki/front-proxy-client-new.key
```

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on control-plane nodes with privilege escalation, one host at a time by default.
2. Verifies that the renewed front-proxy client certificate, key, and kube-apiserver manifest exist.
3. Backs up the kube-apiserver static pod manifest.
4. Configures `--proxy-client-cert-file` and `--proxy-client-key-file` to point at the configured renewed files.
5. Verifies that each managed argument appears exactly once with the expected value.

By default, this recipe does not touch the manifest timestamp after editing. Kubelet normally detects manifest content changes and restarts the static pod. Set `restart_static_pods=true` if you want the playbook to touch the manifest after verification.

## Requirements

- kubeadm-style kube-apiserver static pod manifest under `/etc/kubernetes/manifests`
- Inventory group named `masters`, unless `target_hosts` is overridden
- Existing renewed front-proxy client certificate at `/etc/kubernetes/pki/front-proxy-client-new.crt`
- Existing renewed front-proxy client key at `/etc/kubernetes/pki/front-proxy-client-new.key`
- `awk` available on each target host
- SSH access with privilege escalation, because Kubernetes manifests and PKI files are normally root-owned

## Optional Variables

- `target_hosts`: target host group, defaults to `masters`
- `front_proxy_client_certs_rollout_serial`: number of hosts to process at a time, defaults to `1`
- `manifest_dir`: static pod manifest directory, defaults to `'/etc/kubernetes/manifests'`
- `pki_dir`: Kubernetes PKI directory, defaults to `'/etc/kubernetes/pki'`
- `front_proxy_client_cert_path`: front-proxy client certificate path, defaults to `pki_dir + '/front-proxy-client-new.crt'`
- `front_proxy_client_key_path`: front-proxy client key path, defaults to `pki_dir + '/front-proxy-client-new.key'`
- `kube_apiserver_manifest`: kube-apiserver manifest path, defaults to `manifest_dir + '/kube-apiserver.yaml'`
- `manifest_backup_dir`: directory for manifest backups, defaults to `'/etc/kubernetes/manifest-backups'`
- `manifest_backup_suffix`: backup suffix, defaults to the current Ansible timestamp plus `.bak`
- `restart_static_pods`: whether to touch the updated manifest after verification, defaults to `false`

Example inventory layout:

```ini
[masters]
cp1
cp2
cp3
```

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/configure-front-proxy-client-certs/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-front-proxy-client-certs/playbook.yml
```

To use custom certificate and key paths:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-front-proxy-client-certs/playbook.yml \
  -e front_proxy_client_cert_path=/etc/kubernetes/pki/custom-front-proxy-client.crt \
  -e front_proxy_client_key_path=/etc/kubernetes/pki/custom-front-proxy-client.key
```

To explicitly touch the manifest after verification:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-front-proxy-client-certs/playbook.yml \
  -e restart_static_pods=true
```

## Important Warnings

- This recipe changes the kube-apiserver static pod manifest. Test it on a non-production or fully recoverable cluster before relying on it.
- Back up Kubernetes PKI files before changing front-proxy client certificate settings.
- Backups are written outside the kubelet static pod manifest directory so kubelet does not treat backup files as extra pods.
- Ensure the configured certificate and key are a matching pair trusted by the active requestheader CA configuration.
- Roll out one control-plane node at a time unless you have validated a broader rollout strategy.
