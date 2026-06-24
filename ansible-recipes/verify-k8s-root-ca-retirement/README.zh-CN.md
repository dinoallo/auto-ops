# 验证 Kubernetes Root CA 退出

英文版：`README.md`

这个 recipe 用于验证 Kubernetes Root CA 轮转是否可以继续推进，或者是否已经完全收敛到 new-only 信任状态。它是只读验证，不会改写 manifest、kubeconfig 或 PKI 文件。

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 校验 kube-apiserver 和 kube-controller-manager 静态 Pod manifest 中的 CA 参数。
2. 校验 API server leaf 证书是否由预期的新 Root CA 签发。
3. 校验系统 kubeconfig 中嵌入的 CA 数据，并验证能访问 `/readyz`。
4. 校验 kubelet client 证书是否由预期的新 Root CA 签发。
5. 校验 kubelet kubeconfig 中的 CA 数据。
6. 校验 kubelet 节点上 projected ServiceAccount `ca.crt` 文件。

## 模式

- `root_ca_retirement_phase=compat`: archive/promote 前使用。验证器预期部分位置仍是 bundle trust，并检查新 CA 材料已经进入可用状态。
- `root_ca_retirement_phase=new_only`: archive/promote 和收敛后使用。验证器预期嵌入 CA 数量为 1，且内容等于已提升的新 Root CA。
- Projected ServiceAccount CA 验证只检查当前 `Running` 且没有进入删除流程的 Pod。默认会重试最多 5 分钟（`projected_serviceaccount_ca_verify_retries=20`、`projected_serviceaccount_ca_verify_delay=15`），给 kubelet projected volume 刷新留出收敛时间。

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/verify-k8s-root-ca-retirement/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/verify-k8s-root-ca-retirement/playbook.yml \
  -e renewal_id=${RENEWAL_ID} \
  -e root_ca_retirement_phase=compat

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/verify-k8s-root-ca-retirement/playbook.yml \
  -e root_ca_retirement_phase=new_only
```

## 重要警告

- `compat` 模式不能证明旧 Root CA 已经消失；它证明集群已经可以使用预置新 Root CA 和兼容信任继续运行。
- `new_only` 模式才是旧 CA 退出门禁。它会检查 kubeconfig、kubelet trust、projected ServiceAccount CA 文件和静态 Pod manifest 引用是否已经是 new-only 状态。
- 集群外部客户端无法由这个 playbook 完全证明；需要单独审计并重启或重新配置。
