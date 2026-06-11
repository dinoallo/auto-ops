# 验证 front-proxy 轮换

英文版：`README.md`

这个 recipe 用于在 front-proxy 证书轮换后验证 Kubernetes aggregation API 行为。它会检查 aggregation authentication ConfigMap，列出已注册的 APIService，并查询 metrics API raw endpoint。

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 使用提权权限在 `masters` inventory 组中的主机上运行。
2. 读取 `kube-system` 命名空间里的 `extension-apiserver-authentication` ConfigMap。
3. 列出 APIService 对象。
4. 通过 API server 查询 `/apis/metrics.k8s.io/v1beta1`。
5. 打印 APIService 输出和 metrics API 响应。

## 要求

- Kubernetes 控制平面，并且每台目标主机上可以使用 `kubectl`
- inventory 中存在名为 `masters` 的主机组
- `/etc/kubernetes/admin.conf` 是可用 kubeconfig，除非覆盖 `kubeconfig`
- 集群中已经配置 API aggregation
- 如果期望 metrics endpoint 检查通过，集群中需要安装 metrics API
- 如果 kubeconfig 文件归 root 所有，需要 SSH 连接和提权权限

当 kubeadm 默认 kubeconfig 路径符合你的环境时，不需要额外变量。

## 可选变量

- `kubeconfig`: 验证使用的 kubeconfig，默认 `'/etc/kubernetes/admin.conf'`

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/verify-front-proxy-rotation/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/verify-front-proxy-rotation/playbook.yml
```

使用自定义 kubeconfig：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/verify-front-proxy-rotation/playbook.yml \
  -e kubeconfig=/etc/kubernetes/admin.conf
```

指定 SSH key 运行：

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/verify-front-proxy-rotation/playbook.yml
```

## 重要警告

- 从集群视角看，这个 recipe 是只读检查，但它依赖的 kubeconfig 可能包含敏感客户端凭据。
- metrics API raw endpoint 检查要求集群已经安装并正常运行 metrics API。
- 检查成功只能确认基本 aggregation API 可达性，不能证明所有 aggregated API 实现都正常。
- 如果 front-proxy 轮换后检查失败，应先检查 front-proxy CA bundle、front-proxy client 证书、APIService conditions 和 kube-apiserver 日志，再继续后续步骤。
