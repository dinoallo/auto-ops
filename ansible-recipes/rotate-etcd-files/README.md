# Renewing etcd Leaf Certificates with a Staged CA

Chinese version: `README.zh-CN.md`

This recipe uses a staged new etcd CA to renew kubeadm-managed etcd leaf certificates. It writes the renewed files with `-new` filenames next to the existing certificates, so the current active certificates are not replaced by this playbook.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on hosts in the `etcd_members` inventory group with privilege escalation, one host at a time.
2. Recreates a temporary kubeadm certificate staging directory.
3. Copies the current etcd leaf certificates and private keys into the staging directory as kubeadm renewal templates.
4. Copies the staged new etcd CA from `ca-new.crt` and `ca-new.key` into the staging directory as kubeadm's signing CA.
5. Runs `kubeadm certs renew` for the etcd-related leaf certificate targets.
6. Installs the renewed certificates and keys with `-new` filenames under the Kubernetes PKI directories.
7. Prints the subject, issuer, validity dates, and Subject Alternative Name details for the renewed certificates.

## Requirements

- A kubeadm-managed Kubernetes control plane with local etcd certificates
- Inventory group named `etcd_members`
- `kubeadm`, `openssl`, `cp`, and `install` available on each target host
- Existing etcd leaf certificate and key files under the configured PKI directories
- A staged new etcd CA at `/etc/kubernetes/pki/etcd/ca-new.crt` and `/etc/kubernetes/pki/etcd/ca-new.key` on each target host
- SSH access with privilege escalation, because the source and destination PKI paths are normally root-owned

No extra variables are required when the kubeadm defaults and staged CA filenames match your environment.

## Optional Variables

- `stage_dir`: temporary kubeadm renewal directory, defaults to `'/tmp/kubeadm-etcd-leaf-renew'`
- `pki_dir`: Kubernetes PKI root directory, defaults to `'/etc/kubernetes/pki'`
- `etcd_pki_dir`: etcd PKI directory, defaults to `'/etc/kubernetes/pki/etcd'`
- `kubeadm_renew_targets`: kubeadm certificate targets to renew, defaults to `apiserver-etcd-client`, `etcd-healthcheck-client`, `etcd-peer`, and `etcd-server`

Example inventory layout:

```ini
[etcd_members]
cp1
cp2
cp3
```

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/rotate-etcd-files/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/rotate-etcd-files/playbook.yml
```

To use custom PKI paths:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/rotate-etcd-files/playbook.yml \
  -e pki_dir=/etc/kubernetes/pki \
  -e etcd_pki_dir=/etc/kubernetes/pki/etcd
```

To run with a specific SSH key:

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/rotate-etcd-files/playbook.yml
```

## Important Warnings

- This recipe handles private keys and certificate authority material. Protect the target hosts, logs, and generated files accordingly.
- This recipe does not create the new etcd CA. The `ca-new.crt` and `ca-new.key` files must already exist on each target host.
- This recipe does not replace active certificate files, restart etcd, or restart kube-apiserver. It only prepares `*-new.crt` and `*-new.key` files for a separate controlled cutover.
- Run it only after backing up etcd data and the Kubernetes PKI files.
- Verify the printed issuer, validity dates, and SANs before using the renewed certificates.
- Test the full rotation and rollback procedure on a non-production or fully recoverable cluster before relying on it.
