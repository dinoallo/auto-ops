# Verifying Kubernetes Root CA Retirement

Chinese version: `README.zh-CN.md`

This recipe verifies whether a Kubernetes root CA rotation is ready to proceed or has fully converged to new-only trust. It is read-only and does not rewrite manifests, kubeconfigs, or PKI files.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Verifies kube-apiserver and kube-controller-manager static Pod manifest CA arguments.
2. Verifies API server leaf certificates are signed by the expected new root CA.
3. Verifies system kubeconfigs embed the expected CA data and can reach `/readyz`.
4. Verifies kubelet client certificates are signed by the expected new root CA.
5. Verifies kubelet kubeconfig CA data.
6. Verifies projected ServiceAccount `ca.crt` files on kubelet nodes.

## Modes

- `root_ca_retirement_phase=compat`: use before archive/promotion. The verifier expects bundle trust where appropriate and checks that new CA material is present.
- `root_ca_retirement_phase=new_only`: use after archive/promotion and convergence. The verifier expects exactly one embedded CA certificate and that the data equals the promoted new root CA.
- Projected ServiceAccount CA verification only checks currently `Running` Pods that are not already being deleted. It retries by default for up to 5 minutes (`projected_serviceaccount_ca_verify_retries=20`, `projected_serviceaccount_ca_verify_delay=15`) to allow kubelet projected volume refreshes to converge.

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/verify-k8s-root-ca-retirement/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/verify-k8s-root-ca-retirement/playbook.yml \
  -e renewal_id=${RENEWAL_ID} \
  -e root_ca_retirement_phase=compat

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/verify-k8s-root-ca-retirement/playbook.yml \
  -e root_ca_retirement_phase=new_only
```

## Important Warnings

- `compat` mode does not prove the old root CA has disappeared. It proves the cluster can already operate with the staged new root CA and compatibility trust.
- `new_only` mode is the old-CA retirement gate. It checks kubeconfigs, kubelet trust, projected ServiceAccount CA files, and static Pod manifest references for new-only state.
- External clients outside the cluster cannot be fully proven by this playbook; audit and restart or reconfigure them separately.
