# Configuring the front-proxy CA Bundle

Chinese version: `README.zh-CN.md`

This recipe updates the kube-apiserver static pod manifest so the Kubernetes aggregation requestheader client CA points to the front-proxy CA bundle.

By default, it configures kube-apiserver with:

```text
--requestheader-client-ca-file=/etc/kubernetes/pki/front-proxy-ca-bundle-<renewal_id>.crt
```

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on control-plane nodes with privilege escalation, one host at a time by default.
2. Verifies that the front-proxy CA bundle and kube-apiserver manifest exist.
3. Backs up the kube-apiserver static pod manifest.
4. Configures `--requestheader-client-ca-file` to point at the configured front-proxy CA bundle.
5. Verifies that the managed argument appears exactly once with the expected value.

By default, this recipe does not touch the manifest timestamp after editing. Kubelet normally detects manifest content changes and restarts the static pod. Set `restart_static_pods=true` if you want the playbook to touch the manifest after verification.

## Requirements

- kubeadm-style kube-apiserver static pod manifest under `/etc/kubernetes/manifests`
- Inventory group named `masters`, unless `target_hosts` is overridden
- Existing front-proxy CA bundle at `/etc/kubernetes/pki/front-proxy-ca-bundle-<renewal_id>.crt`
- `awk` available on each target host
- SSH access with privilege escalation, because Kubernetes manifests and PKI files are normally root-owned

## Optional Variables

- `target_hosts`: target host group, defaults to `masters`
- `front_proxy_ca_bundle_rollout_serial`: number of hosts to process at a time, defaults to `1`
- `manifest_dir`: static pod manifest directory, defaults to `'/etc/kubernetes/manifests'`
- `pki_dir`: Kubernetes PKI directory, defaults to `'/etc/kubernetes/pki'`
- `renewal_id`: date-hour or custom ID for staged files, defaults to `YYYYMMDDHH`
- `front_proxy_ca_bundle_path`: front-proxy CA bundle path, defaults to `pki_dir + '/front-proxy-ca-bundle-<renewal_id>.crt'`
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
ansible-playbook --syntax-check ansible-recipes/configure-front-proxy-ca-bundle/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-front-proxy-ca-bundle/playbook.yml
```

To use a custom CA bundle path:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-front-proxy-ca-bundle/playbook.yml \
  -e front_proxy_ca_bundle_path=/etc/kubernetes/pki/custom-front-proxy-ca-bundle.crt
```

To explicitly touch the manifest after verification:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-front-proxy-ca-bundle/playbook.yml \
  -e restart_static_pods=true
```

## Important Warnings

- This recipe changes the kube-apiserver static pod manifest. Test it on a non-production or fully recoverable cluster before relying on it.
- Back up Kubernetes PKI files before changing front-proxy trust settings.
- Backups are written outside the kubelet static pod manifest directory so kubelet does not treat backup files as extra pods.
- Ensure the CA bundle contains every front-proxy CA required during your rotation window.
- Roll out one control-plane node at a time unless you have validated a broader rollout strategy.
