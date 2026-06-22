# Ansible Recipes

Chinese version: `README.zh-CN.md`

This directory contains executable Ansible recipes. Each recipe is usually a standalone directory with at least:

- `playbook.yml`: the executable playbook
- `README.md`: usage, variables, and examples

## Environment Setup

If you do not want to install Ansible globally, you can use the system `python3` to create a local virtual environment in this directory:

```bash
cd ansible-recipes
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ansible
```

Verify that the commands are available inside the virtual environment:

```bash
ansible --version
ansible-playbook --version
```

When you come back later, reactivate the environment before running any recipe:

```bash
cd ansible-recipes
source .venv/bin/activate
```

To leave the virtual environment:

```bash
deactivate
```

## Before You Start

Make sure you have:

1. `ansible-playbook` installed
2. A working inventory file such as `inventory.ini`
3. SSH access and the required permissions for the target hosts

The basic invocation pattern is:

```bash
ansible-playbook \
  -i inventory.ini \
  path/to/playbook.yml \
  -e key=value
```

To use a specific SSH key for the connection:

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  path/to/playbook.yml \
  -e key=value
```

## Kubernetes Root CA and ServiceAccount Key Rotation

Run the following sequence from the repository root to rotate the Kubernetes root
CA (`ca.crt` / `ca.key`) and ServiceAccount signing key (`sa.key` /
`sa.pub`) with the dedicated playbooks. This is a high-impact operation: it
updates control-plane static Pod manifests and restarts control-plane Pods and
kubelets. Validate the inventory and take backups before using it on a shared
cluster.

Use one `RENEWAL_ID` across the whole run. By default the playbooks use
`YYYYMMDD`; pass an explicit value when the rotation spans multiple days or
when you run more than one rotation on the same day.

1. Generate and distribute the staged root CA, CA bundle, and ServiceAccount
   key pair:

   ```bash
   RENEWAL_ID=$(date -u +%Y%m%d)

   ansible-playbook \
     -i inventory.ini \
     ansible-recipes/renew-k8s-ca/playbook.yml \
     -e renewal_id=${RENEWAL_ID}
   ```

2. Move the API server and controller manager into the compatibility phase.
   The API server trusts the CA bundle and accepts both old and new
   ServiceAccount public keys, while the controller manager still signs with
   the old keys:

   ```bash
   ansible-playbook \
     -i inventory.ini \
     ansible-recipes/configure-k8s-ca-bundle/playbook.yml \
     -e renewal_id=${RENEWAL_ID} \
     -e restart_static_pods=true
   ```

3. Record the ServiceAccount signer cutover time and switch new token signing
   to the staged CA and ServiceAccount key:

   ```bash
   CUTOVER=$(date -u +%Y-%m-%dT%H:%M:%SZ)

   ansible-playbook \
     -i inventory.ini \
     ansible-recipes/configure-k8s-ca-bundle/playbook.yml \
     -e renewal_id=${RENEWAL_ID} \
     -e ca_cert_path=/etc/kubernetes/pki/ca-new-${RENEWAL_ID}.crt \
     -e ca_key_path=/etc/kubernetes/pki/ca-new-${RENEWAL_ID}.key \
     -e service_account_signing_key_path=/etc/kubernetes/pki/sa-new-${RENEWAL_ID}.key \
     -e service_account_private_key_path=/etc/kubernetes/pki/sa-new-${RENEWAL_ID}.key \
     -e restart_static_pods=true
   ```

4. Renew staged control-plane serving, client, and system kubeconfig
   certificates against the staged root CA:

   ```bash
   ansible-playbook \
     -i inventory.ini \
     ansible-recipes/renew-k8s-certs/playbook.yml \
     -e renewal_id=${RENEWAL_ID}
   ```

5. Renew kubelet client certificates and keep kubelets trusting the CA bundle
   during the compatibility phase:

   ```bash
   ansible-playbook \
     -i inventory.ini \
     ansible-recipes/renew-k8s-kubelet-certs/playbook.yml \
     -e renewal_id=${RENEWAL_ID} \
     -e kubelet_trust_mode=bundle
   ```

6. Restart or wait for workloads that mount projected ServiceAccount tokens,
   then audit that no pre-cutover tokens remain active:

   ```bash
   ansible-playbook \
     -i inventory.ini \
     ansible-recipes/audit-service-account-token-retirement/playbook.yml \
     -e renewal_id=${RENEWAL_ID} \
     -e sa_key_cutover=${CUTOVER} \
     -e new_ca_file=/etc/kubernetes/pki/ca-new-${RENEWAL_ID}.crt
   ```

7. Promote the staged root CA and ServiceAccount key pair to the active files
   and switch control-plane manifests to new-only trust:

   ```bash
   ansible-playbook \
     -i inventory.ini \
     ansible-recipes/activate-k8s-ca/playbook.yml \
     -e renewal_id=${RENEWAL_ID} \
     -e sa_key_cutover=${CUTOVER} \
     -e new_ca_file=/etc/kubernetes/pki/ca-new-${RENEWAL_ID}.crt \
     -e restart_static_pods=true
   ```

8. Rewrite system kubeconfigs so they embed only the promoted root CA:

   ```bash
   ansible-playbook \
     -i inventory.ini \
     ansible-recipes/converge-k8s-kubeconfig-ca/playbook.yml \
     -e restart_static_pods=true
   ```

9. Switch kubelet trust from the CA bundle to the promoted root CA:

   ```bash
   ansible-playbook \
     -i inventory.ini \
     ansible-recipes/renew-k8s-kubelet-certs/playbook.yml \
     -e renewal_id=${RENEWAL_ID} \
     -e kubelet_trust_mode=new \
     -e promote_kubelet_ca=true \
     -e renew_kubelet_client_cert=false
   ```

10. Verify the control-plane kubeconfigs can still reach the API server:

    ```bash
    ansible-playbook \
      -i inventory.ini \
      ansible-recipes/verify-system-kubeconfig/playbook.yml
    ```

## Available Recipes

### activate-etcd-certs

Path: `ansible-recipes/activate-etcd-certs/playbook.yml`

For recipe-specific details, see `ansible-recipes/activate-etcd-certs/README.md`.

### configure-etcd-ca-bundle

Path: `ansible-recipes/configure-etcd-ca-bundle/playbook.yml`

For recipe-specific details, see `ansible-recipes/configure-etcd-ca-bundle/README.md`.

### configure-front-proxy-ca-bundle

Path: `ansible-recipes/configure-front-proxy-ca-bundle/playbook.yml`

For recipe-specific details, see `ansible-recipes/configure-front-proxy-ca-bundle/README.md`.

### configure-front-proxy-client-certs

Path: `ansible-recipes/configure-front-proxy-client-certs/playbook.yml`

For recipe-specific details, see `ansible-recipes/configure-front-proxy-client-certs/README.md`.

### configure-k8s-ca-bundle

Path: `ansible-recipes/configure-k8s-ca-bundle/playbook.yml`

For recipe-specific details, see `ansible-recipes/configure-k8s-ca-bundle/README.md`.

### activate-k8s-ca

Path: `ansible-recipes/activate-k8s-ca/playbook.yml`

For recipe-specific details, see `ansible-recipes/activate-k8s-ca/README.md`.

### audit-service-account-token-retirement

Path: `ansible-recipes/audit-service-account-token-retirement/playbook.yml`

For recipe-specific details, see `ansible-recipes/audit-service-account-token-retirement/README.md`.

### archive-renewed-k8s-pki

Path: `ansible-recipes/archive-renewed-k8s-pki/playbook.yml`

For recipe-specific details, see `ansible-recipes/archive-renewed-k8s-pki/README.md`.

### configure-kubepods-io-limit

Path: `ansible-recipes/configure-kubepods-io-limit/playbook.yml`

For recipe-specific details, see `ansible-recipes/configure-kubepods-io-limit/README.md`.

### backup-k8s-data

Path: `ansible-recipes/backup-k8s-data/playbook.yml`

For recipe-specific details, see `ansible-recipes/backup-k8s-data/README.md`.

### backup-etcd-data

Path: `ansible-recipes/backup-etcd-data/playbook.yml`

For recipe-specific details, see `ansible-recipes/backup-etcd-data/README.md`.

### change-k8s-privilege-group

Path: `ansible-recipes/change-k8s-privilege-group/playbook.yml`

For recipe-specific details, see `ansible-recipes/change-k8s-privilege-group/README.md`.

### upgrade-os-packages

Path: `ansible-recipes/upgrade-os-packages/playbook.yml`

For recipe-specific details, see `ansible-recipes/upgrade-os-packages/README.md`.

### safely-copying-files

Path: `ansible-recipes/safely-copying-files/playbook.yml`

For recipe-specific details, see `ansible-recipes/safely-copying-files/README.md`.

### renew-etcd-ca

Path: `ansible-recipes/renew-etcd-ca/playbook.yml`

For recipe-specific details, see `ansible-recipes/renew-etcd-ca/README.md`.

### renew-k8s-ca

Path: `ansible-recipes/renew-k8s-ca/playbook.yml`

For recipe-specific details, see `ansible-recipes/renew-k8s-ca/README.md`.

### renew-k8s-certs

Path: `ansible-recipes/renew-k8s-certs/playbook.yml`

For recipe-specific details, see `ansible-recipes/renew-k8s-certs/README.md`.

### renew-k8s-kubelet-certs

Path: `ansible-recipes/renew-k8s-kubelet-certs/playbook.yml`

For recipe-specific details, see `ansible-recipes/renew-k8s-kubelet-certs/README.md`.

### converge-k8s-kubeconfig-ca

Path: `ansible-recipes/converge-k8s-kubeconfig-ca/playbook.yml`

For recipe-specific details, see `ansible-recipes/converge-k8s-kubeconfig-ca/README.md`.

### restart-k8s

Path: `ansible-recipes/restart-k8s/playbook.yml`

For recipe-specific details, see `ansible-recipes/restart-k8s/README.md`.

### verify-system-kubeconfig

Path: `ansible-recipes/verify-system-kubeconfig/playbook.yml`

For recipe-specific details, see `ansible-recipes/verify-system-kubeconfig/README.md`.

### renew-etcd-files

Path: `ansible-recipes/renew-etcd-files/playbook.yml`

For recipe-specific details, see `ansible-recipes/renew-etcd-files/README.md`.

### rotate-k8s-files

Path: `ansible-recipes/rotate-k8s-files/playbook.yml`

For recipe-specific details, see `ansible-recipes/rotate-k8s-files/README.md`.
