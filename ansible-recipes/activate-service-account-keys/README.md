# Activating a Staged Kubernetes ServiceAccount Key Pair

Chinese version: `README.zh-CN.md`

This recipe retires the old ServiceAccount public key and promotes staged `sa-new-<renewal_id>.pub` and `sa-new-<renewal_id>.key` to the canonical kubeadm filenames `sa.pub` and `sa.key`. It archives the previously active files before promotion and rewrites control-plane manifests to new-only ServiceAccount key paths.

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/activate-service-account-keys/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-service-account-keys/playbook.yml \
  -e renewal_id=${RENEWAL_ID} \
  -e sa_key_cutover=${CUTOVER} \
  -e restart_static_pods=true
```

## What This Recipe Does

1. Runs the ServiceAccount token retirement audit before removing the old public key.
2. Verifies active and staged ServiceAccount files.
3. Verifies the staged private key matches the staged public key.
4. Requires the compatibility manifest state by default: kube-apiserver trusts both public keys and signing already uses the staged private key.
5. Archives active `sa.pub` and `sa.key` under `/etc/kubernetes/pki/archive/service-account-<renewal_id>` by default.
6. Promotes the staged key pair to `sa.pub` and `sa.key`.
7. Rewrites kube-apiserver and kube-controller-manager manifests to the canonical new-only paths.
8. Optionally touches and waits for the restarted static Pods.

## Important Warnings

- Do not run this until old ServiceAccount tokens are retired. Removing old `sa.pub` can break still-running legacy or projected tokens.
- For ServiceAccount-only rotation, projected CA bundle auditing is disabled by default. Enable `activate_audit_projected_ca_bundle=true` only when this activation is coupled to root CA rotation.
- Backups are written outside the static pod manifest directory so kubelet does not treat backups as pod manifests.
