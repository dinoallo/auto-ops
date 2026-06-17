# Renewing etcd Leaf Certificates with a Staged CA

Chinese version: `README.zh-CN.md`

This recipe uses a staged new etcd CA to renew kubeadm-managed etcd leaf certificates. It writes the renewed files with `-new` filenames next to the existing certificates, so the current active certificates are not replaced by this playbook.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on hosts in the `etcd_members` inventory group with privilege escalation, one host at a time.
2. Recreates a temporary kubeadm certificate staging directory.
3. Reads the active etcd leaf certificate paths from the kube-apiserver and etcd static pod manifests, then copies those certificates and private keys into the staging directory as kubeadm renewal templates.
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
- `manifest_dir`: static pod manifest directory, defaults to `'/etc/kubernetes/manifests'`
- `kube_apiserver_manifest`: kube-apiserver manifest path, defaults to `manifest_dir + '/kube-apiserver.yaml'`
- `etcd_manifest`: etcd manifest path, defaults to `manifest_dir + '/etcd.yaml'`
- `staged_etcd_ca_cert`: staged etcd CA certificate, defaults to `etcd_pki_dir + '/ca-new.crt'`
- `staged_etcd_ca_key`: staged etcd CA private key, defaults to `etcd_pki_dir + '/ca-new.key'`
- `healthcheck_client_cert_template`: healthcheck client template certificate, defaults to `etcd_pki_dir + '/healthcheck-client.crt'`
- `healthcheck_client_key_template`: healthcheck client template key, defaults to `etcd_pki_dir + '/healthcheck-client.key'`
- `apiserver_etcd_client_cert_output`: renewed apiserver-etcd-client certificate output, defaults to `pki_dir + '/apiserver-etcd-client-new.crt'`
- `apiserver_etcd_client_key_output`: renewed apiserver-etcd-client key output, defaults to `pki_dir + '/apiserver-etcd-client-new.key'`
- `healthcheck_client_cert_output`: renewed healthcheck client certificate output, defaults to `etcd_pki_dir + '/healthcheck-client-new.crt'`
- `healthcheck_client_key_output`: renewed healthcheck client key output, defaults to `etcd_pki_dir + '/healthcheck-client-new.key'`
- `etcd_peer_cert_output`: renewed etcd peer certificate output, defaults to `etcd_pki_dir + '/peer-new.crt'`
- `etcd_peer_key_output`: renewed etcd peer key output, defaults to `etcd_pki_dir + '/peer-new.key'`
- `etcd_server_cert_output`: renewed etcd server certificate output, defaults to `etcd_pki_dir + '/server-new.crt'`
- `etcd_server_key_output`: renewed etcd server key output, defaults to `etcd_pki_dir + '/server-new.key'`
- `prevent_overwrite_active_etcd_leaf_certs`: fail if any configured output path is currently used by the static pod manifests, defaults to `true`
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
ansible-playbook --syntax-check ansible-recipes/renew-etcd-certs/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-etcd-certs/playbook.yml
```

To use custom PKI paths:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-etcd-certs/playbook.yml \
  -e pki_dir=/etc/kubernetes/pki \
  -e etcd_pki_dir=/etc/kubernetes/pki/etcd
```

When the active manifests already use the default `*-new` certificate paths, write a second staged set to different filenames:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-etcd-certs/playbook.yml \
  -e apiserver_etcd_client_cert_output=/etc/kubernetes/pki/apiserver-etcd-client-next.crt \
  -e apiserver_etcd_client_key_output=/etc/kubernetes/pki/apiserver-etcd-client-next.key \
  -e healthcheck_client_cert_output=/etc/kubernetes/pki/etcd/healthcheck-client-next.crt \
  -e healthcheck_client_key_output=/etc/kubernetes/pki/etcd/healthcheck-client-next.key \
  -e etcd_peer_cert_output=/etc/kubernetes/pki/etcd/peer-next.crt \
  -e etcd_peer_key_output=/etc/kubernetes/pki/etcd/peer-next.key \
  -e etcd_server_cert_output=/etc/kubernetes/pki/etcd/server-next.crt \
  -e etcd_server_key_output=/etc/kubernetes/pki/etcd/server-next.key
```

To run with a specific SSH key:

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/renew-etcd-certs/playbook.yml
```

## Important Warnings

- This recipe handles private keys and certificate authority material. Protect the target hosts, logs, and generated files accordingly.
- This recipe does not create the new etcd CA. The `ca-new.crt` and `ca-new.key` files must already exist on each target host.
- This recipe does not replace active certificate files, restart etcd, or restart kube-apiserver. It only prepares `*-new.crt` and `*-new.key` files for a separate controlled cutover.
- Run it only after backing up etcd data and the Kubernetes PKI files.
- Verify the printed issuer, validity dates, and SANs before using the renewed certificates.
- Test the full rotation and rollback procedure on a non-production or fully recoverable cluster before relying on it.
