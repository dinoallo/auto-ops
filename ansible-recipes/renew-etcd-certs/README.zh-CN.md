# 使用预置新 CA 续签 etcd 叶子证书

英文版：`README.md`

这个 recipe 使用已经预置的新 etcd CA 来续签 kubeadm 管理的 etcd 叶子证书。它会把续签后的文件以 `-new` 文件名写到现有证书旁边，因此这个 playbook 不会直接替换当前正在使用的证书。

## 文件

- `playbook.yml`: recipe 主体

## 这个 Recipe 会做什么

1. 使用提权权限在 `etcd_members` inventory 组中的主机上运行，并且每次只处理一台主机。
2. 重新创建一个临时 kubeadm 证书续签 staging 目录。
3. 将当前 etcd 叶子证书和私钥复制到 staging 目录，作为 kubeadm 续签模板。
4. 将预置的新 etcd CA `ca-new.crt` 和 `ca-new.key` 复制到 staging 目录，作为 kubeadm 签发证书使用的 CA。
5. 针对 etcd 相关叶子证书目标执行 `kubeadm certs renew`。
6. 将续签后的证书和私钥以 `-new` 文件名安装到 Kubernetes PKI 目录下。
7. 打印续签证书的 subject、issuer、有效期和 Subject Alternative Name 信息。

## 前置要求

- kubeadm 管理的 Kubernetes 控制平面，并使用本地 etcd 证书
- inventory 中存在名为 `etcd_members` 的主机组
- 每台目标主机上都可以使用 `kubeadm`、`openssl`、`cp` 和 `install`
- 配置的 PKI 目录下已经存在当前 etcd 叶子证书和私钥
- 每台目标主机上都已经预置 `/etc/kubernetes/pki/etcd/ca-new.crt` 和 `/etc/kubernetes/pki/etcd/ca-new.key`
- Ansible 具备 SSH 连接和提权能力，因为源 PKI 路径和目标 PKI 路径通常归 root 所有

如果你的环境符合 kubeadm 默认路径，并且预置 CA 文件名也符合默认值，这个 recipe 不需要额外传入变量。

## 可选变量

- `stage_dir`: 临时 kubeadm 续签目录，默认 `'/tmp/kubeadm-etcd-leaf-renew'`
- `pki_dir`: Kubernetes PKI 根目录，默认 `'/etc/kubernetes/pki'`
- `etcd_pki_dir`: etcd PKI 目录，默认 `'/etc/kubernetes/pki/etcd'`
- `kubeadm_renew_targets`: 要续签的 kubeadm 证书目标，默认包含 `apiserver-etcd-client`、`etcd-healthcheck-client`、`etcd-peer` 和 `etcd-server`

inventory 示例：

```ini
[etcd_members]
cp1
cp2
cp3
```

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/renew-etcd-certs/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-etcd-certs/playbook.yml
```

如果要使用自定义 PKI 路径：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-etcd-certs/playbook.yml \
  -e pki_dir=/etc/kubernetes/pki \
  -e etcd_pki_dir=/etc/kubernetes/pki/etcd
```

如果需要指定 SSH key：

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/renew-etcd-certs/playbook.yml
```

## 重要提醒

- 这个 recipe 会处理私钥和证书 CA 材料，应妥善保护目标主机、日志和生成文件。
- 这个 recipe 不会创建新的 etcd CA。每台目标主机上都必须已经存在 `ca-new.crt` 和 `ca-new.key`。
- 这个 recipe 不会替换当前正在使用的证书文件，也不会重启 etcd 或 kube-apiserver。它只会为后续受控切换准备 `*-new.crt` 和 `*-new.key` 文件。
- 执行前应先备份 etcd 数据和 Kubernetes PKI 文件。
- 在使用续签证书前，请先核对输出中的 issuer、有效期和 SAN 信息。
- 在依赖这套流程前，请先在非生产或可完整恢复的集群上测试完整轮换和回滚流程。
