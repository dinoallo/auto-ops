# Configuring Kubernetes Root CA Bundle Arguments

Chinese version: `README.zh-CN.md`

This recipe updates kubeadm-style kube-apiserver and kube-controller-manager static pod manifests to use the Kubernetes root CA bundle during root CA rotation.

By default, it configures kube-apiserver with:

```text
--client-ca-file=/etc/kubernetes/pki/ca-bundle-<renewal_id>.crt
```

It configures kube-controller-manager with:

```text
--root-ca-file=/etc/kubernetes/pki/ca-bundle-<renewal_id>.crt
--cluster-signing-cert-file=/etc/kubernetes/pki/ca.crt
--cluster-signing-key-file=/etc/kubernetes/pki/ca.key
```

To cut future certificate signing to the staged root CA, pass `ca_cert_path` and `ca_key_path` pointing to `ca-new-<renewal_id>.*`.

## Usage

Compatibility phase, old signer still active:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-k8s-ca-bundle/playbook.yml \
  -e renewal_id=${RENEWAL_ID} \
  -e restart_static_pods=true
```

Certificate signer cutover, keep bundle trust compatible:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-k8s-ca-bundle/playbook.yml \
  -e renewal_id=${RENEWAL_ID} \
  -e ca_cert_path=/etc/kubernetes/pki/ca-new-${RENEWAL_ID}.crt \
  -e ca_key_path=/etc/kubernetes/pki/ca-new-${RENEWAL_ID}.key \
  -e restart_static_pods=true
```

## Important Warnings

- This recipe changes control-plane static pod manifests. Test it on a non-production or fully recoverable cluster before relying on it.
- Back up Kubernetes PKI files before changing root CA trust settings.
- Ensure the CA bundle contains every root CA required during your rotation window.
- ServiceAccount signing keys are configured with the separate `configure-service-account-keys` recipe.
