# 激活预置的 front-proxy CA

英文版：`README.md`

这个 recipe 会把预置的 Kubernetes front-proxy CA 文件提升为当前生效的 front-proxy CA 文件名。默认场景是 kubeadm 管理的控制平面，PKI 文件位于 `/etc/kubernetes/pki`。

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 使用提权权限在 `masters` inventory 组中的主机上运行，每次处理一台主机。
2. 将当前生效的 `front-proxy-ca.crt` 和 `front-proxy-ca.key` 移动为 `front-proxy-ca-old.crt` 和 `front-proxy-ca-old.key`。
3. 将 `front-proxy-ca-new.crt` 和 `front-proxy-ca-new.key` 移动到当前生效的 front-proxy CA 文件名。
4. 打印当前生效 front-proxy CA 证书里的证书数量、subject、issuer、有效期和 SHA256 指纹。

## 要求

- kubeadm 管理的 Kubernetes 控制平面，或等价的 PKI 布局
- inventory 中存在名为 `masters` 的主机组
- `/etc/kubernetes/pki` 下已经存在当前生效的 front-proxy CA 证书和私钥
- `/etc/kubernetes/pki` 下已经存在预置的替换 front-proxy CA 证书和私钥
- 每台目标主机上可以使用 `mv`、`grep` 和 `openssl`
- 具备 SSH 连接和提权权限，因为 PKI 文件通常归 root 所有

当 kubeadm 默认路径和预置 CA 文件名符合你的环境时，不需要额外变量。

## 可选变量

- `pki_dir`: Kubernetes PKI 目录，默认 `'/etc/kubernetes/pki'`

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/activate-front-proxy-ca/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-front-proxy-ca/playbook.yml
```

使用自定义 PKI 目录：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-front-proxy-ca/playbook.yml \
  -e pki_dir=/etc/kubernetes/pki
```

指定 SSH key 运行：

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/activate-front-proxy-ca/playbook.yml
```

## 重要警告

- 这个 recipe 会移动证书颁发机构私钥材料。请妥善保护目标主机、日志和备份文件。
- 这个 recipe 会改变当前生效的 front-proxy CA 文件。只能把它作为经过测试的证书轮换流程的一部分来执行。
- 这个 recipe 不会重启 kube-apiserver、kube-controller-manager 或 kubelet。需要的重启应单独规划。
- 这个 recipe 不会创建预置 CA 文件。执行前需要先生成并分发这些文件。
- 如果 `front-proxy-ca-old.*` 文件已经存在，移动命令可能替换这些旧备份。
- 执行前应先备份 Kubernetes PKI 文件。
