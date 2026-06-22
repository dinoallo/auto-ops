# Renewing Kubelet Root-CA-Signed Client Certificates

Chinese version: `README.zh-CN.md`

This recipe renews kubelet client certificates with a staged new Kubernetes root CA and rewrites kubelet API server trust. It covers both control-plane and worker nodes, which is required before converging kube-apiserver `--client-ca-file` to a new-only root CA.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Reads `ca-new-<renewal_id>.crt`, `ca-new-<renewal_id>.key`, and `ca-bundle-<renewal_id>.crt` from the source control-plane host.
2. Runs on `masters:workers` by default, one node at a time.
3. Installs `ca-new-<renewal_id>.crt` and `ca-bundle-<renewal_id>.crt` on each kubelet node.
4. Generates a kubelet client key and CSR for `system:node:<node-name>`.
5. Signs the kubelet client certificate with `ca-new-<renewal_id>.crt/key` on the source control-plane host.
6. Replaces `kubelet-client-current.pem` with a symlink to the new cert/key PEM.
7. Rewrites `/etc/kubernetes/kubelet.conf` to embed either `ca-bundle-<renewal_id>.crt` or `ca-new-<renewal_id>.crt`.
8. Restarts kubelet and waits for the Kubernetes node to be `Ready`.

## Requirements

- Inventory groups named `masters` and `workers`, unless `target_hosts` is overridden
- Staged root CA files on the source control-plane host: `ca-new-<renewal_id>.crt`, `ca-new-<renewal_id>.key`, and `ca-bundle-<renewal_id>.crt`
- Kubelet configuration at `/etc/kubernetes/kubelet.conf`
- Kubelet client certificate symlink at `/var/lib/kubelet/pki/kubelet-client-current.pem`
- `openssl`, `python3`, `systemctl`, and `kubectl` available on target hosts
- SSH access with privilege escalation

## Optional Variables

- `target_hosts`: kubelet nodes to update, defaults to `masters:workers`
- `k8s_ca_source_host`: source control-plane host for staged CA material, defaults to the first host in `masters`
- `kubelet_ca_rollout_serial`: number of nodes to update at a time, defaults to `1`
- `pki_dir`: Kubernetes PKI directory, defaults to `'/etc/kubernetes/pki'`
- `renewal_id`: date or date-like ID for staged root CA file names, defaults to `YYYYMMDD`
- `kubelet_conf`: kubelet kubeconfig, defaults to `'/etc/kubernetes/kubelet.conf'`
- `kubelet_pki_dir`: kubelet PKI directory, defaults to `'/var/lib/kubelet/pki'`
- `kubelet_trust_mode`: `bundle` or `new`, defaults to `bundle`
- `promote_kubelet_ca`: whether to replace node-local `pki_dir/ca.crt` with `ca-new-<renewal_id>.crt`, defaults to `false`
- `renew_kubelet_client_cert`: whether to create a new kubelet client certificate, defaults to `true`
- `restart_kubelet`: whether to restart kubelet after rewriting files, defaults to `true`
- `wait_kubelet_node_ready`: whether to wait for node readiness, defaults to `restart_kubelet`
- `kubeconfig`: kubeconfig used for node readiness checks, defaults to `'/etc/kubernetes/admin.conf'`

## Usage

During the compatibility phase, keep kubelet trusting both old and new CA certificates:

```bash
ansible-playbook --syntax-check ansible-recipes/renew-k8s-kubelet-certs/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-k8s-kubelet-certs/playbook.yml \
  -e kubelet_trust_mode=bundle
```

After kube-apiserver has converged to new-only root CA, remove old CA trust from kubelet and promote the node-local CA file:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-k8s-kubelet-certs/playbook.yml \
  -e kubelet_trust_mode=new \
  -e promote_kubelet_ca=true \
  -e renew_kubelet_client_cert=false
```

## Important Warnings

- This recipe handles kubelet private keys and root CA private key material on the source host. Protect target hosts and logs accordingly.
- Run this before final root CA activation. Removing the old apiserver client CA while kubelets still present old-CA-signed client certificates can break node authentication.
- Keep `kubelet_trust_mode=bundle` until kube-apiserver is ready with new-only serving and client CA material.
- Test the full rotation and rollback procedure on a non-production or fully recoverable cluster.
