# Activating a Staged Kubernetes Root CA and ServiceAccount Key Pair

Chinese version: `README.zh-CN.md`

This recipe promotes staged Kubernetes root CA files and ServiceAccount signing key files to the active filenames on each master node. By default it assumes a kubeadm-managed control plane where PKI files live under `/etc/kubernetes/pki`.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on hosts in the `masters` inventory group with privilege escalation, one host at a time.
2. Moves the active root CA certificate and key to `ca-old.crt` and `ca-old.key`.
3. Moves the active ServiceAccount public and private keys to `sa-old.pub` and `sa-old.key`.
4. Moves `ca-new.crt`, `ca-new.key`, `sa-new.pub`, and `sa-new.key` into the active filenames.
5. Prints the active root CA certificate subject, issuer, validity dates, and SHA256 fingerprint.
6. Derives the ServiceAccount public key from the active private key and compares it with the active `sa.pub`.

## Requirements

- A kubeadm-managed Kubernetes control plane, or equivalent PKI layout
- Inventory group named `masters`
- Existing active root CA files `ca.crt` and `ca.key` under the configured PKI directory
- Existing active ServiceAccount files `sa.pub` and `sa.key` under the configured PKI directory
- Staged replacement files `ca-new.crt`, `ca-new.key`, `sa-new.pub`, and `sa-new.key`
- `mv`, `openssl`, and `diff` available on each target host
- SSH access with privilege escalation, because the PKI files are normally root-owned

No extra variables are required when the kubeadm defaults and staged filenames match your environment.

## Optional Variables

- `pki_dir`: Kubernetes PKI directory, defaults to `'/etc/kubernetes/pki'`

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/activate-k8s-ca/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-k8s-ca/playbook.yml
```

To use a custom PKI directory:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-k8s-ca/playbook.yml \
  -e pki_dir=/etc/kubernetes/pki
```

To run with a specific SSH key:

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/activate-k8s-ca/playbook.yml
```

## Important Warnings

- This recipe moves root certificate authority and ServiceAccount signing private key material. Protect target hosts, logs, and backups accordingly.
- This recipe changes active Kubernetes root CA and ServiceAccount signing files. Run it only as part of a tested certificate rotation procedure.
- This recipe does not restart kube-apiserver, kube-controller-manager, scheduler, kubelet, or workloads. Plan required restarts separately.
- This recipe does not create staged root CA or ServiceAccount files. Generate and distribute them before running this playbook.
- The move commands can replace existing `ca-old.*` and `sa-old.*` files if they already exist.
- Back up Kubernetes PKI files and kubeconfigs before running this recipe.
- Test the complete activation and rollback procedure on a non-production or fully recoverable cluster before relying on it.
