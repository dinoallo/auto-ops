# 配置 etcd CA Bundle

英文版：`README.md`

这个 recipe 会更新 kubeadm 风格的静态 Pod manifest，让 kube-apiserver 和 etcd 信任 `/etc/kubernetes/pki/etcd/ca-bundle-<renewal_id>.crt` 中的 etcd CA bundle。

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 使用提权权限在控制平面节点上运行，默认每次处理一台主机。
2. 检查 etcd CA bundle、kube-apiserver manifest 和 etcd manifest 是否存在。
3. 备份这两个静态 Pod manifest。
4. 为 kube-apiserver 配置 `--etcd-cafile=/etc/kubernetes/pki/etcd/ca-bundle-<renewal_id>.crt`。
5. 为 etcd 配置 `--trusted-ca-file=/etc/kubernetes/pki/etcd/ca-bundle-<renewal_id>.crt`。
6. 为 etcd 配置 `--peer-trusted-ca-file=/etc/kubernetes/pki/etcd/ca-bundle-<renewal_id>.crt`。
7. 校验每个受管理参数都只出现一次，且值符合预期。

默认情况下，这个 recipe 在编辑后不会额外 touch manifest 时间戳。kubelet 通常会检测到 manifest 内容变化并重启静态 Pod。如果希望 playbook 在校验后显式 touch manifest，可以设置 `restart_static_pods=true`。

## 要求

- kubeadm 风格的静态 Pod manifest 位于 `/etc/kubernetes/manifests`
- inventory 中存在名为 `masters` 的主机组，除非覆盖 `target_hosts`
- 已存在 etcd CA bundle：`/etc/kubernetes/pki/etcd/ca-bundle-<renewal_id>.crt`
- 每台目标主机上可以使用 `awk`
- 具备 SSH 连接和提权权限，因为 Kubernetes manifest 和 PKI 文件通常归 root 所有

## 可选变量

- `target_hosts`: 目标主机组，默认 `masters`
- `etcd_ca_bundle_rollout_serial`: 每批处理的主机数量，默认 `1`
- `manifest_dir`: 静态 Pod manifest 目录，默认 `'/etc/kubernetes/manifests'`
- `renewal_id`: 预置文件名中的日期小时或自定义 ID，默认 `YYYYMMDDHH`
- `etcd_ca_bundle_path`: etcd CA bundle 路径，默认 `'/etc/kubernetes/pki/etcd/ca-bundle-<renewal_id>.crt'`
- `kube_apiserver_manifest`: kube-apiserver manifest 路径，默认 `manifest_dir + '/kube-apiserver.yaml'`
- `etcd_manifest`: etcd manifest 路径，默认 `manifest_dir + '/etcd.yaml'`
- `manifest_backup_dir`: manifest 备份目录，默认 `'/etc/kubernetes/manifest-backups'`
- `manifest_backup_suffix`: 备份后缀，默认使用当前 Ansible 时间戳加 `.bak`
- `restart_static_pods`: 校验后是否 touch 已更新的 manifest，默认 `false`

inventory 示例：

```ini
[masters]
cp1
cp2
cp3
```

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/configure-etcd-ca-bundle/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-etcd-ca-bundle/playbook.yml
```

使用自定义 CA bundle 路径：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-etcd-ca-bundle/playbook.yml \
  -e etcd_ca_bundle_path=/etc/kubernetes/pki/etcd/custom-ca-bundle.crt
```

在校验后显式 touch manifest：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-etcd-ca-bundle/playbook.yml \
  -e restart_static_pods=true
```

## 重要警告

- 这个 recipe 会修改控制平面的静态 Pod manifest。在依赖它前，应先在非生产或可完整恢复的集群上测试。
- 修改 etcd 信任配置前，应先备份 etcd 数据和 Kubernetes PKI 文件。
- 备份文件会写到 kubelet 静态 Pod manifest 目录之外，避免 kubelet 把备份文件也当成静态 Pod。
- 确保 CA bundle 包含 etcd CA 轮换窗口内所需的全部 CA。
- 除非已经验证更大批次的发布策略，否则应一次只处理一个控制平面节点。
