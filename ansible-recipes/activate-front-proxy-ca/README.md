# Activating a Staged front-proxy CA

Chinese version: `README.zh-CN.md`

This recipe promotes staged Kubernetes front-proxy CA files to the active front-proxy CA filenames on each master node. By default it assumes a kubeadm-managed control plane where PKI files live under `/etc/kubernetes/pki`.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on hosts in the `masters` inventory group with privilege escalation, one host at a time.
2. Moves the active `front-proxy-ca.crt` and `front-proxy-ca.key` files to `front-proxy-ca-old.crt` and `front-proxy-ca-old.key`.
3. Moves `front-proxy-ca-new.crt` and `front-proxy-ca-new.key` into the active front-proxy CA filenames.
4. Prints the certificate count, subject, issuer, validity dates, and SHA256 fingerprint for the active front-proxy CA certificate.

## Requirements

- A kubeadm-managed Kubernetes control plane, or equivalent PKI layout
- Inventory group named `masters`
- Existing active front-proxy CA certificate and key under `/etc/kubernetes/pki`
- Staged replacement front-proxy CA certificate and key under `/etc/kubernetes/pki`
- `mv`, `grep`, and `openssl` available on each target host
- SSH access with privilege escalation, because the PKI files are normally root-owned

No extra variables are required when the kubeadm defaults and staged CA filenames match your environment.

## Optional Variables

- `pki_dir`: Kubernetes PKI directory, defaults to `'/etc/kubernetes/pki'`

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

To run with a specific SSH key:

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/activate-front-proxy-ca/playbook.yml
```

## Important Warnings

- This recipe moves certificate authority private key material. Protect target hosts, logs, and backups accordingly.
- This recipe changes which front-proxy CA files are active. Run it only as part of a tested certificate rotation procedure.
- This recipe does not restart kube-apiserver, kube-controller-manager, or kubelet. Plan required restarts separately.
- This recipe does not create staged CA files. Generate and distribute them before running this playbook.
- The move commands can replace existing `front-proxy-ca-old.*` files if they already exist.
- Back up Kubernetes PKI files before running this recipe.
