# Renewing Root-CA-Signed Kubernetes Certificates and Kubeconfigs

Chinese version: `README.zh-CN.md`

This recipe renews Kubernetes API server certificates and selected kubeconfigs with a staged new root CA. It writes renewed files with `-new` filenames, so the active files are not replaced by this playbook.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on hosts in the `masters` inventory group with privilege escalation, one host at a time.
2. Recreates a temporary kubeadm certificate staging directory.
3. Copies current API server certificate templates into the staging directory.
4. Stages `ca-new.crt` and `ca-new.key` as kubeadm's signing CA.
5. Renews `apiserver` and `apiserver-kubelet-client` certificates with kubeadm.
6. Installs the renewed API server certificates and keys with `-new` filenames.
7. Creates new client certificates for `admin`, `controller-manager`, and `scheduler`.
8. Creates `admin-new.conf`, `controller-manager-new.conf`, and `scheduler-new.conf` that embed the new client certificates and use `ca-bundle.crt`.
9. Verifies the renewed certificates and checks `/readyz` with the generated kubeconfigs.

## Requirements

- A kubeadm-managed Kubernetes control plane
- Inventory group named `masters`
- `kubeadm`, `kubectl`, `openssl`, `cp`, `install`, and `chmod` available on each target host
- Current API server certificates and kubeconfigs under the configured Kubernetes directories
- Staged root CA files `ca-new.crt`, `ca-new.key`, and `ca-bundle.crt`
- SSH access with privilege escalation, because the PKI and kubeconfig files are normally root-owned

No extra variables are required when the kubeadm defaults and staged CA filenames match your environment.

## Optional Variables

- `pki_dir`: Kubernetes PKI directory, defaults to `'/etc/kubernetes/pki'`
- `kube_dir`: Kubernetes configuration directory, defaults to `'/etc/kubernetes'`
- `stage_dir`: temporary kubeadm certificate renewal directory, defaults to `'/tmp/kubeadm-root-leaf-renew'`
- `work_dir`: temporary kubeconfig and client certificate workspace, defaults to `'/tmp/kubeconfig-root-ca-renew'`

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/renew-k8s-certs/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-k8s-certs/playbook.yml
```

To use custom Kubernetes directories:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-k8s-certs/playbook.yml \
  -e pki_dir=/etc/kubernetes/pki \
  -e kube_dir=/etc/kubernetes
```

To run with a specific SSH key:

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/renew-k8s-certs/playbook.yml
```

## Important Warnings

- This recipe handles private keys and root CA material. Protect target hosts, logs, and generated files accordingly.
- This recipe does not create the staged root CA files.
- This recipe does not replace active API server certificates or kubeconfigs, and it does not restart Kubernetes components.
- The generated kubeconfigs are verified against `/readyz`; a failed readiness check must be investigated before activation.
- Back up Kubernetes PKI files and kubeconfigs before running this recipe.
- Test the full rotation and rollback procedure on a non-production or fully recoverable cluster.
