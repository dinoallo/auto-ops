# 续签由 Root CA 签发的 Kubelet 客户端证书

英文版：`README.md`

这个 recipe 使用预置的新 Kubernetes root CA 续签 kubelet client certificate，并重写 kubelet 访问 API server 时使用的 CA 信任。它会覆盖 control-plane 和 worker 节点；在把 kube-apiserver 的 `--client-ca-file` 收敛到 new-only root CA 前，这是必需步骤。

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 从源 control-plane 节点读取 `ca-new-<renewal_id>.crt`、`ca-new-<renewal_id>.key` 和 `ca-bundle-<renewal_id>.crt`。
2. 默认在 `masters:workers` 上运行，每次处理一台节点。
3. 在每个 kubelet 节点安装 `ca-new-<renewal_id>.crt` 和 `ca-bundle-<renewal_id>.crt`。
4. 为 `system:node:<node-name>` 生成 kubelet client key 和 CSR。
5. 在源 control-plane 节点用 `ca-new-<renewal_id>.crt/key` 签发 kubelet client certificate。
6. 将 `kubelet-client-current.pem` 替换为指向新 cert/key PEM 的 symlink。
7. 重写 `/etc/kubernetes/kubelet.conf`，嵌入 `ca-bundle-<renewal_id>.crt` 或 `ca-new-<renewal_id>.crt`。
8. 重启 kubelet，并等待 Kubernetes Node 回到 `Ready`。

## 要求

- inventory 中存在 `masters` 和 `workers` 组，除非覆盖 `target_hosts`
- 源 control-plane 节点已存在预置 root CA 文件：`ca-new-<renewal_id>.crt`、`ca-new-<renewal_id>.key` 和 `ca-bundle-<renewal_id>.crt`
- kubelet 配置文件位于 `/etc/kubernetes/kubelet.conf`
- kubelet client certificate symlink 位于 `/var/lib/kubelet/pki/kubelet-client-current.pem`
- 目标主机上可以使用 `openssl`、`python3`、`systemctl` 和 `kubectl`
- 具备 SSH 连接和提权权限

## 可选变量

- `target_hosts`: 要更新的 kubelet 节点，默认 `masters:workers`
- `k8s_ca_source_host`: 预置 CA 材料所在的源 control-plane 节点，默认 `masters` 中第一台
- `kubelet_ca_rollout_serial`: 每批更新的节点数，默认 `1`
- `pki_dir`: Kubernetes PKI 目录，默认 `'/etc/kubernetes/pki'`
- `renewal_id`: 预置 root CA 文件名中的日期小时或自定义 ID，默认 `YYYYMMDDHH`
- `kubelet_conf`: kubelet kubeconfig，默认 `'/etc/kubernetes/kubelet.conf'`
- `kubelet_pki_dir`: kubelet PKI 目录，默认 `'/var/lib/kubelet/pki'`
- `kubelet_trust_mode`: `bundle` 或 `new`，默认 `bundle`
- `promote_kubelet_ca`: 是否将节点本地 `pki_dir/ca.crt` 替换为 `ca-new-<renewal_id>.crt`，默认 `false`
- `renew_kubelet_client_cert`: 是否创建新的 kubelet client certificate，默认 `true`
- `restart_kubelet`: 重写文件后是否重启 kubelet，默认 `true`
- `wait_kubelet_node_ready`: 是否等待 Node Ready，默认跟随 `restart_kubelet`
- `kubeconfig`: Node readiness 检查使用的 kubeconfig，默认 `'/etc/kubernetes/admin.conf'`

## 用法

兼容期内，让 kubelet 同时信任 old 和 new CA：

```bash
ansible-playbook --syntax-check ansible-recipes/renew-k8s-kubelet-certs/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-k8s-kubelet-certs/playbook.yml \
  -e kubelet_trust_mode=bundle
```

kube-apiserver 已经收敛到 new-only root CA 后，移除 kubelet 对旧 CA 的信任，并提升节点本地 CA 文件：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-k8s-kubelet-certs/playbook.yml \
  -e kubelet_trust_mode=new \
  -e promote_kubelet_ca=true \
  -e renew_kubelet_client_cert=false
```

## 重要警告

- 这个 recipe 会处理 kubelet 私钥，并在源节点使用 root CA 私钥材料。请妥善保护目标主机和日志。
- 必须在最终 root CA 激活前执行。如果 kubelet 仍使用旧 CA 签发的 client certificate，而 apiserver 已移除旧 client CA，节点认证会失败。
- 在 kube-apiserver 的 serving/client CA 材料确认 new-only 可用之前，保持 `kubelet_trust_mode=bundle`。
- 应在非生产或可完整恢复的集群上测试完整的轮换和回滚流程。
