# 激活预置的 etcd CA

英文版：`README.md`

这个 recipe 会把预置的 etcd CA 文件提升为当前生效的 CA 文件名。默认场景是 kubeadm 管理的控制平面，etcd CA 文件位于 `/etc/kubernetes/pki/etcd`。

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 使用提权权限在目标主机上运行，默认每次处理一台主机。
2. 校验配置的当前生效、预置和备份文件名非空且互不冲突。
3. 检查配置的 etcd PKI 目录下是否存在当前生效 CA 证书和私钥，以及预置 CA 证书和私钥。
4. 将当前生效的 CA 证书和私钥移动到备份文件名。
5. 将预置的 CA 证书和私钥移动到当前生效文件名。
6. 打印当前生效 CA 证书里的证书数量、subject、issuer、有效期和 SHA256 指纹。

## 要求

- kubeadm 管理的 Kubernetes 控制平面并使用本地 etcd CA 文件，或等价的 etcd PKI 布局
- inventory 中存在名为 `etcd_members` 的主机组，除非覆盖 `target_hosts`
- 配置的 PKI 目录下已经存在当前生效的 etcd CA 证书和私钥
- 配置的 PKI 目录下已经存在预置的替换 etcd CA 证书和私钥
- 每台目标主机上可以使用 `mv`、`grep` 和 `openssl`
- 具备 SSH 连接和提权权限，因为 PKI 文件通常归 root 所有

当 kubeadm 默认路径和预置 CA 文件名符合你的环境时，不需要额外变量。

## 可选变量

- `target_hosts`: 目标主机组，默认 `etcd_members`
- `etcd_ca_rollout_serial`: 每批处理的主机数量，默认 `1`
- `etcd_pki_dir`: etcd PKI 目录，默认 `'/etc/kubernetes/pki/etcd'`
- `etcd_ca_active_cert`: 当前生效 CA 证书文件名，默认 `'ca.crt'`
- `etcd_ca_active_key`: 当前生效 CA 私钥文件名，默认 `'ca.key'`
- `etcd_ca_staged_cert`: 预置 CA 证书文件名，默认 `'ca-new.crt'`
- `etcd_ca_staged_key`: 预置 CA 私钥文件名，默认 `'ca-new.key'`
- `etcd_ca_backup_cert`: 备份 CA 证书文件名，默认 `'ca-old.crt'`
- `etcd_ca_backup_key`: 备份 CA 私钥文件名，默认 `'ca-old.key'`
- `etcd_ca_verify_cert`: 激活后要验证的证书文件名，默认使用当前生效 CA 证书文件名
- `etcd_ca_certificate_marker`: 证书校验时统计的标记，默认 `'BEGIN CERTIFICATE'`
- `file_move_command`: 移动文件使用的命令名或路径，默认 `'mv'`
- `grep_command`: `grep` 的命令名或路径，默认 `'grep'`
- `openssl_command`: `openssl` 的命令名或路径，默认 `'openssl'`

inventory 示例：

```ini
[etcd_members]
cp1
cp2
cp3
```

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/activate-etcd-ca/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-etcd-ca/playbook.yml
```

使用自定义预置文件名和备份文件名：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-etcd-ca/playbook.yml \
  -e etcd_ca_staged_cert=etcd-ca-2026.crt \
  -e etcd_ca_staged_key=etcd-ca-2026.key \
  -e etcd_ca_backup_cert=etcd-ca-previous.crt \
  -e etcd_ca_backup_key=etcd-ca-previous.key
```

使用自定义 PKI 目录：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-etcd-ca/playbook.yml \
  -e etcd_pki_dir=/etc/etcd/pki
```

指定 SSH key 运行：

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/activate-etcd-ca/playbook.yml
```

## 重要警告

- 这个 recipe 会移动证书颁发机构私钥材料。请妥善保护目标主机、日志和备份文件。
- 这个 recipe 会改变当前生效的 etcd CA 文件。只能把它作为经过测试的证书轮换流程的一部分来执行。
- 这个 recipe 不会重启 etcd、kube-apiserver 或 kubelet。需要的服务重启应单独规划。
- 这个 recipe 不会创建预置 CA 文件。执行前需要先生成并分发这些文件。
- 请谨慎选择备份文件名。底层移动命令可能替换已经存在的备份文件。
- 执行前应先备份 etcd 数据和 Kubernetes PKI 文件。
- 在依赖此流程前，应先在非生产或可完整恢复的集群上测试完整的激活和回滚流程。
