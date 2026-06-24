# Renewing Root-CA-Signed Kubernetes Certificates and Kubeconfigs

Chinese version: `README.zh-CN.md`

This recipe renews Kubernetes API server certificates and selected kubeconfigs with a staged new root CA. It writes renewed files with date-hour-stamped `-new-<renewal_id>` filenames, so the active files are not replaced by this playbook.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on hosts in the `masters` inventory group with privilege escalation, one host at a time.
2. Recreates a temporary kubeadm certificate staging directory.
3. Copies current API server certificate templates into the staging directory.
4. Stages `ca-new-<renewal_id>.crt` and `ca-new-<renewal_id>.key` as kubeadm's signing CA.
5. Writes a temporary kubeadm configuration. With `kubeadm_config_api_version=v1beta3`, no certificate validity fields are written; with `v1beta4`, optional validity fields can be added.
6. Renews `apiserver` and `apiserver-kubelet-client` certificates with kubeadm.
7. Installs the renewed API server certificates and keys with date-hour-stamped filenames.
8. Creates new client certificates for `admin`, `controller-manager`, and `scheduler`.
9. Creates `admin-new-<renewal_id>.conf`, `controller-manager-new-<renewal_id>.conf`, and `scheduler-new-<renewal_id>.conf` that embed the new client certificates and use `ca-bundle-<renewal_id>.crt`.
10. Verifies the renewed certificates and checks `/readyz` with the generated kubeconfigs.

## Requirements

- A kubeadm-managed Kubernetes control plane
- Inventory group named `masters`
- `kubeadm`, `kubectl`, `openssl`, `cp`, `install`, and `chmod` available on each target host
- Current API server certificates and kubeconfigs under the configured Kubernetes directories
- Staged root CA files `ca-new-<renewal_id>.crt`, `ca-new-<renewal_id>.key`, and `ca-bundle-<renewal_id>.crt`
- SSH access with privilege escalation, because the PKI and kubeconfig files are normally root-owned

No extra variables are required when the kubeadm defaults and staged CA filenames match your environment.

## Optional Variables

- `pki_dir`: Kubernetes PKI directory, defaults to `'/etc/kubernetes/pki'`
- `kube_dir`: Kubernetes configuration directory, defaults to `'/etc/kubernetes'`
- `renewal_id`: date-hour or custom ID for staged file names, defaults to `YYYYMMDDHH`
- `stage_dir`: temporary kubeadm certificate renewal directory, defaults to `'/tmp/kubeadm-root-leaf-renew'`
- `work_dir`: temporary kubeconfig and client certificate workspace, defaults to `'/tmp/kubeconfig-root-ca-renew'`
- `kubeadm_config_api_version`: kubeadm configuration API used for API server certificate renewal, defaults to `'v1beta3'`; set to `'v1beta4'` only on kubeadm versions that support it
- `kubeadm_config_file`: temporary kubeadm configuration path, defaults to `stage_dir + '/kubeadm-config.yaml'`
- `kubeadm_certificate_validity_period`: optional kubeadm-managed leaf certificate validity duration, for example `'867240h'`; only supported when `kubeadm_config_api_version=v1beta4`
- `kubeadm_ca_certificate_validity_period`: optional CA certificate validity duration, for example `'867240h'`; only supported when `kubeadm_config_api_version=v1beta4`
- `kubeadm_cluster_name`: cluster name written to the temporary kubeadm config, defaults to `'kubernetes'`
- `kubeadm_kubernetes_version`: optional Kubernetes version written to the temporary kubeadm config, defaults to empty
- `kubeconfig_client_cert_valid_days`: OpenSSL-signed kubeconfig client certificate validity in days, defaults to `365`; use `36135` for 99 years

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

To request 99-year kubeadm-managed API server leaf certificates on kubeadm versions that support `kubeadm.k8s.io/v1beta4`, and 99-year generated kubeconfig client certificates:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-k8s-certs/playbook.yml \
  -e kubeadm_config_api_version=v1beta4 \
  -e kubeadm_certificate_validity_period=867240h \
  -e kubeconfig_client_cert_valid_days=36135
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
- kubeadm config API `v1beta3` does not support certificate validity fields. Use `kubeadm_config_api_version=v1beta4` only on kubeadm versions that support it; otherwise kubeadm fails strict config decoding.
- The generated kubeconfigs are verified against `/readyz`; a failed readiness check must be investigated before activation.
- Back up Kubernetes PKI files and kubeconfigs before running this recipe.
- Test the full rotation and rollback procedure on a non-production or fully recoverable cluster.
