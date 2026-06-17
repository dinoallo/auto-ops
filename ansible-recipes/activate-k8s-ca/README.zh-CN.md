# 激活预置的 Kubernetes Root CA 和 ServiceAccount Key Pair

英文版：`README.md`

这个 recipe 会把 kubeadm 风格 Kubernetes 控制平面从兼容期收敛到 new-only root CA 和 ServiceAccount 签名材料。它会提升预置的 `ca-new.*` 和 `sa-new.*` 文件，重写 kube-apiserver 与 kube-controller-manager 静态 Pod manifest，并且可以激活前面生成的 `*-new.conf` kubeconfig。

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 使用提权权限在控制平面节点上运行，默认每次处理一台主机。
2. 检查当前和预置的 root CA、ServiceAccount 文件。
3. 校验预置 ServiceAccount 私钥与预置公钥匹配。
4. 按需检查预置 API server leaf 证书和预置 kubeconfig。
5. 默认检查所有 kubelet 节点已经使用新 root CA 签发的 kubelet client certificate，并且 kubelet.conf 已信任预置的新 root CA。
6. 默认在最终激活前执行 ServiceAccount token 退出审计，包括 legacy token Secret 引用、projected token 签发时间和 projected CA 内容。
7. 把静态 Pod manifest 备份到 `/etc/kubernetes/manifest-backups`。
8. 启用 kubeconfig 激活时，把当前 kubeconfig 备份到 `/etc/kubernetes/kubeconfig-backups`。
9. 将 `ca-new.crt`、`ca-new.key`、`sa-new.pub` 和 `sa-new.key` 提升为当前生效文件名，并给旧文件生成带时间戳的备份。
10. 将 kube-apiserver 收敛到 new-only `ca.crt`、`sa.pub`、`sa.key`，默认也切到预置 API server leaf 证书。
11. 将 kube-controller-manager 收敛到 new-only root CA 和 ServiceAccount 私钥路径。
12. 按需 touch 并等待 kube-apiserver、kube-controller-manager 和 kube-scheduler 静态 Pod。

## 要求

- kubeadm 管理的 Kubernetes 控制平面，或等价的 PKI 布局
- inventory 中存在名为 `masters` 的主机组，除非覆盖 `target_hosts`
- `/etc/kubernetes/pki` 下已有当前文件：`ca.crt`、`ca.key`、`sa.pub` 和 `sa.key`
- `/etc/kubernetes/pki` 下已有预置文件：`ca-new.crt`、`ca-new.key`、`sa-new.pub` 和 `sa-new.key`
- `activate_leaf_certs=true` 时，已存在预置 API server leaf 文件：`apiserver-new.*` 和 `apiserver-kubelet-client-new.*`
- `activate_kubeconfigs=true` 时，已存在预置 kubeconfig：`admin-new.conf`、`controller-manager-new.conf` 和 `scheduler-new.conf`
- kubelet 已经通过 `renew-k8s-kubelet-certs` 续签，client certificate 已由 `ca-new.crt` 签发，并且 kubelet.conf 的信任数据包含预置的新 root CA
- 已设置 `sa_key_cutover`，其值是 ServiceAccount signer 切到 `sa-new.key` 之前记录的 UTC 时间戳；除非设置 `activate_audit_projected_service_account_tokens=false`
- 目标主机上可以使用 Python 3、`openssl`、`diff`、`mv` 和 `kubectl`
- 具备 SSH 连接和提权权限

只能在兼容期已经成功后执行：API server 必须已经信任 `ca-bundle.crt` 和新旧两个 ServiceAccount 公钥，kubelet 必须已经使用新 root CA 签发的 client certificate；移除旧 `sa.pub` 前，旧 ServiceAccount token 必须已经退出。

## 可选变量

- `target_hosts`: 目标主机组，默认 `masters`
- `k8s_ca_activation_rollout_serial`: 每批处理的主机数量，默认 `1`
- `manifest_dir`: 静态 Pod manifest 目录，默认 `'/etc/kubernetes/manifests'`
- `pki_dir`: Kubernetes PKI 目录，默认 `'/etc/kubernetes/pki'`
- `kube_dir`: Kubernetes 配置目录，默认 `'/etc/kubernetes'`
- `manifest_backup_dir`: manifest 备份目录，默认 `'/etc/kubernetes/manifest-backups'`
- `kubeconfig_backup_dir`: kubeconfig 备份目录，默认 `kube_dir + '/kubeconfig-backups'`
- `backup_suffix`: 备份后缀，默认使用当前 Ansible 时间戳加 `.bak`
- `activate_leaf_certs`: 是否将 kube-apiserver 切到 `apiserver-new.*` 和 `apiserver-kubelet-client-new.*`，默认 `true`
- `activate_kubeconfigs`: 是否用预置 `*-new.conf` 替换 `admin.conf`、`controller-manager.conf` 和 `scheduler.conf`，默认 `true`
- `restart_static_pods`: 收敛后是否 touch 静态 Pod manifest，默认 `false`
- `wait_static_pods`: 是否等待重启后的静态 Pod Ready，默认跟随 `restart_static_pods`
- `kubeconfig`: readiness 检查使用的 kubeconfig，默认 `kube_dir + '/admin.conf'`
- `audit_service_account_token_retirement`: 是否执行最终激活前的 ServiceAccount token 退出审计，默认 `true`
- `activate_audit_projected_service_account_tokens`: 最终激活前审计是否扫描 kubelet projected token 文件和 projected CA 文件，默认跟随 `audit_service_account_token_retirement`
- `sa_key_cutover`: ServiceAccount token 签发切到 `sa-new.key` 前记录的 UTC 时间戳；启用 projected token 审计时必须设置
- `new_ca_file`: 用于校验 projected volume `ca.crt` 内容的预置新 root CA 文件，默认 `'/etc/kubernetes/pki/ca-new.crt'`
- `verify_kubelet_root_ca_rollout`: 最终激活前是否检查 kubelet client cert 和 kubelet 信任，默认 `true`
- `kubelet_target_hosts`: 最终激活前置检查使用的 kubelet 节点组，默认 `masters:workers`
- `kubectl_command`: kubectl 命令路径，默认 `kubectl`
- `python_interpreter`: 目标主机上使用的 Python 解释器，默认 `'/usr/bin/python3'`

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/activate-k8s-ca/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-k8s-ca/playbook.yml \
  -e sa_key_cutover=${CUTOVER} \
  -e restart_static_pods=true
```

只提升 root CA / ServiceAccount 文件并收敛 CA/SA manifest 参数，不切换 API server leaf 证书和 kubeconfig：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-k8s-ca/playbook.yml \
  -e sa_key_cutover=${CUTOVER} \
  -e activate_leaf_certs=false \
  -e activate_kubeconfigs=false \
  -e restart_static_pods=true
```

## 重要警告

- 这个 recipe 会移动 root CA 私钥材料和 ServiceAccount 签名私钥材料。请妥善保护目标主机、日志和备份文件。
- 如果 kubelet client certificate 尚未由新 root CA 签发，移除 kube-apiserver 对旧 `ca.crt` 的 client CA 信任会导致 kubelet 认证失败。
- 移除旧 `sa.pub` 可能导致仍在运行的 legacy 或 projected ServiceAccount token 失效。执行前保持默认 token 退出审计开启。
- 备份会写到静态 Pod manifest 目录之外，避免 kubelet 把备份文件当作 Pod manifest。
- 在依赖此流程前，应先在非生产或可完整恢复的集群上测试完整激活和回滚流程。
