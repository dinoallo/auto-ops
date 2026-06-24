# 配置 Kubernetes Root CA Bundle 参数

英文版：`README.md`

这个 recipe 会更新 kubeadm 风格的 kube-apiserver 和 kube-controller-manager 静态 Pod manifest，让它们在 root CA 轮转期间使用 Kubernetes root CA bundle。

默认会给 kube-apiserver 配置：

```text
--client-ca-file=/etc/kubernetes/pki/ca-bundle-<renewal_id>.crt
```

会给 kube-controller-manager 配置：

```text
--root-ca-file=/etc/kubernetes/pki/ca-bundle-<renewal_id>.crt
--cluster-signing-cert-file=/etc/kubernetes/pki/ca.crt
--cluster-signing-key-file=/etc/kubernetes/pki/ca.key
```

要把后续证书签发切到预置 root CA 时，把 `ca_cert_path` 和 `ca_key_path` 指向 `ca-new-<renewal_id>.*`。

## 用法

兼容期，仍使用旧 signer：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-k8s-ca-bundle/playbook.yml \
  -e renewal_id=${RENEWAL_ID} \
  -e restart_static_pods=true
```

切换证书 signer，同时保持 bundle 兼容信任：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-k8s-ca-bundle/playbook.yml \
  -e renewal_id=${RENEWAL_ID} \
  -e ca_cert_path=/etc/kubernetes/pki/ca-new-${RENEWAL_ID}.crt \
  -e ca_key_path=/etc/kubernetes/pki/ca-new-${RENEWAL_ID}.key \
  -e restart_static_pods=true
```

## 重要警告

- 这个 recipe 会修改控制面静态 Pod manifest。在依赖它之前，请先在非生产或可完整恢复的集群中测试。
- 修改 root CA 信任配置前，应先备份 Kubernetes PKI 文件。
- 确保 CA bundle 包含轮转窗口内需要信任的所有 root CA。
- ServiceAccount 签名 key 使用独立的 `configure-service-account-keys` recipe 配置。
