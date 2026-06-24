# 激活预置 Kubernetes Root CA

英文版：`README.md`

这个 recipe 会把 kubeadm 风格 Kubernetes 控制平面从 root CA 兼容期收敛到 new-only root CA 材料。它会提升预置的 `ca-new-<renewal_id>.*` 文件，重写 kube-apiserver 与 kube-controller-manager 静态 Pod manifest，并且可以激活前面生成的 `*-new-<renewal_id>.conf` kubeconfig。

## 这个 Recipe 做什么

1. 默认在最终激活前校验 kubelet client certificate 和 kubelet 信任。
2. 检查当前和预置的 root CA 文件。
3. 可选校验预置 API server leaf 证书和预置 kubeconfig。
4. 备份静态 Pod manifest 和当前 kubeconfig。
5. 把 `ca-new-<renewal_id>.crt` 和 `ca-new-<renewal_id>.key` 提升为 `ca.crt` 和 `ca.key`。
6. 把 kube-apiserver 和 kube-controller-manager manifest 收敛到 new-only root CA 路径。
7. 可选 touch 并等待 kube-apiserver、kube-controller-manager 和 kube-scheduler 静态 Pod。

## 要求

- `/etc/kubernetes/pki` 下已有当前文件：`ca.crt` 和 `ca.key`
- `/etc/kubernetes/pki` 下已有预置文件：`ca-new-<renewal_id>.crt` 和 `ca-new-<renewal_id>.key`
- kubelet 已经通过 `renew-k8s-kubelet-certs` 续签，client certificate 由 `ca-new-<renewal_id>.crt` 签发，并且 kubelet.conf 信任包含预置的新 root CA
- 目标主机上有 Python 3、`openssl`、`grep` 和 `kubectl`
- SSH 访问和提权权限

只能在兼容期已经成功后执行：API server 必须已经信任 `ca-bundle-<renewal_id>.crt`，kubelet 必须已经使用新 root CA 签发的 client certificate。

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/activate-k8s-ca/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-k8s-ca/playbook.yml \
  -e renewal_id=${RENEWAL_ID} \
  -e restart_static_pods=true
```

只提升 root CA 文件并收敛 CA manifest 参数，不切换 API server leaf 证书和 kubeconfig：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-k8s-ca/playbook.yml \
  -e renewal_id=${RENEWAL_ID} \
  -e activate_leaf_certs=false \
  -e activate_kubeconfigs=false \
  -e restart_static_pods=true
```

## 重要警告

- 这个 recipe 会移动 root CA 私钥材料。请妥善保护目标主机、日志和备份文件。
- 如果 kubelet client certificate 尚未由新 root CA 签发，移除 kube-apiserver 对旧 `ca.crt` 的 client CA 信任会导致 kubelet 认证失败。
- ServiceAccount 签名 key 使用独立的 `activate-service-account-keys` recipe 激活。
- 备份会写到静态 Pod manifest 目录之外，避免 kubelet 把备份文件当成 Pod manifest。
