# 配置 Kubernetes CA Bundle 参数

英文版：`README.md`

这个 recipe 会更新 kubeadm 风格的 kube-apiserver 和 kube-controller-manager 静态 Pod manifest，让它们使用 Kubernetes root CA bundle，同时让 kube-apiserver 信任当前和新的 ServiceAccount 公钥。

默认会为 kube-apiserver 配置：

```text
--client-ca-file=/etc/kubernetes/pki/ca-bundle-<renewal_id>.crt
--service-account-key-file=/etc/kubernetes/pki/sa.pub
--service-account-key-file=/etc/kubernetes/pki/sa-new-<renewal_id>.pub
--service-account-signing-key-file=/etc/kubernetes/pki/sa.key
```

会为 kube-controller-manager 配置：

```text
--root-ca-file=/etc/kubernetes/pki/ca-bundle-<renewal_id>.crt
--cluster-signing-cert-file=/etc/kubernetes/pki/ca.crt
--cluster-signing-key-file=/etc/kubernetes/pki/ca.key
--service-account-private-key-file=/etc/kubernetes/pki/sa.key
```

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 使用提权权限在控制平面节点上运行，默认每次处理一台主机。
2. 检查必需的 Kubernetes PKI 文件和静态 Pod manifest 是否存在。
3. 默认把 kube-apiserver 和 kube-controller-manager 静态 Pod manifest 备份到 `/etc/kubernetes/manifest-backups`。
4. 重写受管理的 kube-apiserver 命令参数，并保留两个 `--service-account-key-file` 条目。
5. 重写受管理的 kube-controller-manager 命令参数。
6. 校验每个受管理参数都符合预期。
7. touch manifest 后，可选等待 kube-apiserver 和 kube-controller-manager Ready。

默认情况下，这个 recipe 在编辑后不会额外 touch manifest 时间戳。kubelet 通常会检测到 manifest 内容变化并重启静态 Pod。如果希望 playbook 在校验后显式 touch manifest，可以设置 `restart_static_pods=true`。

## 要求

- kubeadm 风格的静态 Pod manifest 位于 `/etc/kubernetes/manifests`
- inventory 中存在名为 `masters` 的主机组，除非覆盖 `target_hosts`
- `/etc/kubernetes/pki` 下已存在这些 PKI 文件：`ca-bundle-<renewal_id>.crt`、`ca.crt`、`ca.key`、`sa.pub`、`sa-new-<renewal_id>.pub` 和 `sa.key`
- 每台目标主机上有 Python 3
- 具备 SSH 连接和提权权限，因为 Kubernetes manifest 和 PKI 文件通常归 root 所有

## 可选变量

- `target_hosts`: 目标主机组，默认 `masters`
- `k8s_ca_bundle_rollout_serial`: 每批处理的主机数量，默认 `1`
- `manifest_dir`: 静态 Pod manifest 目录，默认 `'/etc/kubernetes/manifests'`
- `pki_dir`: Kubernetes PKI 目录，默认 `'/etc/kubernetes/pki'`
- `renewal_id`: 预置文件名中的日期或类日期 ID，默认 `YYYYMMDD`
- `ca_bundle_path`: root CA bundle 路径，默认 `pki_dir + '/ca-bundle-<renewal_id>.crt'`
- `ca_cert_path`: root CA 证书路径，默认 `pki_dir + '/ca.crt'`
- `ca_key_path`: root CA 私钥路径，默认 `pki_dir + '/ca.key'`
- `service_account_public_key_path`: 当前 ServiceAccount 公钥路径，默认 `pki_dir + '/sa.pub'`
- `service_account_new_public_key_path`: 新 ServiceAccount 公钥路径，默认 `pki_dir + '/sa-new-<renewal_id>.pub'`
- `service_account_signing_key_path`: ServiceAccount 签名私钥路径，默认 `pki_dir + '/sa.key'`
- `service_account_private_key_path`: controller-manager 使用的 ServiceAccount 私钥路径，默认 `service_account_signing_key_path`
- `kube_apiserver_manifest`: kube-apiserver manifest 路径，默认 `manifest_dir + '/kube-apiserver.yaml'`
- `kube_controller_manager_manifest`: kube-controller-manager manifest 路径，默认 `manifest_dir + '/kube-controller-manager.yaml'`
- `manifest_backup_dir`: manifest 备份目录，默认 `'/etc/kubernetes/manifest-backups'`
- `manifest_backup_suffix`: 备份后缀，默认使用当前 Ansible 时间戳加 `.bak`
- `restart_static_pods`: 校验后是否 touch 已更新的 manifest，默认 `false`
- `wait_static_pods`: 是否等待重启后的静态 Pod Ready，默认跟随 `restart_static_pods`
- `kubeconfig`: readiness 检查使用的 kubeconfig，默认 `'/etc/kubernetes/admin.conf'`
- `python_interpreter`: 目标主机上使用的 Python 解释器，默认 `'/usr/bin/python3'`

inventory 示例：

```ini
[masters]
cp1
cp2
cp3
```

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/configure-k8s-ca-bundle/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-k8s-ca-bundle/playbook.yml
```

在校验后显式 touch manifest：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-k8s-ca-bundle/playbook.yml \
  -e restart_static_pods=true
```

确认所有 API server 都已经信任 `ca-bundle-<renewal_id>.crt` 和新旧两个 ServiceAccount 公钥后，可以用同一个 playbook 把后续证书签发和 token 签发切到预置的新材料，同时继续保持兼容期信任：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-k8s-ca-bundle/playbook.yml \
  -e renewal_id=${RENEWAL_ID} \
  -e ca_cert_path=/etc/kubernetes/pki/ca-new-${RENEWAL_ID}.crt \
  -e ca_key_path=/etc/kubernetes/pki/ca-new-${RENEWAL_ID}.key \
  -e service_account_signing_key_path=/etc/kubernetes/pki/sa-new-${RENEWAL_ID}.key \
  -e service_account_private_key_path=/etc/kubernetes/pki/sa-new-${RENEWAL_ID}.key \
  -e restart_static_pods=true
```

## 重要警告

- 这个 recipe 会修改控制平面的静态 Pod manifest。在依赖它前，应先在非生产或可完整恢复的集群上测试。
- 修改 CA 和 ServiceAccount 信任配置前，应先备份 Kubernetes PKI 文件。
- 确保 CA bundle 包含 CA 轮换窗口内所需的全部 root CA。
- 执行这个 playbook 前，确保 `sa-new-<renewal_id>.pub` 已经存在。
- 除非已经验证更大批次的发布策略，否则应一次只处理一个控制平面节点。
