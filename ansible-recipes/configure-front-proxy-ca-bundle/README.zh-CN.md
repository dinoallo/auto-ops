# 配置 front-proxy CA Bundle

英文版：`README.md`

这个 recipe 会更新 kube-apiserver 静态 Pod manifest，让 Kubernetes aggregation requestheader client CA 指向 front-proxy CA bundle。

默认会为 kube-apiserver 配置：

```text
--requestheader-client-ca-file=/etc/kubernetes/pki/front-proxy-ca-bundle-<renewal_id>.crt
```

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 使用提权权限在控制平面节点上运行，默认每次处理一台主机。
2. 检查 front-proxy CA bundle 和 kube-apiserver manifest 是否存在。
3. 备份 kube-apiserver 静态 Pod manifest。
4. 将 `--requestheader-client-ca-file` 配置为指向指定的 front-proxy CA bundle。
5. 校验受管理参数只出现一次，且值符合预期。

默认情况下，这个 recipe 在编辑后不会额外 touch manifest 时间戳。kubelet 通常会检测到 manifest 内容变化并重启静态 Pod。如果希望 playbook 在校验后显式 touch manifest，可以设置 `restart_static_pods=true`。

## 要求

- kubeadm 风格的 kube-apiserver 静态 Pod manifest 位于 `/etc/kubernetes/manifests`
- inventory 中存在名为 `masters` 的主机组，除非覆盖 `target_hosts`
- 已存在 front-proxy CA bundle：`/etc/kubernetes/pki/front-proxy-ca-bundle-<renewal_id>.crt`
- 每台目标主机上可以使用 `awk`
- 具备 SSH 连接和提权权限，因为 Kubernetes manifest 和 PKI 文件通常归 root 所有

## 可选变量

- `target_hosts`: 目标主机组，默认 `masters`
- `front_proxy_ca_bundle_rollout_serial`: 每批处理的主机数量，默认 `1`
- `manifest_dir`: 静态 Pod manifest 目录，默认 `'/etc/kubernetes/manifests'`
- `pki_dir`: Kubernetes PKI 目录，默认 `'/etc/kubernetes/pki'`
- `renewal_id`: 预置文件名中的日期或类日期 ID，默认 `YYYYMMDD`
- `front_proxy_ca_bundle_path`: front-proxy CA bundle 路径，默认 `pki_dir + '/front-proxy-ca-bundle-<renewal_id>.crt'`
- `kube_apiserver_manifest`: kube-apiserver manifest 路径，默认 `manifest_dir + '/kube-apiserver.yaml'`
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
ansible-playbook --syntax-check ansible-recipes/configure-front-proxy-ca-bundle/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-front-proxy-ca-bundle/playbook.yml
```

使用自定义 CA bundle 路径：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-front-proxy-ca-bundle/playbook.yml \
  -e front_proxy_ca_bundle_path=/etc/kubernetes/pki/custom-front-proxy-ca-bundle.crt
```

在校验后显式 touch manifest：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-front-proxy-ca-bundle/playbook.yml \
  -e restart_static_pods=true
```

## 重要警告

- 这个 recipe 会修改 kube-apiserver 静态 Pod manifest。在依赖它前，应先在非生产或可完整恢复的集群上测试。
- 修改 front-proxy 信任配置前，应先备份 Kubernetes PKI 文件。
- 备份文件会写到 kubelet 静态 Pod manifest 目录之外，避免 kubelet 把备份文件也当成静态 Pod。
- 确保 CA bundle 包含 front-proxy CA 轮换窗口内所需的全部 CA。
- 除非已经验证更大批次的发布策略，否则应一次只处理一个控制平面节点。
