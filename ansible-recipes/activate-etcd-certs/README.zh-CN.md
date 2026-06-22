# 激活预置 etcd 叶子证书

English version: `README.md`

这个 recipe 会更新 kubeadm 风格的静态 Pod manifest，让 kube-apiserver 和 etcd 使用 `renew-etcd-certs` 生成的预置 etcd 叶子证书。

默认会为 kube-apiserver 配置：

```text
--etcd-certfile=/etc/kubernetes/pki/apiserver-etcd-client-new-<renewal_id>.crt
--etcd-keyfile=/etc/kubernetes/pki/apiserver-etcd-client-new-<renewal_id>.key
```

并为 etcd 配置：

```text
--cert-file=/etc/kubernetes/pki/etcd/server-new-<renewal_id>.crt
--key-file=/etc/kubernetes/pki/etcd/server-new-<renewal_id>.key
--peer-cert-file=/etc/kubernetes/pki/etcd/peer-new-<renewal_id>.crt
--peer-key-file=/etc/kubernetes/pki/etcd/peer-new-<renewal_id>.key
```

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 会做什么

1. 使用提权权限在控制平面节点上运行，默认每次只处理一台主机。
2. 检查预置 etcd 证书和 key 文件是否存在。
3. 检查 kube-apiserver 和 etcd manifest 是否存在。
4. 检查 manifest 是否已经信任 etcd CA bundle，除非设置 `require_etcd_ca_bundle=false`。
5. 备份两个静态 Pod manifest。
6. 先修改临时 manifest 副本，并检查每个受管参数都只出现一次且值符合预期。
7. 先安装更新后的 etcd manifest，再安装更新后的 kube-apiserver manifest。
8. 当 `restart_static_pods=true` 时，额外 touch manifest 以触发重启。

这个 recipe 会先修改临时文件，只有在全部受管参数验证通过后才写回真实 manifest。Kubelet 通常会检测 manifest 内容变化并重启静态 Pod。如果希望 playbook 在安装后显式 touch manifest，可以设置 `restart_static_pods=true`。

## 要求

- kubeadm 管理的 Kubernetes 控制平面，并使用本地 etcd 证书
- inventory 中存在名为 `masters` 的主机组，除非你覆盖 `target_hosts`
- 已由 `renew-etcd-certs` 生成的预置 etcd 叶子证书文件
- 已存在 etcd CA bundle：`/etc/kubernetes/pki/etcd/ca-bundle-<renewal_id>.crt`，除非设置 `require_etcd_ca_bundle=false`
- `/etc/kubernetes/manifests` 下存在 kube-apiserver 和 etcd manifest
- 每台目标主机上可以使用 `awk`
- SSH 访问和提权权限，因为 Kubernetes manifest 和 PKI 文件通常归 root 所有

## 可选变量

- `target_hosts`: 目标主机组，默认 `'masters'`
- `etcd_cert_rollout_serial`: 每批处理的主机数量，默认 `1`
- `manifest_dir`: 静态 Pod manifest 目录，默认 `'/etc/kubernetes/manifests'`
- `pki_dir`: Kubernetes PKI 目录，默认 `'/etc/kubernetes/pki'`
- `etcd_pki_dir`: etcd PKI 目录，默认 `pki_dir + '/etcd'`
- `renewal_id`: 预置文件名中的日期或类日期 ID，默认 `YYYYMMDD`
- `kube_apiserver_manifest`: kube-apiserver manifest 路径，默认 `manifest_dir + '/kube-apiserver.yaml'`
- `etcd_manifest`: etcd manifest 路径，默认 `manifest_dir + '/etcd.yaml'`
- `apiserver_etcd_certfile`: kube-apiserver etcd 客户端证书路径，默认 `pki_dir + '/apiserver-etcd-client-new-<renewal_id>.crt'`
- `apiserver_etcd_keyfile`: kube-apiserver etcd 客户端 key 路径，默认 `pki_dir + '/apiserver-etcd-client-new-<renewal_id>.key'`
- `etcd_certfile`: etcd server 证书路径，默认 `etcd_pki_dir + '/server-new-<renewal_id>.crt'`
- `etcd_keyfile`: etcd server key 路径，默认 `etcd_pki_dir + '/server-new-<renewal_id>.key'`
- `etcd_peer_certfile`: etcd peer 证书路径，默认 `etcd_pki_dir + '/peer-new-<renewal_id>.crt'`
- `etcd_peer_keyfile`: etcd peer key 路径，默认 `etcd_pki_dir + '/peer-new-<renewal_id>.key'`
- `etcd_ca_bundle_path`: etcd CA bundle 路径，默认 `etcd_pki_dir + '/ca-bundle-<renewal_id>.crt'`
- `require_etcd_ca_bundle`: 激活前是否要求 manifest 已使用 etcd CA bundle，默认 `true`
- `manifest_backup_dir`: manifest 备份目录，默认 `'/etc/kubernetes/manifest-backups'`
- `manifest_backup_suffix`: 备份后缀，默认当前 Ansible 时间戳加 `.bak`
- `restart_static_pods`: 安装更新后的 manifest 后是否 touch manifest，默认 `false`

示例 inventory：

```ini
[masters]
cp1
cp2
cp3
```

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/activate-etcd-certs/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-etcd-certs/playbook.yml
```

如果希望安装后显式 touch manifest：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-etcd-certs/playbook.yml \
  -e restart_static_pods=true
```

如果要使用自定义预置证书路径：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-etcd-certs/playbook.yml \
  -e apiserver_etcd_certfile=/etc/kubernetes/pki/apiserver-etcd-client-2026.crt \
  -e apiserver_etcd_keyfile=/etc/kubernetes/pki/apiserver-etcd-client-2026.key \
  -e etcd_certfile=/etc/kubernetes/pki/etcd/server-2026.crt \
  -e etcd_keyfile=/etc/kubernetes/pki/etcd/server-2026.key \
  -e etcd_peer_certfile=/etc/kubernetes/pki/etcd/peer-2026.crt \
  -e etcd_peer_keyfile=/etc/kubernetes/pki/etcd/peer-2026.key
```

如果需要指定连接时使用的 SSH key：

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/activate-etcd-certs/playbook.yml
```

## 重要提醒

- 先运行 `configure-etcd-ca-bundle`，并确认所有 etcd 成员健康后，再激活预置证书。
- 这个 recipe 会修改控制平面静态 Pod manifest，可能导致 etcd 和 kube-apiserver 重启。
- 备份文件会写到 kubelet 静态 Pod manifest 目录之外，避免 kubelet 把备份文件也当成静态 Pod。
- 除非已经验证过更大的滚动策略，否则应每次只处理一台控制平面节点。
- 修改活动 etcd 证书路径前，应先备份 etcd 数据和 Kubernetes PKI 文件。
- 先在非生产环境或可完整恢复的集群中验证完整的 CA 续签、证书续签、激活、健康检查和回滚流程。
