# Activating a Staged Kubernetes Root CA and ServiceAccount Key Pair

Chinese version: `README.zh-CN.md`

This recipe converges a kubeadm-style Kubernetes control plane from compatibility mode to new-only root CA and ServiceAccount signing material. It promotes staged `ca-new.*` and `sa-new.*` files, rewrites kube-apiserver and kube-controller-manager static pod manifests, and can activate previously generated `*-new.conf` kubeconfigs.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on control-plane hosts with privilege escalation, one host at a time by default.
2. Verifies active and staged root CA and ServiceAccount files.
3. Verifies the staged ServiceAccount private key matches the staged public key.
4. Optionally verifies staged API server leaf certificates and staged kubeconfigs.
5. By default, verifies every kubelet node already has a new-root-CA-signed kubelet client certificate and trusts the staged new root CA.
6. By default, runs the ServiceAccount token retirement audit before final activation, including legacy token Secret references and projected token issuance time / projected CA contents.
7. Backs up static pod manifests under `/etc/kubernetes/manifest-backups`.
8. Backs up active kubeconfigs under `/etc/kubernetes/kubeconfig-backups` when kubeconfig activation is enabled.
9. Promotes `ca-new.crt`, `ca-new.key`, `sa-new.pub`, and `sa-new.key` to the active filenames with timestamped backups.
10. Rewrites kube-apiserver to use new-only `ca.crt`, `sa.pub`, `sa.key`, and, by default, staged API server leaf certificates.
11. Rewrites kube-controller-manager to use new-only root CA and ServiceAccount private key paths.
12. Optionally touches and waits for kube-apiserver, kube-controller-manager, and kube-scheduler static pods.

## Requirements

- A kubeadm-managed Kubernetes control plane, or equivalent PKI layout
- Inventory group named `masters`, unless `target_hosts` is overridden
- Active files under `/etc/kubernetes/pki`: `ca.crt`, `ca.key`, `sa.pub`, and `sa.key`
- Staged files under `/etc/kubernetes/pki`: `ca-new.crt`, `ca-new.key`, `sa-new.pub`, and `sa-new.key`
- Staged API server leaf files when `activate_leaf_certs=true`: `apiserver-new.*` and `apiserver-kubelet-client-new.*`
- Staged kubeconfigs when `activate_kubeconfigs=true`: `admin-new.conf`, `controller-manager-new.conf`, and `scheduler-new.conf`
- Kubelets already renewed with `renew-k8s-kubelet-certs`, so their client certificates are signed by `ca-new.crt` and their kubelet.conf trust includes the staged new root CA
- `sa_key_cutover` set to the UTC timestamp captured immediately before the ServiceAccount signer was switched to `sa-new.key`, unless `activate_audit_projected_service_account_tokens=false`
- Python 3, `openssl`, `diff`, `mv`, and `kubectl` available on target hosts
- SSH access with privilege escalation

Run this only after the compatibility phase has succeeded: API servers must already trust `ca-bundle.crt` and both ServiceAccount public keys, kubelets must already use new-root-CA-signed client certificates, and old ServiceAccount tokens must be retired before old `sa.pub` is removed.

## Optional Variables

- `target_hosts`: target host group, defaults to `masters`
- `k8s_ca_activation_rollout_serial`: number of hosts to process at a time, defaults to `1`
- `manifest_dir`: static pod manifest directory, defaults to `'/etc/kubernetes/manifests'`
- `pki_dir`: Kubernetes PKI directory, defaults to `'/etc/kubernetes/pki'`
- `kube_dir`: Kubernetes configuration directory, defaults to `'/etc/kubernetes'`
- `manifest_backup_dir`: directory for manifest backups, defaults to `'/etc/kubernetes/manifest-backups'`
- `kubeconfig_backup_dir`: directory for kubeconfig backups, defaults to `kube_dir + '/kubeconfig-backups'`
- `backup_suffix`: backup suffix, defaults to the current Ansible timestamp plus `.bak`
- `activate_leaf_certs`: whether to switch kube-apiserver to `apiserver-new.*` and `apiserver-kubelet-client-new.*`, defaults to `true`
- `activate_kubeconfigs`: whether to replace `admin.conf`, `controller-manager.conf`, and `scheduler.conf` with staged `*-new.conf`, defaults to `true`
- `restart_static_pods`: whether to touch static pod manifests after convergence, defaults to `false`
- `wait_static_pods`: whether to wait for restarted static pods, defaults to `restart_static_pods`
- `kubeconfig`: kubeconfig used for readiness checks, defaults to `kube_dir + '/admin.conf'`
- `audit_service_account_token_retirement`: whether to run the pre-activation ServiceAccount token retirement audit, defaults to `true`
- `activate_audit_projected_service_account_tokens`: whether the pre-activation audit scans kubelet projected token files and projected CA files, defaults to `audit_service_account_token_retirement`
- `sa_key_cutover`: UTC timestamp captured before switching ServiceAccount token signing to `sa-new.key`; required when projected token auditing is enabled
- `new_ca_file`: staged new root CA file used to verify projected volume `ca.crt` contents, defaults to `'/etc/kubernetes/pki/ca-new.crt'`
- `verify_kubelet_root_ca_rollout`: whether to verify kubelet client certs and kubelet trust before final activation, defaults to `true`
- `kubelet_target_hosts`: kubelet node group used by the pre-activation verification, defaults to `masters:workers`
- `kubectl_command`: kubectl command path, defaults to `kubectl`
- `python_interpreter`: Python interpreter used on target hosts, defaults to `'/usr/bin/python3'`

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/activate-k8s-ca/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-k8s-ca/playbook.yml \
  -e sa_key_cutover=${CUTOVER} \
  -e restart_static_pods=true
```

To promote only the root CA and ServiceAccount files plus new-only CA/SA manifest arguments, without switching API server leaf certs or kubeconfigs:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-k8s-ca/playbook.yml \
  -e sa_key_cutover=${CUTOVER} \
  -e activate_leaf_certs=false \
  -e activate_kubeconfigs=false \
  -e restart_static_pods=true
```

## Important Warnings

- This recipe moves root CA private key material and ServiceAccount signing private key material. Protect target hosts, logs, and backups accordingly.
- Removing old `ca.crt` from kube-apiserver client CA trust can break kubelets unless their client certificates have already been signed by the new root CA.
- Removing old `sa.pub` can break still-running legacy or projected ServiceAccount tokens. Keep the default retirement audit enabled before this step.
- Backups are written outside the static pod manifest directory so kubelet does not treat backups as pod manifests.
- Test the full activation and rollback procedure on a non-production or fully recoverable cluster before relying on it.
