# Generating a New front-proxy CA and Trust Bundle

Chinese version: `README.zh-CN.md`

This recipe generates a replacement Kubernetes front-proxy CA on one source master, builds a trust bundle containing the current and new front-proxy CA certificates, and distributes the generated files to all target master nodes.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on the target master hosts with privilege escalation.
2. Verifies that all target hosts start with the same active front-proxy CA certificate.
3. Generates the new front-proxy CA private key and certificate on the configured source host.
4. Builds a bundle containing the current and new front-proxy CA certificates on the source host.
5. Sets file permissions for the generated CA files.
6. Reads the generated files from the source host and installs them on all target hosts.
7. Prints the bundle certificate count and the new CA certificate details.

## Requirements

- A kubeadm-managed Kubernetes control plane, or equivalent PKI layout
- Inventory group named `masters`, unless `target_hosts` is overridden
- A source host defaults to the first host in the play, unless `front_proxy_ca_source_host` is overridden
- Existing active front-proxy CA certificate under the configured PKI directory on every target host
- `openssl`, `grep`, and `cat` available on the target hosts
- SSH access with privilege escalation, because the PKI files are normally root-owned

No extra variables are required when the defaults match your environment.

## Optional Variables

- `target_hosts`: target host group, defaults to `masters`
- `front_proxy_ca_source_host`: host where the new CA is generated, defaults to the first host in the play
- `pki_dir`: Kubernetes PKI directory, defaults to `'/etc/kubernetes/pki'`
- `front_proxy_ca_current_cert`: active front-proxy CA certificate filename, defaults to `'front-proxy-ca.crt'`
- `front_proxy_ca_new_key`: new front-proxy CA private key filename, defaults to `'front-proxy-ca-new.key'`
- `front_proxy_ca_new_cert`: new front-proxy CA certificate filename, defaults to `'front-proxy-ca-new.crt'`
- `front_proxy_ca_bundle`: trust bundle filename, defaults to `'front-proxy-ca-bundle.crt'`
- `front_proxy_ca_key_bits`: new CA key size, defaults to `4096`
- `front_proxy_ca_valid_days`: new CA validity period in days, defaults to `3650`
- `front_proxy_ca_subject`: new CA subject, defaults to `'/CN=kubernetes-front-proxy-ca'`
- `front_proxy_ca_digest`: certificate digest name, defaults to `'sha256'`
- `front_proxy_ca_basic_constraints`: CA basic constraints extension
- `front_proxy_ca_key_usage`: CA key usage extension
- `front_proxy_ca_new_key_mode`: private key mode, defaults to `'0600'`
- `front_proxy_ca_new_cert_mode`: certificate mode, defaults to `'0644'`
- `front_proxy_ca_bundle_mode`: bundle mode, defaults to `'0644'`
- `openssl_command`: path or command name for `openssl`, defaults to `'openssl'`
- `grep_command`: path or command name for `grep`, defaults to `'grep'`
- `cat_command`: path or command name for `cat`, defaults to `'cat'`
- `shell_executable`: shell used for bundle creation, defaults to `'/bin/bash'`

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/renew-front-proxy-ca/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-front-proxy-ca/playbook.yml
```

To use a different source host:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-front-proxy-ca/playbook.yml \
  -e front_proxy_ca_source_host=cp1
```

To use custom generated filenames:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-front-proxy-ca/playbook.yml \
  -e front_proxy_ca_new_key=front-proxy-ca-2026.key \
  -e front_proxy_ca_new_cert=front-proxy-ca-2026.crt \
  -e front_proxy_ca_bundle=front-proxy-ca-bundle-2026.crt
```

## Important Warnings

- This recipe creates and distributes certificate authority private key material. Protect target hosts, logs, and backups accordingly.
- This recipe does not activate the new front-proxy CA. It prepares staged files for a later activation step.
- This recipe does not renew front-proxy client certificates and does not restart Kubernetes components.
- All target hosts must start with the same active front-proxy CA certificate.
- Back up Kubernetes PKI files before running this recipe.
- Test the complete rotation and rollback procedure on a non-production or fully recoverable cluster.
