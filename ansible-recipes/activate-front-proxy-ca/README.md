# Activating a Staged front-proxy CA

Chinese version: `README.zh-CN.md`

This recipe promotes staged Kubernetes front-proxy CA files to the active front-proxy CA filenames on each master node and converges kube-apiserver requestheader trust back to the active CA. By default it assumes a kubeadm-managed control plane where PKI files live under `/etc/kubernetes/pki`.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on hosts in the `masters` inventory group with privilege escalation, one host at a time.
2. Verifies that the staged CA files, renewed front-proxy client files, and kube-apiserver manifest exist.
3. Verifies that kube-apiserver already uses the staged front-proxy client certificate paths before removing the trust bundle, unless `require_staged_front_proxy_client_certs=false`.
4. Backs up the kube-apiserver static pod manifest outside the manifest directory.
5. Moves the active `front-proxy-ca.crt` and `front-proxy-ca.key` files to timestamped backup filenames.
6. Moves `front-proxy-ca-new-<renewal_id>.crt` and `front-proxy-ca-new-<renewal_id>.key` into the active front-proxy CA filenames.
7. Configures `--requestheader-client-ca-file` to point at the active front-proxy CA certificate.
8. Prints the certificate count, subject, issuer, validity dates, and SHA256 fingerprint for the active front-proxy CA certificate.

## Requirements

- A kubeadm-managed Kubernetes control plane, or equivalent PKI layout
- Inventory group named `masters`
- Existing active front-proxy CA certificate and key under `/etc/kubernetes/pki`
- Staged replacement front-proxy CA certificate and key under `/etc/kubernetes/pki`
- Renewed front-proxy client certificate and key under `/etc/kubernetes/pki`
- kubeadm-style kube-apiserver static pod manifest under `/etc/kubernetes/manifests`
- `mv`, `grep`, `awk`, and `openssl` available on each target host
- SSH access with privilege escalation, because the PKI files are normally root-owned

No extra variables are required when the kubeadm defaults and staged CA filenames match your environment.

## Optional Variables

- `target_hosts`: target host group, defaults to `masters`
- `front_proxy_ca_rollout_serial`: number of hosts to process at a time, defaults to `1`
- `manifest_dir`: static pod manifest directory, defaults to `'/etc/kubernetes/manifests'`
- `pki_dir`: Kubernetes PKI directory, defaults to `'/etc/kubernetes/pki'`
- `front_proxy_ca_active_cert`: active CA certificate filename, defaults to `'front-proxy-ca.crt'`
- `front_proxy_ca_active_key`: active CA private key filename, defaults to `'front-proxy-ca.key'`
- `renewal_id`: date or date-like ID for staged files, defaults to `YYYYMMDD`
- `front_proxy_ca_staged_cert`: staged CA certificate filename, defaults to `'front-proxy-ca-new-<renewal_id>.crt'`
- `front_proxy_ca_staged_key`: staged CA private key filename, defaults to `'front-proxy-ca-new-<renewal_id>.key'`
- `front_proxy_ca_backup_cert`: backup CA certificate filename, defaults to a timestamped `front-proxy-ca-backup-*.crt`
- `front_proxy_ca_backup_key`: backup CA private key filename, defaults to a timestamped `front-proxy-ca-backup-*.key`
- `front_proxy_ca_active_cert_path`: active CA certificate path used in kube-apiserver, defaults to `pki_dir + '/' + front_proxy_ca_active_cert`
- `front_proxy_client_cert_path`: expected active front-proxy client certificate, defaults to `pki_dir + '/front-proxy-client-new-<renewal_id>.crt'`
- `front_proxy_client_key_path`: expected active front-proxy client key, defaults to `pki_dir + '/front-proxy-client-new-<renewal_id>.key'`
- `kube_apiserver_manifest`: kube-apiserver manifest path, defaults to `manifest_dir + '/kube-apiserver.yaml'`
- `require_staged_front_proxy_client_certs`: require kube-apiserver to use the staged client certificate before CA activation, defaults to `true`
- `manifest_backup_dir`: directory for manifest backups, defaults to `'/etc/kubernetes/manifest-backups'`
- `manifest_backup_suffix`: backup suffix, defaults to the current Ansible timestamp plus `.bak`
- `restart_static_pods`: whether to touch the updated manifest after verification, defaults to `false`

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/activate-front-proxy-ca/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-front-proxy-ca/playbook.yml
```

To use a custom PKI directory:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-front-proxy-ca/playbook.yml \
  -e pki_dir=/etc/kubernetes/pki
```

To activate a second staged client certificate set:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-front-proxy-ca/playbook.yml \
  -e front_proxy_client_cert_path=/etc/kubernetes/pki/front-proxy-client-next.crt \
  -e front_proxy_client_key_path=/etc/kubernetes/pki/front-proxy-client-next.key
```

To run with a specific SSH key:

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/activate-front-proxy-ca/playbook.yml
```

## Important Warnings

- This recipe moves certificate authority private key material. Protect target hosts, logs, and backups accordingly.
- This recipe changes which front-proxy CA files are active and updates the kube-apiserver static pod manifest. Run it only as part of a tested certificate rotation procedure.
- Backups are written outside the kubelet static pod manifest directory so kubelet does not treat backup files as extra pods.
- This recipe does not restart kubelet. It only touches the kube-apiserver static pod manifest when `restart_static_pods=true`.
- This recipe does not create staged CA files. Generate and distribute them before running this playbook.
- Run `configure-front-proxy-client-certs` and verify aggregation API behavior before running this recipe. Otherwise the playbook fails by default rather than removing the old CA while kube-apiserver still points at old client certificates.
- Back up Kubernetes PKI files before running this recipe.
