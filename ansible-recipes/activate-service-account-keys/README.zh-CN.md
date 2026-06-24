# 激活预置 Kubernetes ServiceAccount Key Pair

英文版：`README.md`

这个 recipe 会退出旧 ServiceAccount 公钥，并把预置的 `sa-new-<renewal_id>.pub` 和 `sa-new-<renewal_id>.key` 提升为 kubeadm 原始文件名 `sa.pub` 和 `sa.key`。提升前会归档当前生效文件，并把控制面 manifest 收敛到 new-only ServiceAccount key 路径。

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/activate-service-account-keys/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-service-account-keys/playbook.yml \
  -e renewal_id=${RENEWAL_ID} \
  -e sa_key_cutover=${CUTOVER} \
  -e restart_static_pods=true
```

## 这个 Recipe 做什么

1. 移除旧公钥前执行 ServiceAccount token 退出审计。
2. 检查当前和预置 ServiceAccount 文件。
3. 校验预置私钥与预置公钥匹配。
4. 默认要求已经处于兼容期 manifest 状态：kube-apiserver 信任新旧两个公钥，签发已经切到预置私钥。
5. 默认把当前 `sa.pub` 和 `sa.key` 归档到 `/etc/kubernetes/pki/archive/service-account-<renewal_id>`。
6. 把预置 key pair 提升为 `sa.pub` 和 `sa.key`。
7. 把 kube-apiserver 和 kube-controller-manager manifest 收敛到 canonical new-only 路径。
8. 可选 touch manifest 并等待静态 Pod 重启完成。

## 重要警告

- 在旧 ServiceAccount token 退出前不要执行本 recipe。移除旧 `sa.pub` 可能导致仍在运行的 legacy 或 projected token 失效。
- 对于只轮转 ServiceAccount key 的流程，默认不检查 projected CA bundle。只有当本激活和 Root CA 轮转耦合时，才设置 `activate_audit_projected_ca_bundle=true`。
- 备份会写到静态 Pod manifest 目录之外，避免 kubelet 把备份文件当成 Pod manifest。
