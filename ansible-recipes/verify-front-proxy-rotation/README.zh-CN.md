# 验证 front-proxy 轮换

英文版：`README.md`

这个 recipe 用于在 front-proxy 证书轮换后验证 Kubernetes aggregation API 行为。它会检查 aggregation authentication ConfigMap，列出已注册的 APIService，并在集群已安装 metrics APIService 时查询 metrics API raw endpoint。

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 使用提权权限在 `masters` inventory 组中的主机上运行。
2. 读取 `kube-system` 命名空间里的 `extension-apiserver-authentication` ConfigMap。
3. 列出 APIService 对象。
4. 检查是否安装了 metrics APIService。
5. 当 metrics API 已安装或 `require_metrics_api=true` 时，通过 API server 查询 `/apis/metrics.k8s.io/v1beta1`。
6. 打印 APIService 输出、metrics API 响应或跳过原因。

## 要求

- Kubernetes 控制平面，并且每台目标主机上可以使用 `kubectl`
- inventory 中存在名为 `masters` 的主机组
- `/etc/kubernetes/admin.conf` 是可用 kubeconfig，除非覆盖 `kubeconfig`
- 集群中已经配置 API aggregation
- 只有在要求 metrics endpoint 检查时，集群才需要安装 metrics API
- 如果 kubeconfig 文件归 root 所有，需要 SSH 连接和提权权限

当 kubeadm 默认 kubeconfig 路径符合你的环境时，不需要额外变量。

## 可选变量

- `kubeconfig`: 验证使用的 kubeconfig，默认 `'/etc/kubernetes/admin.conf'`
- `metrics_apiservice_name`: 要探测的 APIService 名称，默认 `'v1beta1.metrics.k8s.io'`
- `metrics_raw_endpoint`: 要查询的 metrics API raw 路径，默认 `'/apis/metrics.k8s.io/v1beta1'`
- `require_metrics_api`: metrics APIService 未安装时是否失败，默认 `false`
- `kubectl_retries`: API server 检查的重试次数，默认 `12`
- `kubectl_delay`: API server 检查每次重试之间的秒数，默认 `10`

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

要求执行 metrics API endpoint 检查：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/verify-front-proxy-rotation/playbook.yml \
  -e require_metrics_api=true
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
- playbook 会重试 kubectl 检查，避免 static Pod 重启窗口造成误判。
- metrics API raw endpoint 检查只会在 metrics API 已安装或 `require_metrics_api=true` 时运行。
- 检查成功只能确认基本 aggregation API 可达性，不能证明所有 aggregated API 实现都正常。
- 如果 front-proxy 轮换后检查失败，应先检查 front-proxy CA bundle、front-proxy client 证书、APIService conditions 和 kube-apiserver 日志，再继续后续步骤。
