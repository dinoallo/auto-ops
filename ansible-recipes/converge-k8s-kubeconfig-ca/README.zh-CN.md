# 收敛 Kubernetes Kubeconfig CA 数据

英文版：`README.md`

这个 recipe 会重写选定 Kubernetes kubeconfig 中嵌入的 `certificate-authority-data`，使其只包含新 root CA。它用于 root CA 轮转末尾，也就是 kube-apiserver 已经收敛到 new-only serving/client CA 材料之后。

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 在 control-plane 节点上运行，默认每次处理一台。
2. 将选定 kubeconfig 备份到 `/etc/kubernetes/kubeconfig-backups`。
3. 将每个 kubeconfig 里的 `certificate-authority-data` 替换为 `new_ca_file`。
4. 验证每个 kubeconfig 只包含一个 CA 证书，且与新 root CA 完全一致。
5. 验证每个 kubeconfig 都能访问 `/readyz`。
6. 可选重启 kube-controller-manager 和 kube-scheduler 静态 Pod，以重新加载 kubeconfig。

## 要求

- `/etc/kubernetes` 下存在 kubeconfig
- 新 root CA 文件，默认 `/etc/kubernetes/pki/ca.crt`
- 目标主机上可以使用 `kubectl` 和 Python 3
- 具备 SSH 连接和提权权限

## 可选变量

- `target_hosts`: 目标主机组，默认 `masters`
- `kubeconfig_ca_rollout_serial`: 每批处理的主机数量，默认 `1`
- `new_ca_file`: 要嵌入的 CA 文件，默认 `pki_dir + '/ca.crt'`
- `kubeconfig_files`: 要重写的 kubeconfig 列表，默认 admin、controller-manager 和 scheduler kubeconfig
- `restart_static_pods`: 重写后是否 touch kube-controller-manager 和 kube-scheduler manifest，默认 `false`
- `wait_static_pods`: 是否等待重启后的静态 Pod Ready，默认跟随 `restart_static_pods`

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/converge-k8s-kubeconfig-ca/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/converge-k8s-kubeconfig-ca/playbook.yml \
  -e restart_static_pods=true
```

## 重要警告

- 只能在 kube-apiserver 已经使用新 root CA 签发的 serving certificate，并且已经信任新 root CA 签发的 client certificate 后执行。
- 重写 controller-manager 和 scheduler kubeconfig 后，需要重启对应静态 Pod 才会重新加载新的 CA 数据。
