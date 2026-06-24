# Renewing front-proxy-client Certificates with a Staged CA

Chinese version: `README.zh-CN.md`

This recipe renews the kubeadm-managed `front-proxy-client` certificate on each master node by using staged front-proxy CA files. It writes the renewed certificate and key with date-hour-stamped `-new-<renewal_id>` filenames, so the active files are not replaced by this playbook.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on hosts in the `masters` inventory group with privilege escalation, one host at a time.
2. Recreates a temporary kubeadm staging directory.
3. Reads the active `front-proxy-client` certificate and key paths from the kube-apiserver static pod manifest, then copies those files into the staging directory as renewal templates.
4. Copies `front-proxy-ca-new-<renewal_id>.crt` and `front-proxy-ca-new-<renewal_id>.key` into the staging directory as kubeadm's signing CA.
5. Writes a temporary kubeadm configuration. With `kubeadm_config_api_version=v1beta3`, no certificate validity fields are written; with `v1beta4`, optional validity fields can be added.
6. Runs `kubeadm certs renew front-proxy-client`.
7. Installs the renewed certificate and key as `front-proxy-client-new-<renewal_id>.crt` and `front-proxy-client-new-<renewal_id>.key`.
8. Prints subject, issuer, validity dates, and extended key usage for the renewed certificate.

## Requirements

- A kubeadm-managed Kubernetes control plane
- Inventory group named `masters`
- `kubeadm`, `openssl`, and `install` available on each target host
- Existing `front-proxy-client.crt` and `front-proxy-client.key` under the configured PKI directory
- Staged front-proxy CA files at `front-proxy-ca-new-<renewal_id>.crt` and `front-proxy-ca-new-<renewal_id>.key`
- SSH access with privilege escalation, because the PKI files are normally root-owned

No extra variables are required when the kubeadm defaults and staged CA filenames match your environment.

## Optional Variables

- `stage_dir`: temporary kubeadm renewal directory, defaults to `'/tmp/kubeadm-front-proxy-leaf-renew'`
- `pki_dir`: Kubernetes PKI directory, defaults to `'/etc/kubernetes/pki'`
- `manifest_dir`: static pod manifest directory, defaults to `'/etc/kubernetes/manifests'`
- `kube_apiserver_manifest`: kube-apiserver manifest path, defaults to `manifest_dir + '/kube-apiserver.yaml'`
- `renewal_id`: date-hour or custom ID for staged file names, defaults to `YYYYMMDDHH`
- `staged_front_proxy_ca_cert`: staged front-proxy CA certificate, defaults to `pki_dir + '/front-proxy-ca-new-<renewal_id>.crt'`
- `staged_front_proxy_ca_key`: staged front-proxy CA private key, defaults to `pki_dir + '/front-proxy-ca-new-<renewal_id>.key'`
- `front_proxy_client_cert_output`: renewed front-proxy client certificate output, defaults to `pki_dir + '/front-proxy-client-new-<renewal_id>.crt'`
- `front_proxy_client_key_output`: renewed front-proxy client key output, defaults to `pki_dir + '/front-proxy-client-new-<renewal_id>.key'`
- `prevent_overwrite_active_front_proxy_client_certs`: fail if an output path is currently used by the kube-apiserver manifest, defaults to `true`
- `kubeadm_config_api_version`: kubeadm configuration API used for renewal, defaults to `'v1beta3'`; set to `'v1beta4'` only on kubeadm versions that support it
- `kubeadm_config_file`: temporary kubeadm configuration path, defaults to `stage_dir + '/kubeadm-config.yaml'`
- `kubeadm_certificate_validity_period`: optional leaf certificate validity duration, for example `'867240h'`; only supported when `kubeadm_config_api_version=v1beta4`
- `kubeadm_ca_certificate_validity_period`: optional CA certificate validity duration, for example `'867240h'`; only supported when `kubeadm_config_api_version=v1beta4`
- `kubeadm_cluster_name`: cluster name written to the temporary kubeadm config, defaults to `'kubernetes'`
- `kubeadm_kubernetes_version`: optional Kubernetes version written to the temporary kubeadm config, defaults to empty

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

To request a 99-year front-proxy-client certificate on kubeadm versions that support `kubeadm.k8s.io/v1beta4`:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-front-proxy-certs/playbook.yml \
  -e kubeadm_config_api_version=v1beta4 \
  -e kubeadm_certificate_validity_period=867240h
```

When the active manifest already uses the default `*-new` certificate paths, write a second staged set to different filenames:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-front-proxy-certs/playbook.yml \
  -e front_proxy_client_cert_output=/etc/kubernetes/pki/front-proxy-client-next.crt \
  -e front_proxy_client_key_output=/etc/kubernetes/pki/front-proxy-client-next.key
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
- By default, this recipe refuses to write renewed files to paths currently used by the kube-apiserver manifest.
- kubeadm config API `v1beta3` does not support certificate validity fields. Use `kubeadm_config_api_version=v1beta4` only on kubeadm versions that support it; otherwise kubeadm fails strict config decoding.
- Verify the printed issuer and validity dates before activating or using the renewed certificate.
- Back up Kubernetes PKI files before running this recipe.
