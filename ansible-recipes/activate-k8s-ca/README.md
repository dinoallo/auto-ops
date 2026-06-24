# Activating a Staged Kubernetes Root CA

Chinese version: `README.zh-CN.md`

This recipe converges a kubeadm-style Kubernetes control plane from root CA compatibility mode to new-only root CA material. It promotes staged `ca-new-<renewal_id>.*` files, rewrites kube-apiserver and kube-controller-manager static pod manifests, and can activate previously generated `*-new-<renewal_id>.conf` kubeconfigs.

## What This Recipe Does

1. Verifies kubelet client certificates and kubelet trust before final activation by default.
2. Verifies active and staged root CA files.
3. Optionally verifies staged API server leaf certificates and staged kubeconfigs.
4. Backs up static pod manifests and active kubeconfigs.
5. Promotes `ca-new-<renewal_id>.crt` and `ca-new-<renewal_id>.key` to `ca.crt` and `ca.key`.
6. Rewrites kube-apiserver and kube-controller-manager manifests to new-only root CA paths.
7. Optionally touches and waits for kube-apiserver, kube-controller-manager, and kube-scheduler static Pods.

## Requirements

- Active files under `/etc/kubernetes/pki`: `ca.crt` and `ca.key`
- Staged files under `/etc/kubernetes/pki`: `ca-new-<renewal_id>.crt` and `ca-new-<renewal_id>.key`
- Kubelets already renewed with `renew-k8s-kubelet-certs`, so their client certificates are signed by `ca-new-<renewal_id>.crt` and their kubelet.conf trust includes the staged new root CA
- Python 3, `openssl`, `grep`, and `kubectl` available on target hosts
- SSH access with privilege escalation

Run this only after the compatibility phase has succeeded: API servers must already trust `ca-bundle-<renewal_id>.crt`, and kubelets must already use new-root-CA-signed client certificates.

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/activate-k8s-ca/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-k8s-ca/playbook.yml \
  -e renewal_id=${RENEWAL_ID} \
  -e restart_static_pods=true
```

To promote only the root CA files plus new-only CA manifest arguments, without switching API server leaf certs or kubeconfigs:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-k8s-ca/playbook.yml \
  -e renewal_id=${RENEWAL_ID} \
  -e activate_leaf_certs=false \
  -e activate_kubeconfigs=false \
  -e restart_static_pods=true
```

## Important Warnings

- This recipe moves root CA private key material. Protect target hosts, logs, and backups accordingly.
- Removing old `ca.crt` from kube-apiserver client CA trust can break kubelets unless their client certificates have already been signed by the new root CA.
- ServiceAccount signing keys are activated with the separate `activate-service-account-keys` recipe.
- Backups are written outside the static pod manifest directory so kubelet does not treat backups as pod manifests.
