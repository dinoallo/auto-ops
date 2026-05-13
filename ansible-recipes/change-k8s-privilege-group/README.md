# Changing the Kubernetes Privileged Group

Chinese version: `README.zh-CN.md`

This recipe copies a patched `kubeadm` binary from the Ansible control node to one Kubernetes control plane node, renews selected certificates with a new organization group, updates the kube-apiserver static pod manifest, and removes `system:masters` from the chosen ClusterRoleBinding.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Ensures the run targets exactly one control plane node.
2. Verifies that the patched `kubeadm` binary exists on the Ansible control node.
3. Copies that binary to the remote node and makes it executable.
4. Backs up `admin.conf`, `/root/.kube/config` when present, the kube-apiserver manifest, and the `apiserver-kubelet-client` certificate files when present.
5. Uses the patched `kubeadm` binary to renew `admin.conf` and `apiserver-kubelet-client` with the target privileged group as the certificate organization, and can optionally pass a user-specified certificate validity period.
6. Updates `/root/.kube/config` from the renewed `admin.conf`.
7. Sets `--system-privileged-group` in the kube-apiserver static pod manifest and updates the kube-apiserver image.
8. Waits for `kubectl get --raw=/healthz` to succeed again.
9. Backs up the current ClusterRoleBinding JSON and removes `system:masters` from its subjects when present.

## Requirements

- Exactly one target host per run
- A kubeadm-managed control plane node with a static kube-apiserver manifest
- A patched `kubeadm` binary on the Ansible control node that supports `certs renew ... --org=...`
- If you set a custom certificate validity period, the patched `kubeadm` must also support the corresponding renew flag
- `kubectl` available on the target host
- SSH access and privilege escalation on the target host

## Required Variables

- `patched_kubeadm_src`: local path on the Ansible control node to the patched `kubeadm` binary
- `kube_apiserver_image`: replacement kube-apiserver image reference, for example `repo.example/kube-apiserver:tag`

## Optional Variables

- `target_hosts`: target host group, defaults to `all`
- `system_privileged_group`: privileged group to write into renewed certificates and the kube-apiserver manifest, defaults to a generated value like `system:admin-abc123def456`
- `patched_kubeadm_dest`: remote path for the copied patched `kubeadm` binary, defaults to `'/tmp/kubeadm-patched'`
- `kubeadm_cert_validity_period`: certificate validity period passed to both `certs renew` commands, disabled by default
- `kubeadm_cert_validity_period_flag`: flag name used with `kubeadm_cert_validity_period`, defaults to `'--certificate-validity-period'`
- `kube_apiserver_manifest_path`: kube-apiserver manifest path, defaults to `'/etc/kubernetes/manifests/kube-apiserver.yaml'`
- `admin_conf_path`: admin kubeconfig path, defaults to `'/etc/kubernetes/admin.conf'`
- `root_kube_config_path`: root kubeconfig path, defaults to `'/root/.kube/config'`
- `pki_dir`: Kubernetes PKI directory, defaults to `'/etc/kubernetes/pki'`
- `kubectl_command`: kubectl command path or name, defaults to `'kubectl'`
- `clusterrolebinding_name`: ClusterRoleBinding to patch, defaults to `'cluster-admin'`
- `initial_restart_wait_seconds`: fixed wait after editing the kube-apiserver manifest, defaults to `30`
- `healthcheck_retries`: retry count for the post-change API server health check, defaults to `20`
- `healthcheck_delay`: seconds between health check retries, defaults to `5`

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/change-k8s-privilege-group/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/change-k8s-privilege-group/playbook.yml \
  -e target_hosts=cp1 \
  -e patched_kubeadm_src=./bin/kubeadm-patched \
  -e kube_apiserver_image=dinoallo/kube-apiserver:045f369
```

To use a fixed privileged group instead of a generated one:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/change-k8s-privilege-group/playbook.yml \
  -e target_hosts=cp1 \
  -e patched_kubeadm_src=./bin/kubeadm-patched \
  -e kube_apiserver_image=dinoallo/kube-apiserver:045f369 \
  -e system_privileged_group=system:admin-custom
```

To pass a custom certificate validity period to the renew commands:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/change-k8s-privilege-group/playbook.yml \
  -e target_hosts=cp1 \
  -e patched_kubeadm_src=./bin/kubeadm-patched \
  -e kube_apiserver_image=dinoallo/kube-apiserver:045f369 \
  -e kubeadm_cert_validity_period=8760h
```

If your patched `kubeadm` uses a different flag name for the validity period, override it explicitly:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/change-k8s-privilege-group/playbook.yml \
  -e target_hosts=cp1 \
  -e patched_kubeadm_src=./bin/kubeadm-patched \
  -e kube_apiserver_image=dinoallo/kube-apiserver:045f369 \
  -e kubeadm_cert_validity_period=8760h \
  -e kubeadm_cert_validity_period_flag=--validity-period
```

To run with a specific SSH key:

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/change-k8s-privilege-group/playbook.yml \
  -e target_hosts=cp1 \
  -e patched_kubeadm_src=./bin/kubeadm-patched \
  -e kube_apiserver_image=dinoallo/kube-apiserver:045f369
```

## Important Warnings

- This recipe is highly disruptive and can remove your current cluster-admin access if used incorrectly.
- The recipe currently targets exactly one control plane node. It does not propagate manifest or certificate changes to other control plane nodes in an HA cluster.
- If `system:masters` is the only subject in the patched ClusterRoleBinding, this recipe leaves that binding with an empty `subjects` list.
- The certificate validity period option only works when your patched `kubeadm` actually supports the chosen renew flag.
- Run it only on a non-production or fully recoverable cluster first.
- Verify the generated backup files before relying on this workflow as a rollback path.
