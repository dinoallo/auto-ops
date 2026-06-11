# 续签由根 CA 签发的 Kubernetes 证书和 kubeconfig

英文版：`README.md`

这个 recipe 使用预置的新 root CA 续签 Kubernetes API server 证书和部分 kubeconfig。它会把续签后的文件写成 `-new` 文件名，因此不会直接替换当前正在使用的文件。

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 使用提权权限在 `masters` inventory 组中的主机上运行，每次处理一台主机。
2. 重建临时 kubeadm 证书 staging 目录。
3. 将当前 API server 证书模板复制到 staging 目录。
4. 将 `ca-new.crt` 和 `ca-new.key` 作为 kubeadm 签发 CA 放入 staging 目录。
5. 使用 kubeadm 续签 `apiserver` 和 `apiserver-kubelet-client` 证书。
6. 将续签后的 API server 证书和私钥安装为 `-new` 文件名。
7. 为 `admin`、`controller-manager` 和 `scheduler` 创建新的客户端证书。
8. 创建 `admin-new.conf`、`controller-manager-new.conf` 和 `scheduler-new.conf`，其中嵌入新的客户端证书并使用 `ca-bundle.crt`。
9. 验证续签证书，并使用生成的 kubeconfig 检查 `/readyz`。

## 要求

- kubeadm 管理的 Kubernetes 控制平面
- inventory 中存在名为 `masters` 的主机组
- 每台目标主机上可以使用 `kubeadm`、`kubectl`、`openssl`、`cp`、`install` 和 `chmod`
- 配置的 Kubernetes 目录下已经存在当前 API server 证书和 kubeconfig
- 已预置 root CA 文件 `ca-new.crt`、`ca-new.key` 和 `ca-bundle.crt`
- 具备 SSH 连接和提权权限，因为 PKI 和 kubeconfig 文件通常归 root 所有

当 kubeadm 默认路径和预置 CA 文件名符合你的环境时，不需要额外变量。

## 可选变量

- `pki_dir`: Kubernetes PKI 目录，默认 `'/etc/kubernetes/pki'`
- `kube_dir`: Kubernetes 配置目录，默认 `'/etc/kubernetes'`
- `stage_dir`: 临时 kubeadm 证书续签目录，默认 `'/tmp/kubeadm-root-leaf-renew'`
- `work_dir`: 临时 kubeconfig 和客户端证书工作目录，默认 `'/tmp/kubeconfig-root-ca-renew'`

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/renew-k8s-certs/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-k8s-certs/playbook.yml
```

使用自定义 Kubernetes 目录：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-k8s-certs/playbook.yml \
  -e pki_dir=/etc/kubernetes/pki \
  -e kube_dir=/etc/kubernetes
```

指定 SSH key 运行：

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/renew-k8s-certs/playbook.yml
```

## 重要警告

- 这个 recipe 会处理私钥和 root CA 材料。请妥善保护目标主机、日志和生成文件。
- 这个 recipe 不会创建预置的 root CA 文件。
- 这个 recipe 不会替换当前生效的 API server 证书或 kubeconfig，也不会重启 Kubernetes 组件。
- 生成的 kubeconfig 会通过 `/readyz` 验证；如果 readiness 检查失败，必须先排查再激活。
- 执行前应先备份 Kubernetes PKI 文件和 kubeconfig。
- 应在非生产或可完整恢复的集群上测试完整的轮换和回滚流程。
