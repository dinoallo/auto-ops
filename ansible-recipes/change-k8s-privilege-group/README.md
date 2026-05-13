# Changing the Kubernetes Privileged Group

Chinese version: `README.zh-CN.md`

This recipe copies a patched `kubeadm` binary from the Ansible control node to Kubernetes control plane nodes, renews selected certificates with a new organization group, updates the kube-apiserver static pod manifest, and removes `system:masters` from the chosen ClusterRoleBinding.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Ensures the run targets at least one control plane node.
2. Verifies that the patched `kubeadm` binary exists on the Ansible control node.
3. Chooses one effective privileged group value for the whole run.
4. Copies that binary to each target control plane node and makes it executable.
5. Backs up `admin.conf`, `/root/.kube/config` when present, the kube-apiserver manifest, and the `apiserver-kubelet-client` certificate files when present on each target node.
6. Uses the patched `kubeadm` binary to renew `admin.conf` and `apiserver-kubelet-client` with the same target privileged group on each node, and can optionally pass a user-provided kubeadm configuration file via `--config`.
7. Updates `/root/.kube/config` from the renewed `admin.conf` on each node.
8. Sets `--system-privileged-group` in each kube-apiserver static pod manifest and updates the kube-apiserver image.
9. Waits for `kubectl get --raw=/healthz` to succeed again on each node.
10. On the first target host only, backs up the current ClusterRoleBinding JSON and removes `system:masters` from its subjects when present.

## Requirements

- One or more target hosts per run
- Kubeadm-managed control plane nodes with a static kube-apiserver manifest
- A patched `kubeadm` binary on the Ansible control node that supports `certs renew ... --org=...`
- If you provide a kubeadm configuration file, it must match the kubeadm and Kubernetes versions on the target hosts
- `kubectl` available on the target host
- SSH access and privilege escalation on the target host

## Required Variables

- `patched_kubeadm_src`: local path on the Ansible control node to the patched `kubeadm` binary
- `kube_apiserver_image`: replacement kube-apiserver image reference, for example `repo.example/kube-apiserver:tag`

## Optional Variables

- `target_hosts`: target control plane host group, defaults to `all`
- `system_privileged_group`: privileged group to write into renewed certificates and the kube-apiserver manifest, defaults to a generated value like `system:admin-abc123def456`
- `patched_kubeadm_dest`: remote path for the copied patched `kubeadm` binary, defaults to `'/tmp/kubeadm-patched'`
- `kubeadm_configuration_src`: local path on the Ansible control node to an optional kubeadm configuration file for renew commands, disabled by default
- `kubeadm_configuration_dest`: remote path used to stage `kubeadm_configuration_src`, defaults to `'/etc/kubernetes/kubeadm-privilege-group-config.yaml'`
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
  -e target_hosts=masters \
  -e patched_kubeadm_src=./bin/kubeadm-patched \
  -e kube_apiserver_image=dinoallo/kube-apiserver:045f369
```

To use a fixed privileged group instead of a generated one:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/change-k8s-privilege-group/playbook.yml \
  -e target_hosts=masters \
  -e patched_kubeadm_src=./bin/kubeadm-patched \
  -e kube_apiserver_image=dinoallo/kube-apiserver:045f369 \
  -e system_privileged_group=system:admin-custom
```

To pass a kubeadm configuration file to both renew commands:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/change-k8s-privilege-group/playbook.yml \
  -e target_hosts=masters \
  -e patched_kubeadm_src=./bin/kubeadm-patched \
  -e kube_apiserver_image=dinoallo/kube-apiserver:045f369 \
  -e kubeadm_configuration_src=./kubeadm-privilege-group-config.yaml
```

To customize where that configuration file is stored on target nodes:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/change-k8s-privilege-group/playbook.yml \
  -e target_hosts=masters \
  -e patched_kubeadm_src=./bin/kubeadm-patched \
  -e kube_apiserver_image=dinoallo/kube-apiserver:045f369 \
  -e kubeadm_configuration_src=./kubeadm-privilege-group-config.yaml \
  -e kubeadm_configuration_dest=/etc/kubernetes/kubeadm-custom-renew-config.yaml
```

To run with a specific SSH key:

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/change-k8s-privilege-group/playbook.yml \
  -e target_hosts=masters \
  -e patched_kubeadm_src=./bin/kubeadm-patched \
  -e kube_apiserver_image=dinoallo/kube-apiserver:045f369
```

## Important Warnings

- This recipe is highly disruptive and can remove your current cluster-admin access if used incorrectly.
- The recipe runs with `serial: 1`, so control plane nodes are changed one by one.
- The ClusterRoleBinding patch step runs on the first selected target host only.
- If `system:masters` is the only subject in the patched ClusterRoleBinding, this recipe leaves that binding with an empty `subjects` list.
- Any provided kubeadm configuration file is passed directly to renew commands with `--config`; validate it on a non-production cluster first.
- Run it only on a non-production or fully recoverable cluster first.
- Verify the generated backup files before relying on this workflow as a rollback path.
