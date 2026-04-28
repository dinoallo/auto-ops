# Rotating Kubernetes CA and Certificates

Chinese version: `README.zh-CN.md`

This recipe rotates Kubernetes control-plane CA material on a kubeadm-managed cluster, regenerates related certificates and kubeconfig files on master nodes, and rejoins worker nodes to the cluster.

## Files

- `playbook.yml`: the recipe playbook

## What This Recipe Does

1. Back up `/etc/kubernetes` on all master nodes.
2. On the first master node, remove old kubeconfig paths and selected PKI files, then generate a new CA, component certificates, and kubeconfig files.
3. Fetch shared CA files to the Ansible control node.
4. Copy those CA files to the remaining master nodes, remove stale kubeconfig paths there, and generate node-specific certificates and kubeconfig files.
5. Remove old master kubelet client certificate files, then restart `kubelet` and force-remove static control plane containers so the components restart with the new certificates.
6. Refresh bootstrap discovery data so `cluster-info` uses the rotated CA, then create a new `kubeadm join` command.
7. Wait for master kubelets to obtain fresh client certificates and finalize kubelet client certificate rotation.
8. Reset worker nodes and rejoin them to the cluster.
9. Remove temporary CA files from the control node.

## Requirements

- A kubeadm-managed Kubernetes cluster
- Static control plane pods under `/etc/kubernetes/manifests`
- `kubeadm`, `kubelet`, and `crictl` available on the target hosts
- SSH access with privilege escalation on all target hosts
- Inventory groups named `masters`, `master_first`, `master_rest`, and `workers`
- Exactly one host in `master_first`

No extra variables are required by this recipe.

Example inventory layout:

```ini
[masters]
cp1
cp2
cp3

[master_first]
cp1

[master_rest]
cp2
cp3

[workers]
worker1
worker2
```

## Usage

```bash
ansible-playbook --syntax-check ansible-recipes/rotate-k8s-files/playbook.yml
ansible-playbook -i inventory.ini ansible-recipes/rotate-k8s-files/playbook.yml
```

To run with a specific SSH key:

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/rotate-k8s-files/playbook.yml
```

To skip SSH host verification for this run:

```bash
ANSIBLE_HOST_KEY_CHECKING=False \
ansible-playbook -i inventory.ini ansible-recipes/rotate-k8s-files/playbook.yml
```

## Important Warnings

- This recipe is disruptive and rotates cluster CA material.
- Worker nodes are reset with `kubeadm reset -f`.
- Run it only on a non-production or fully recoverable cluster first.
- Verify that your `/etc/kubernetes` backups are usable before relying on this workflow.
- The recipe force-removes `/etc/kubernetes/*.conf` paths before regenerating kubeconfig, including stale directories left by a partial run.
- The recipe refreshes bootstrap discovery metadata before creating worker join commands so `kube-public/cluster-info` matches the rotated CA.
- The recipe also removes stale `/var/lib/kubelet/pki/kubelet-client*` files on master nodes and finalizes kubelet client certificate rotation so control-plane kubelets do not continue using the old CA.
- If your control plane uses Docker instead of containerd, replace the `crictl` command in the playbook.
