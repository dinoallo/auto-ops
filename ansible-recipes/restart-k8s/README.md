# Rolling Restart of Kubernetes Control Plane Pods

Chinese version: `README.zh-CN.md`

This recipe rolls `kube-apiserver` and `kube-controller-manager` static pods one master node at a time by touching their manifest files. It captures pre- and post-restart cluster state so the operator can compare the result.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Runs on hosts in the `masters` inventory group with privilege escalation, one host at a time.
2. Reads the target node name with `hostname`.
3. Checks cluster nodes and selected control-plane pods before restarting.
4. Backs up `kube-apiserver.yaml` and `kube-controller-manager.yaml` with a timestamped suffix.
5. Touches the kube-apiserver static pod manifest to trigger a restart.
6. Waits for the kube-apiserver pod on that node to become Ready and checks `/readyz`.
7. Touches the kube-controller-manager static pod manifest to trigger a restart.
8. Waits for the kube-controller-manager pod on that node to become Ready.
9. Checks cluster nodes and selected control-plane pods after the restart.

## Requirements

- A kubeadm-managed Kubernetes control plane using static pod manifests
- Inventory group named `masters`
- `kubectl` available on each target host
- A working kubeconfig at `/etc/kubernetes/admin.conf`, unless `kubeconfig` is overridden
- Static pod manifests under `/etc/kubernetes/manifests`, unless `manifest_dir` is overridden
- SSH access with privilege escalation, because manifest files are normally root-owned

No extra variables are required when the kubeadm defaults match your environment.

## Optional Variables

- `kubeconfig`: kubeconfig used for readiness checks, defaults to `'/etc/kubernetes/admin.conf'`
- `manifest_dir`: static pod manifest directory, defaults to `'/etc/kubernetes/manifests'`
- `backup_suffix`: suffix used for manifest backups, defaults to the current Ansible timestamp plus `.bak`

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/restart-k8s/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/restart-k8s/playbook.yml
```

To use a custom kubeconfig:

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/restart-k8s/playbook.yml \
  -e kubeconfig=/etc/kubernetes/admin.conf
```

To run with a specific SSH key:

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/restart-k8s/playbook.yml
```

## Important Warnings

- This recipe restarts control-plane static pods. Run it only during an approved maintenance window or tested rotation workflow.
- It does not restart the scheduler, etcd, kubelet, or worker workloads.
- Ensure the cluster can tolerate one control-plane node restarting at a time.
- Verify that the manifest backups are present before relying on rollback.
- Investigate any failed Ready or `/readyz` checks before continuing with later rotation steps.
