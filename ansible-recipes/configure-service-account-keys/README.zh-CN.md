# 配置 Kubernetes ServiceAccount Key 参数

英文版：`README.md`

这个 recipe 会更新 kubeadm 风格的 kube-apiserver 和 kube-controller-manager 静态 Pod manifest，用于 ServiceAccount 签名 key 轮转。它可以让 kube-apiserver 同时信任当前和预置公钥，并把新 token 签发切到预置私钥。

默认会给 kube-apiserver 配置：

```text
--service-account-key-file=/etc/kubernetes/pki/sa.pub
--service-account-key-file=/etc/kubernetes/pki/sa-new-<renewal_id>.pub
--service-account-signing-key-file=/etc/kubernetes/pki/sa.key
```

会给 kube-controller-manager 配置：

```text
--service-account-private-key-file=/etc/kubernetes/pki/sa.key
```

要切换新 token 签发时，把 `service_account_signing_key_path` 和 `service_account_private_key_path` 指向 `sa-new-<renewal_id>.key`。

## 用法

兼容期，仍使用旧 signer：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-service-account-keys/playbook.yml \
  -e renewal_id=${RENEWAL_ID} \
  -e restart_static_pods=true
```

切换 signer，同时继续信任新旧两个公钥：

```bash
CUTOVER=$(date -u +%Y-%m-%dT%H:%M:%SZ)

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-service-account-keys/playbook.yml \
  -e renewal_id=${RENEWAL_ID} \
  -e service_account_signing_key_path=/etc/kubernetes/pki/sa-new-${RENEWAL_ID}.key \
  -e service_account_private_key_path=/etc/kubernetes/pki/sa-new-${RENEWAL_ID}.key \
  -e restart_static_pods=true
```

后续执行 `activate-service-account-keys` 时使用记录下来的 `CUTOVER`。

## 重要警告

- 在切换前签发的 legacy 和 projected ServiceAccount token 退出之前，保持 kube-apiserver 同时信任新旧两个公钥。
- 除非已经验证过更宽的 rollout 策略，否则控制平面节点应逐台滚动。
