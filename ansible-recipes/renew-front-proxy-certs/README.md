# Renewing front-proxy-client Certificates with a Staged CA

Chinese version: `README.zh-CN.md`

This recipe renews the kubeadm-managed `front-proxy-client` certificate on each master node by using staged front-proxy CA files. It writes the renewed certificate and key with `-new` filenames, so the active files are not replaced by this playbook.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on hosts in the `masters` inventory group with privilege escalation, one host at a time.
2. Recreates a temporary kubeadm staging directory.
3. Copies the current `front-proxy-client` certificate and key into the staging directory as renewal templates.
4. Copies `front-proxy-ca-new.crt` and `front-proxy-ca-new.key` into the staging directory as kubeadm's signing CA.
5. Runs `kubeadm certs renew front-proxy-client`.
6. Installs the renewed certificate and key as `front-proxy-client-new.crt` and `front-proxy-client-new.key`.
7. Prints subject, issuer, validity dates, and extended key usage for the renewed certificate.

## Requirements

- A kubeadm-managed Kubernetes control plane
- Inventory group named `masters`
- `kubeadm`, `openssl`, and `install` available on each target host
- Existing `front-proxy-client.crt` and `front-proxy-client.key` under the configured PKI directory
- Staged front-proxy CA files at `front-proxy-ca-new.crt` and `front-proxy-ca-new.key`
- SSH access with privilege escalation, because the PKI files are normally root-owned

No extra variables are required when the kubeadm defaults and staged CA filenames match your environment.

## Optional Variables

- `stage_dir`: temporary kubeadm renewal directory, defaults to `'/tmp/kubeadm-front-proxy-leaf-renew'`
- `pki_dir`: Kubernetes PKI directory, defaults to `'/etc/kubernetes/pki'`

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/renew-front-proxy-certs/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-front-proxy-certs/playbook.yml
```

To use a custom PKI path:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-front-proxy-certs/playbook.yml \
  -e pki_dir=/etc/kubernetes/pki
```

To run with a specific SSH key:

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/renew-front-proxy-certs/playbook.yml
```

## Important Warnings

- This recipe handles private keys and front-proxy CA material. Protect target hosts, logs, and generated files accordingly.
- This recipe does not create the staged front-proxy CA files.
- This recipe does not replace active `front-proxy-client.*` files and does not restart Kubernetes components.
- Verify the printed issuer and validity dates before activating or using the renewed certificate.
- Back up Kubernetes PKI files before running this recipe.
