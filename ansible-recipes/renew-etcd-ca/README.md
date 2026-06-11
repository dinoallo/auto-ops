# Renewing the etcd CA

Chinese version: `README.zh-CN.md`

This recipe generates a staged replacement etcd CA and a trust bundle for kubeadm-managed etcd PKI. It creates `ca-new.key`, `ca-new.crt`, and `ca-bundle.crt` by default under the etcd PKI directory, while leaving the currently active `ca.crt` and `ca.key` in place.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on `target_hosts`, defaulting to the `etcd_members` inventory group, with privilege escalation.
2. Validates the etcd CA file names and certificate generation settings.
3. Verifies that the current etcd CA certificate exists.
4. Generates a new etcd CA private key.
5. Generates a new self-signed etcd CA certificate with the configured subject, validity, digest, basic constraints, and key usage.
6. Builds a trust bundle by concatenating the current etcd CA certificate and the new etcd CA certificate.
7. Sets permissions on the generated key, certificate, and bundle files.
8. Prints the bundle certificate count and new CA certificate details for verification.

## Requirements

- A kubeadm-managed Kubernetes control plane with local etcd PKI files
- Inventory group named `etcd_members`, unless you override `target_hosts`
- Existing active etcd CA certificate, defaulting to `/etc/kubernetes/pki/etcd/ca.crt`
- `openssl`, `grep`, and `cat` available on each target host
- SSH access with privilege escalation, because the default PKI directory is normally root-owned

No extra variables are required when the kubeadm defaults match your environment.

## Optional Variables

- `target_hosts`: target host group, defaults to `'etcd_members'`
- `etcd_pki_dir`: etcd PKI directory, defaults to `'/etc/kubernetes/pki/etcd'`
- `etcd_ca_current_cert`: current active CA certificate filename, defaults to `'ca.crt'`
- `etcd_ca_new_key`: staged new CA private key filename, defaults to `'ca-new.key'`
- `etcd_ca_new_cert`: staged new CA certificate filename, defaults to `'ca-new.crt'`
- `etcd_ca_bundle`: old plus new CA bundle filename, defaults to `'ca-bundle.crt'`
- `etcd_ca_key_bits`: private key size, defaults to `4096`
- `etcd_ca_valid_days`: certificate validity in days, defaults to `3650`
- `etcd_ca_subject`: certificate subject, defaults to `'/CN=etcd-ca'`
- `etcd_ca_digest`: OpenSSL digest option suffix, defaults to `'sha256'`
- `etcd_ca_basic_constraints`: OpenSSL basic constraints extension, defaults to `'basicConstraints=critical,CA:TRUE'`
- `etcd_ca_key_usage`: OpenSSL key usage extension, defaults to `'keyUsage=critical,keyCertSign,cRLSign'`
- `etcd_ca_new_key_mode`: staged key file mode, defaults to `'0600'`
- `etcd_ca_new_cert_mode`: staged certificate file mode, defaults to `'0644'`
- `etcd_ca_bundle_mode`: CA bundle file mode, defaults to `'0644'`
- `openssl_command`: OpenSSL command or path, defaults to `'openssl'`
- `grep_command`: grep command or path, defaults to `'grep'`
- `cat_command`: cat command or path, defaults to `'cat'`
- `shell_executable`: shell used for bundle creation, defaults to `'/bin/bash'`

Example inventory layout:

```ini
[etcd_members]
cp1
cp2
cp3
```

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/renew-etcd-ca/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-etcd-ca/playbook.yml
```

To use custom CA filenames or a different subject:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-etcd-ca/playbook.yml \
  -e etcd_ca_new_key=ca-2026.key \
  -e etcd_ca_new_cert=ca-2026.crt \
  -e etcd_ca_bundle=ca-2026-bundle.crt \
  -e etcd_ca_subject=/CN=etcd-ca-2026
```

To run against a specific target group:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-etcd-ca/playbook.yml \
  -e target_hosts=cp1
```

To run with a specific SSH key:

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/renew-etcd-ca/playbook.yml
```

## Important Warnings

- This recipe generates CA private key material. Protect the target hosts, logs, backups, and generated files accordingly.
- This recipe does not replace the active etcd CA files. It only stages a new CA and builds a trust bundle.
- This recipe does not renew etcd leaf certificates. Renew the leaf certificates after staging the new CA and before removing old CA trust.
- Back up etcd data and the Kubernetes PKI directory before running any CA rotation workflow.
- Verify the printed subject, issuer, validity dates, fingerprint, and bundle certificate count before using the generated files.
- Test the full CA renewal, certificate renewal, activation, restart, and rollback procedure on a non-production or fully recoverable cluster first.
