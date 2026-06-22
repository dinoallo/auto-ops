# 证书轮换后验证系统 kubeconfig

英文版：`README.md`

这个 recipe 用于在证书轮换后验证选定的 Kubernetes kubeconfig 是否能访问 API server readiness endpoint。

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 使用提权权限在 `masters` inventory 组中的主机上运行。
2. 使用 `/etc/kubernetes/admin.conf` 检查 `/readyz`。
3. 使用 `/etc/kubernetes/controller-manager.conf` 检查 `/readyz`。
4. 使用 `/etc/kubernetes/scheduler.conf` 检查 `/readyz`。

## 要求

- Kubernetes 控制平面，并且每台目标主机上可以使用 `kubectl`
- inventory 中存在名为 `masters` 的主机组
- 目标 kubeconfig 文件存在于 `/etc/kubernetes`
- 每台目标主机可以访问 API server
- 如果 kubeconfig 文件归 root 所有，需要 SSH 连接和提权权限

当前 playbook 不需要额外变量。

## 可选变量

- `kubectl_retries`: API server 检查的重试次数，默认 `12`
- `kubectl_delay`: API server 检查每次重试之间的秒数，默认 `10`

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/verify-system-kubeconfig/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/verify-system-kubeconfig/playbook.yml
```

指定 SSH key 运行：

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/verify-system-kubeconfig/playbook.yml
```

## 重要警告

- 从集群视角看，这个 recipe 是只读检查，但它依赖的 kubeconfig 可能包含敏感客户端凭据。
- playbook 会重试 `/readyz` 检查，避免 static Pod 重启窗口造成误判。
- `/readyz` 成功只能确认基本 API 可达性，不能完整证明 controller 或 scheduler 行为正常。
- 如果证书轮换后任一检查失败，应先检查 kubeconfig 中的 CA 数据、客户端证书和 API server 可用性，再继续后续步骤。
