# 激活预置的 etcd CA

英文版：`README.md`

这个 recipe 会把预置的 etcd CA 文件提升为当前生效的 CA 文件名，并更新 kube-apiserver 和 etcd 静态 Pod manifest，让它们使用当前生效的 etcd CA 证书。默认场景是 kubeadm 管理的控制平面，etcd CA 文件位于 `/etc/kubernetes/pki/etcd`。

默认会为 kube-apiserver 配置：

```text
--etcd-cafile=/etc/kubernetes/pki/etcd/ca.crt
```

会为 etcd 配置：

```text
--trusted-ca-file=/etc/kubernetes/pki/etcd/ca.crt
--peer-trusted-ca-file=/etc/kubernetes/pki/etcd/ca.crt
```

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 使用提权权限在目标主机上运行，默认每次处理一台主机。
2. 校验配置的当前生效、预置和备份文件名非空且互不冲突。
3. 检查配置的 etcd PKI 目录下是否存在当前生效 CA 证书和私钥，以及预置 CA 证书和私钥。
4. 检查 kube-apiserver 和 etcd 静态 Pod manifest 是否存在，并确认受管理 CA 参数有可用插入点。
5. 备份 kube-apiserver 和 etcd 静态 Pod manifest。
6. 将当前生效的 CA 证书和私钥移动到备份文件名。
7. 将预置的 CA 证书和私钥移动到当前生效文件名。
8. 在移除 trust bundle 之前，先检查 manifest 是否已经使用预置的 etcd 叶子证书路径，除非设置 `require_staged_etcd_leaf_certs=false`。
9. 将 `--etcd-cafile`、`--trusted-ca-file` 和 `--peer-trusted-ca-file` 配置为指向当前生效的 etcd CA 证书。
10. 校验受管理的静态 Pod manifest 参数。
11. 打印当前生效 CA 证书里的证书数量、subject、issuer、有效期和 SHA256 指纹。

默认情况下，这个 recipe 在编辑后不会额外 touch manifest 时间戳。kubelet 通常会检测到 manifest 内容变化并重启静态 Pod。如果希望 playbook 在校验后显式 touch manifest，可以设置 `restart_static_pods=true`。

## 要求

- kubeadm 管理的 Kubernetes 控制平面并使用本地 etcd CA 文件，或等价的 etcd PKI 布局
- kubeadm 风格的 kube-apiserver 和 etcd 静态 Pod manifest 位于 `/etc/kubernetes/manifests`
- inventory 中存在名为 `etcd_members` 的主机组，除非覆盖 `target_hosts`
- 配置的 PKI 目录下已经存在当前生效的 etcd CA 证书和私钥
- 配置的 PKI 目录下已经存在预置的替换 etcd CA 证书和私钥
- 每台目标主机上可以使用 `awk`、`mv`、`grep` 和 `openssl`
- 具备 SSH 连接和提权权限，因为 PKI 文件和静态 Pod manifest 通常归 root 所有

当 kubeadm 默认路径和预置 CA 文件名符合你的环境时，不需要额外变量。

## 可选变量

- `target_hosts`: 目标主机组，默认 `etcd_members`
- `etcd_ca_rollout_serial`: 每批处理的主机数量，默认 `1`
- `manifest_dir`: 静态 Pod manifest 目录，默认 `'/etc/kubernetes/manifests'`
- `pki_dir`: Kubernetes PKI 目录，默认 `'/etc/kubernetes/pki'`
- `etcd_pki_dir`: etcd PKI 目录，默认 `'/etc/kubernetes/pki/etcd'`
- `etcd_ca_active_cert`: 当前生效 CA 证书文件名，默认 `'ca.crt'`
- `etcd_ca_active_key`: 当前生效 CA 私钥文件名，默认 `'ca.key'`
- `renewal_id`: 预置文件名中的日期或类日期 ID，默认 `YYYYMMDD`
- `etcd_ca_staged_cert`: 预置 CA 证书文件名，默认 `'ca-new-<renewal_id>.crt'`
- `etcd_ca_staged_key`: 预置 CA 私钥文件名，默认 `'ca-new-<renewal_id>.key'`
- `etcd_ca_backup_cert`: 备份 CA 证书文件名，默认使用带时间戳的 `ca-backup-*.crt`
- `etcd_ca_backup_key`: 备份 CA 私钥文件名，默认使用带时间戳的 `ca-backup-*.key`
- `etcd_ca_verify_cert`: 激活后要验证的证书文件名，默认使用当前生效 CA 证书文件名
- `etcd_ca_active_cert_path`: manifest 中使用的当前生效 CA 证书路径，默认 `etcd_pki_dir + '/' + etcd_ca_active_cert`
- `kube_apiserver_manifest`: kube-apiserver manifest 路径，默认 `manifest_dir + '/kube-apiserver.yaml'`
- `etcd_manifest`: etcd manifest 路径，默认 `manifest_dir + '/etcd.yaml'`
- `apiserver_etcd_certfile`: 预期当前使用的 kube-apiserver etcd client 证书，默认 `pki_dir + '/apiserver-etcd-client-new-<renewal_id>.crt'`
- `apiserver_etcd_keyfile`: 预期当前使用的 kube-apiserver etcd client 私钥，默认 `pki_dir + '/apiserver-etcd-client-new-<renewal_id>.key'`
- `etcd_certfile`: 预期当前使用的 etcd server 证书，默认 `etcd_pki_dir + '/server-new-<renewal_id>.crt'`
- `etcd_keyfile`: 预期当前使用的 etcd server 私钥，默认 `etcd_pki_dir + '/server-new-<renewal_id>.key'`
- `etcd_peer_certfile`: 预期当前使用的 etcd peer 证书，默认 `etcd_pki_dir + '/peer-new-<renewal_id>.crt'`
- `etcd_peer_keyfile`: 预期当前使用的 etcd peer 私钥，默认 `etcd_pki_dir + '/peer-new-<renewal_id>.key'`
- `require_staged_etcd_leaf_certs`: 激活 CA 前是否要求 manifest 已使用预置叶子证书，默认 `true`
- `manifest_backup_dir`: manifest 备份目录，默认 `'/etc/kubernetes/manifest-backups'`
- `manifest_backup_suffix`: 备份后缀，默认使用当前 Ansible 时间戳加 `.bak`
- `restart_static_pods`: 校验后是否 touch 已更新的 manifest，默认 `false`
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

在校验后显式 touch manifest：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-etcd-ca/playbook.yml \
  -e restart_static_pods=true
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
- 这个 recipe 会改变当前生效的 etcd CA 文件，并更新控制平面的静态 Pod manifest。只能把它作为经过测试的证书轮换流程的一部分来执行。
- 备份文件会写到 kubelet 静态 Pod manifest 目录之外，避免 kubelet 把备份文件也当成静态 Pod。
- 这个 recipe 不会重启 kubelet。只有在 `restart_static_pods=true` 时，它才会 touch 静态 Pod manifest。
- 这个 recipe 不会创建预置 CA 文件。执行前需要先生成并分发这些文件。
- 执行本 recipe 前应先运行 `activate-etcd-certs` 并确认 etcd 健康。否则 playbook 默认会失败，而不是在 manifest 仍指向旧叶子证书时移除旧 CA。
- 请谨慎选择备份文件名。底层移动命令可能替换已经存在的备份文件。
- 执行前应先备份 etcd 数据和 Kubernetes PKI 文件。
- 在依赖此流程前，应先在非生产或可完整恢复的集群上测试完整的激活和回滚流程。
