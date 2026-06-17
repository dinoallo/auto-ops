# 审计 ServiceAccount Token 退出状态

英文版：`README.md`

这个 recipe 用于 Kubernetes root CA 和 ServiceAccount 签名 key 轮转时，在移除旧 ServiceAccount 公钥前检查 token 阻塞项。它始终支持 legacy `kubernetes.io/service-account-token` Secret 引用检查；当传入 `sa_key_cutover` 时，还会扫描 kubelet 上的 projected token 文件。

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 默认在第一台 master 上执行 API 侧检查。
2. 通过 `kubectl` 读取所有 Secret 和 Pod。
3. 查找 legacy `kubernetes.io/service-account-token` Secret。
4. 如果任一 Pod 通过 volume、`env` 或 `envFrom` 引用这类 Secret，则失败。
5. 设置 `sa_key_cutover` 时，生成当前存活 Pod UID 映射，并在 `masters:workers` 上扫描 kubelet projected token 文件。
6. 如果 projected token 的 `iat` 早于 `sa_key_cutover`，则失败。
7. 默认在启用 projected 审计时，也会检查 token 旁边的 projected `ca.crt` 是否包含配置的新 CA 文件。

## 要求

- 可用 kubeconfig，默认 `/etc/kubernetes/admin.conf`
- projected token 审计需要 inventory 中存在 `masters` 和 `workers` 组
- API 审计源主机上有 `kubectl` 和 Python 3
- projected token 审计时，kubelet 节点上有 Python 3
- 具备跨命名空间列出 Pod 和 Secret 的权限
- 启用 projected token 审计时，需要 kubelet 节点 root 权限，因为 token 文件在 `/var/lib/kubelet/pods` 下

## 可选变量

- `audit_source_host`: API 读取使用的主机，默认 `masters` 中第一台
- `kubelet_target_hosts`: 要扫描的 kubelet 节点，默认 `masters:workers`
- `kubeconfig`: API 审计使用的 kubeconfig，默认 `'/etc/kubernetes/admin.conf'`
- `audit_legacy_service_account_tokens`: 是否检查 legacy token Secret 引用，默认 `true`
- `audit_projected_service_account_tokens`: 是否检查 projected token 文件，默认在设置 `sa_key_cutover` 时启用
- `sa_key_cutover`: kube-apiserver 切到 `sa-new.key` 的 RFC3339 时间戳
- `new_ca_file`: projected `ca.crt` 中应包含的新 root CA 文件，默认 `'/etc/kubernetes/pki/ca-new.crt'`
- `audit_projected_ca_bundle`: 是否检查 projected `ca.crt` 包含 `new_ca_file`，默认跟随 projected 审计状态
- `kubelet_pods_dir`: kubelet pod 目录，默认 `'/var/lib/kubelet/pods'`
- `python_interpreter`: 目标主机上使用的 Python 解释器，默认 `'/usr/bin/python3'`
- `kubectl_command`: kubectl 命令路径，默认 `kubectl`

## 用法

只检查 legacy Secret 引用：

```bash
ansible-playbook --syntax-check ansible-recipes/audit-service-account-token-retirement/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/audit-service-account-token-retirement/playbook.yml
```

ServiceAccount signer 切换后，检查 projected token 和 projected CA：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/audit-service-account-token-retirement/playbook.yml \
  -e sa_key_cutover=2026-06-17T09:30:00Z \
  -e new_ca_file=/etc/kubernetes/pki/ca-new.crt
```

## 重要警告

- 如果仍有 legacy token Secret 被引用，不要移除旧 `sa.pub`。
- 如果 projected token 是在 `sa_key_cutover` 之前签发的，需要重启或等待相关 Pod 后再移除旧 `sa.pub`。
- 这个 playbook 只检查 API server 当前仍存在的存活 Pod，并忽略 kubelet 目录中 API 已不存在 UID 的历史残留。
