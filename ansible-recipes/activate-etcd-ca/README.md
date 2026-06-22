# Activating a Staged etcd CA

Chinese version: `README.zh-CN.md`

This recipe promotes staged etcd CA files to the active CA filenames on each etcd member and updates the kube-apiserver and etcd static pod manifests to use the active etcd CA certificate. By default it assumes a kubeadm-managed control plane where etcd CA files live under `/etc/kubernetes/pki/etcd`.

By default, it configures kube-apiserver with:

```text
--etcd-cafile=/etc/kubernetes/pki/etcd/ca.crt
```

It configures etcd with:

```text
--trusted-ca-file=/etc/kubernetes/pki/etcd/ca.crt
--peer-trusted-ca-file=/etc/kubernetes/pki/etcd/ca.crt
```

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on the target hosts with privilege escalation, one host at a time by default.
2. Validates that the configured active, staged, and backup filenames are non-empty and distinct.
3. Checks that the active CA certificate and key, plus the staged CA certificate and key, exist under the configured etcd PKI directory.
4. Checks that the kube-apiserver and etcd static pod manifests exist and have usable insertion points for the managed CA arguments.
5. Backs up the kube-apiserver and etcd static pod manifests.
6. Moves the active CA certificate and key to backup filenames.
7. Moves the staged CA certificate and key to the active filenames.
8. Configures `--etcd-cafile`, `--trusted-ca-file`, and `--peer-trusted-ca-file` to point at the active etcd CA certificate.
9. Verifies that the manifests already use the staged etcd leaf certificate paths before removing the trust bundle, unless `require_staged_etcd_leaf_certs=false`.
10. Verifies the managed static pod manifest arguments.
11. Prints the certificate count, subject, issuer, validity dates, and SHA256 fingerprint for the active CA certificate.

By default, this recipe does not touch manifest timestamps after editing. Kubelet normally detects manifest content changes and restarts static pods. Set `restart_static_pods=true` if you want the playbook to touch the manifests after verification.

## Requirements

- A kubeadm-managed Kubernetes control plane with local etcd CA files, or equivalent etcd PKI layout
- kubeadm-style kube-apiserver and etcd static pod manifests under `/etc/kubernetes/manifests`
- Inventory group named `etcd_members`, unless `target_hosts` is overridden
- Existing active etcd CA certificate and key under the configured PKI directory
- Staged replacement etcd CA certificate and key under the configured PKI directory
- `awk`, `mv`, `grep`, and `openssl` available on each target host
- SSH access with privilege escalation, because the PKI files and static pod manifests are normally root-owned

No extra variables are required when the kubeadm defaults and staged CA filenames match your environment.

## Optional Variables

- `target_hosts`: target host group, defaults to `etcd_members`
- `etcd_ca_rollout_serial`: number of hosts to process at a time, defaults to `1`
- `manifest_dir`: static pod manifest directory, defaults to `'/etc/kubernetes/manifests'`
- `pki_dir`: Kubernetes PKI directory, defaults to `'/etc/kubernetes/pki'`
- `etcd_pki_dir`: etcd PKI directory, defaults to `'/etc/kubernetes/pki/etcd'`
- `etcd_ca_active_cert`: active CA certificate filename, defaults to `'ca.crt'`
- `etcd_ca_active_key`: active CA private key filename, defaults to `'ca.key'`
- `renewal_id`: date or date-like ID for staged files, defaults to `YYYYMMDD`
- `etcd_ca_staged_cert`: staged CA certificate filename, defaults to `'ca-new-<renewal_id>.crt'`
- `etcd_ca_staged_key`: staged CA private key filename, defaults to `'ca-new-<renewal_id>.key'`
- `etcd_ca_backup_cert`: backup CA certificate filename, defaults to a timestamped `ca-backup-*.crt`
- `etcd_ca_backup_key`: backup CA private key filename, defaults to a timestamped `ca-backup-*.key`
- `etcd_ca_verify_cert`: certificate filename to verify after activation, defaults to the active CA certificate filename
- `etcd_ca_active_cert_path`: active CA certificate path used in manifests, defaults to `etcd_pki_dir + '/' + etcd_ca_active_cert`
- `kube_apiserver_manifest`: kube-apiserver manifest path, defaults to `manifest_dir + '/kube-apiserver.yaml'`
- `etcd_manifest`: etcd manifest path, defaults to `manifest_dir + '/etcd.yaml'`
- `apiserver_etcd_certfile`: expected active kube-apiserver etcd client certificate, defaults to `pki_dir + '/apiserver-etcd-client-new-<renewal_id>.crt'`
- `apiserver_etcd_keyfile`: expected active kube-apiserver etcd client key, defaults to `pki_dir + '/apiserver-etcd-client-new-<renewal_id>.key'`
- `etcd_certfile`: expected active etcd server certificate, defaults to `etcd_pki_dir + '/server-new-<renewal_id>.crt'`
- `etcd_keyfile`: expected active etcd server key, defaults to `etcd_pki_dir + '/server-new-<renewal_id>.key'`
- `etcd_peer_certfile`: expected active etcd peer certificate, defaults to `etcd_pki_dir + '/peer-new-<renewal_id>.crt'`
- `etcd_peer_keyfile`: expected active etcd peer key, defaults to `etcd_pki_dir + '/peer-new-<renewal_id>.key'`
- `require_staged_etcd_leaf_certs`: require manifests to use the staged leaf certificates before CA activation, defaults to `true`
- `manifest_backup_dir`: directory for manifest backups, defaults to `'/etc/kubernetes/manifest-backups'`
- `manifest_backup_suffix`: backup suffix, defaults to the current Ansible timestamp plus `.bak`
- `restart_static_pods`: whether to touch updated manifests after verification, defaults to `false`
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

To explicitly touch the manifests after verification:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-etcd-ca/playbook.yml \
  -e restart_static_pods=true
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
- This recipe changes which etcd CA files are active and updates control-plane static pod manifests. Run it only as part of a tested certificate rotation procedure.
- Backups are written outside the kubelet static pod manifest directory so kubelet does not treat backup files as extra pods.
- This recipe does not restart kubelet. It only touches static pod manifests when `restart_static_pods=true`.
- This recipe does not create the staged CA files. Generate and distribute them before running this playbook.
- Run `activate-etcd-certs` and verify etcd health before running this recipe. Otherwise the playbook fails by default rather than removing the old CA while manifests still point at old leaf certificates.
- Choose backup filenames carefully. The underlying move command may replace existing backup files.
- Run it only after backing up etcd data and Kubernetes PKI files.
- Test the full activation and rollback procedure on a non-production or fully recoverable cluster before relying on it.
