# Configuring Kubernetes ServiceAccount Key Arguments

Chinese version: `README.zh-CN.md`

This recipe updates kubeadm-style kube-apiserver and kube-controller-manager static pod manifests for ServiceAccount signing key rotation. It can keep kube-apiserver trusting both the current and staged public keys while switching new token signing to the staged private key.

By default, it configures kube-apiserver with:

```text
--service-account-key-file=/etc/kubernetes/pki/sa.pub
--service-account-key-file=/etc/kubernetes/pki/sa-new-<renewal_id>.pub
--service-account-signing-key-file=/etc/kubernetes/pki/sa.key
```

It configures kube-controller-manager with:

```text
--service-account-private-key-file=/etc/kubernetes/pki/sa.key
```

To cut over new token signing, pass `service_account_signing_key_path` and `service_account_private_key_path` pointing to `sa-new-<renewal_id>.key`.

## Usage

Compatibility phase, old signer still active:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-service-account-keys/playbook.yml \
  -e renewal_id=${RENEWAL_ID} \
  -e restart_static_pods=true
```

Signer cutover, keep both public keys trusted:

```bash
CUTOVER=$(date -u +%Y-%m-%dT%H:%M:%SZ)

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-service-account-keys/playbook.yml \
  -e renewal_id=${RENEWAL_ID} \
  -e service_account_signing_key_path=/etc/kubernetes/pki/sa-new-${RENEWAL_ID}.key \
  -e service_account_private_key_path=/etc/kubernetes/pki/sa-new-${RENEWAL_ID}.key \
  -e restart_static_pods=true
```

Use the recorded `CUTOVER` value with `activate-service-account-keys`.

## Important Warnings

- Keep both old and new public keys trusted until legacy and projected ServiceAccount tokens issued before cutover are retired.
- Roll out one control-plane node at a time unless you have validated a broader rollout strategy.
