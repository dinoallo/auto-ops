# 滚动重启 Kubernetes 控制平面 Pod

英文版：`README.md`

这个 recipe 通过 touch 静态 Pod manifest 文件，逐台 master 滚动重启 `kube-apiserver` 和 `kube-controller-manager`。它会记录重启前后的集群状态，方便操作者对比结果。

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 使用提权权限在 `masters` inventory 组中的主机上运行，每次处理一台主机。
2. 使用 `hostname` 读取目标节点名。
3. 重启前检查集群节点和选定的控制平面 Pod。
4. 使用带时间戳的后缀备份 `kube-apiserver.yaml` 和 `kube-controller-manager.yaml`。
5. touch kube-apiserver 静态 Pod manifest 以触发重启。
6. 等待该节点上的 kube-apiserver Pod 变为 Ready，并检查 `/readyz`。
7. touch kube-controller-manager 静态 Pod manifest 以触发重启。
8. 等待该节点上的 kube-controller-manager Pod 变为 Ready。
9. 重启后再次检查集群节点和选定的控制平面 Pod。

## 要求

- 使用静态 Pod manifest 的 kubeadm 管理 Kubernetes 控制平面
- inventory 中存在名为 `masters` 的主机组
- 每台目标主机上可以使用 `kubectl`
- `/etc/kubernetes/admin.conf` 是可用 kubeconfig，除非覆盖 `kubeconfig`
- 静态 Pod manifest 位于 `/etc/kubernetes/manifests`，除非覆盖 `manifest_dir`
- 具备 SSH 连接和提权权限，因为 manifest 文件通常归 root 所有

当 kubeadm 默认路径符合你的环境时，不需要额外变量。

## 可选变量

- `kubeconfig`: readiness 检查使用的 kubeconfig，默认 `'/etc/kubernetes/admin.conf'`
- `manifest_dir`: 静态 Pod manifest 目录，默认 `'/etc/kubernetes/manifests'`
- `backup_suffix`: manifest 备份使用的后缀，默认当前 Ansible 时间戳加 `.bak`

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/restart-k8s/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/restart-k8s/playbook.yml
```

使用自定义 kubeconfig：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/restart-k8s/playbook.yml \
  -e kubeconfig=/etc/kubernetes/admin.conf
```

指定 SSH key 运行：

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/restart-k8s/playbook.yml
```

## 重要警告

- 这个 recipe 会重启控制平面静态 Pod。只能在批准的维护窗口或经过测试的轮换流程中执行。
- 它不会重启 scheduler、etcd、kubelet 或 worker workload。
- 执行前确认集群能够承受每次一台控制平面节点重启。
- 依赖回滚前，请确认 manifest 备份已经生成。
- 如果 Ready 或 `/readyz` 检查失败，应先排查，再继续后续轮换步骤。
