# Rotating Kubernetes CA and Certificates

英文版：`README.md`

这个 recipe 用于在 kubeadm 管理的 Kubernetes 集群里轮换控制平面的 CA 材料，重新生成相关证书和 kubeconfig，并让 worker 节点重新加入集群。

## 文件

- `playbook.yml`: recipe 主体

## 这个 Recipe 会做什么

1. 在所有 master 节点上备份 `/etc/kubernetes`。
2. 在第一台 master 上删除旧的 kubeconfig 路径和部分 PKI 文件，然后重新生成新的 CA、组件证书和 kubeconfig。
3. 把共享的 CA 文件拉取到 Ansible 控制机。
4. 将这些 CA 文件分发到其余 master 节点，清理那里的残留 kubeconfig 路径，再为每台节点生成它自己的组件证书和 kubeconfig。
5. 重启 `kubelet`，并强制删除控制平面的静态 Pod 容器，让组件用新证书重新启动。
6. 生成新的 `kubeadm join` 命令。
7. 对 worker 节点执行 reset，并重新加入集群。
8. 清理控制机上的临时 CA 文件。

## 前置要求

- 集群由 kubeadm 管理
- 控制平面使用 `/etc/kubernetes/manifests` 下的静态 Pod
- 目标主机上可用 `kubeadm`、`kubelet` 和 `crictl`
- Ansible 控制机可以通过 SSH 访问所有目标主机，并具备提权能力
- inventory 中存在 `masters`、`master_first`、`master_rest` 和 `workers` 这几个主机组
- `master_first` 中必须且只能有一台主机

这个 recipe 不需要额外传入变量。

inventory 示例：

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

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/rotate-k8s-files/playbook.yml
ansible-playbook -i inventory.ini ansible-recipes/rotate-k8s-files/playbook.yml
```

如果需要指定 SSH key：

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/rotate-k8s-files/playbook.yml
```

如果这次执行需要跳过 SSH 主机验证：

```bash
ANSIBLE_HOST_KEY_CHECKING=False \
ansible-playbook -i inventory.ini ansible-recipes/rotate-k8s-files/playbook.yml
```

## 重要提醒

- 这是一个有中断影响的 recipe，会轮换集群 CA 材料。
- worker 节点会执行 `kubeadm reset -f`。
- 应该先在非生产环境或可完整恢复的集群里验证。
- 运行前先确认 `/etc/kubernetes` 的备份可用，不要把这份 playbook 当成唯一回滚手段。
- recipe 在重新生成 kubeconfig 前会强制删除 `/etc/kubernetes/*.conf` 路径，包括上次中断执行遗留的同名目录。
- 如果控制平面运行在 Docker 而不是 containerd 上，需要把 playbook 里的 `crictl` 命令改成对应的 Docker 命令。
