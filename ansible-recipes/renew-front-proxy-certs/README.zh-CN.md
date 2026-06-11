# 使用预置 CA 续签 front-proxy-client 证书

英文版：`README.md`

这个 recipe 使用预置的 front-proxy CA 文件续签 kubeadm 管理的 `front-proxy-client` 证书。它会把续签后的证书和私钥写成 `-new` 文件名，因此不会直接替换当前正在使用的文件。

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 使用提权权限在 `masters` inventory 组中的主机上运行，每次处理一台主机。
2. 重建临时 kubeadm staging 目录。
3. 将当前 `front-proxy-client` 证书和私钥复制到 staging 目录作为续签模板。
4. 将 `front-proxy-ca-new.crt` 和 `front-proxy-ca-new.key` 复制到 staging 目录作为 kubeadm 签发 CA。
5. 执行 `kubeadm certs renew front-proxy-client`。
6. 将续签后的证书和私钥安装为 `front-proxy-client-new.crt` 和 `front-proxy-client-new.key`。
7. 打印续签证书的 subject、issuer、有效期和 extended key usage。

## 要求

- kubeadm 管理的 Kubernetes 控制平面
- inventory 中存在名为 `masters` 的主机组
- 每台目标主机上可以使用 `kubeadm`、`openssl` 和 `install`
- 配置的 PKI 目录下已经存在 `front-proxy-client.crt` 和 `front-proxy-client.key`
- 已预置 front-proxy CA 文件 `front-proxy-ca-new.crt` 和 `front-proxy-ca-new.key`
- 具备 SSH 连接和提权权限，因为 PKI 文件通常归 root 所有

当 kubeadm 默认路径和预置 CA 文件名符合你的环境时，不需要额外变量。

## 可选变量

- `stage_dir`: 临时 kubeadm 续签目录，默认 `'/tmp/kubeadm-front-proxy-leaf-renew'`
- `pki_dir`: Kubernetes PKI 目录，默认 `'/etc/kubernetes/pki'`

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/renew-front-proxy-certs/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-front-proxy-certs/playbook.yml
```

使用自定义 PKI 路径：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-front-proxy-certs/playbook.yml \
  -e pki_dir=/etc/kubernetes/pki
```

指定 SSH key 运行：

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/renew-front-proxy-certs/playbook.yml
```

## 重要警告

- 这个 recipe 会处理私钥和 front-proxy CA 材料。请妥善保护目标主机、日志和生成文件。
- 这个 recipe 不会创建预置的 front-proxy CA 文件。
- 这个 recipe 不会替换当前生效的 `front-proxy-client.*` 文件，也不会重启 Kubernetes 组件。
- 激活或使用续签证书前，应先核对打印出的 issuer 和有效期。
- 执行前应先备份 Kubernetes PKI 文件。
