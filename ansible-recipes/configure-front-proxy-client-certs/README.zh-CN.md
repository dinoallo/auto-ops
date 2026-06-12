# 配置 front-proxy Client 证书

英文版：`README.md`

这个 recipe 会更新 kube-apiserver 静态 Pod manifest，让 Kubernetes aggregation 使用的 front-proxy client 证书和私钥指向续期后的 front-proxy client 文件。

默认会为 kube-apiserver 配置：

```text
--proxy-client-cert-file=/etc/kubernetes/pki/front-proxy-client-new.crt
--proxy-client-key-file=/etc/kubernetes/pki/front-proxy-client-new.key
```

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 使用提权权限在控制平面节点上运行，默认每次处理一台主机。
2. 检查续期后的 front-proxy client 证书、私钥和 kube-apiserver manifest 是否存在。
3. 备份 kube-apiserver 静态 Pod manifest。
4. 将 `--proxy-client-cert-file` 和 `--proxy-client-key-file` 配置为指向指定的续期后文件。
5. 校验每个受管理参数只出现一次，且值符合预期。

默认情况下，这个 recipe 在编辑后不会额外 touch manifest 时间戳。kubelet 通常会检测到 manifest 内容变化并重启静态 Pod。如果希望 playbook 在校验后显式 touch manifest，可以设置 `restart_static_pods=true`。

## 要求

- kubeadm 风格的 kube-apiserver 静态 Pod manifest 位于 `/etc/kubernetes/manifests`
- inventory 中存在名为 `masters` 的主机组，除非覆盖 `target_hosts`
- 已存在续期后的 front-proxy client 证书：`/etc/kubernetes/pki/front-proxy-client-new.crt`
- 已存在续期后的 front-proxy client 私钥：`/etc/kubernetes/pki/front-proxy-client-new.key`
- 每台目标主机上可以使用 `awk`
- 具备 SSH 连接和提权权限，因为 Kubernetes manifest 和 PKI 文件通常归 root 所有

## 可选变量

- `target_hosts`: 目标主机组，默认 `masters`
- `front_proxy_client_certs_rollout_serial`: 每批处理的主机数量，默认 `1`
- `manifest_dir`: 静态 Pod manifest 目录，默认 `'/etc/kubernetes/manifests'`
- `pki_dir`: Kubernetes PKI 目录，默认 `'/etc/kubernetes/pki'`
- `front_proxy_client_cert_path`: front-proxy client 证书路径，默认 `pki_dir + '/front-proxy-client-new.crt'`
- `front_proxy_client_key_path`: front-proxy client 私钥路径，默认 `pki_dir + '/front-proxy-client-new.key'`
- `kube_apiserver_manifest`: kube-apiserver manifest 路径，默认 `manifest_dir + '/kube-apiserver.yaml'`
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
ansible-playbook --syntax-check ansible-recipes/configure-front-proxy-client-certs/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-front-proxy-client-certs/playbook.yml
```

使用自定义证书和私钥路径：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-front-proxy-client-certs/playbook.yml \
  -e front_proxy_client_cert_path=/etc/kubernetes/pki/custom-front-proxy-client.crt \
  -e front_proxy_client_key_path=/etc/kubernetes/pki/custom-front-proxy-client.key
```

在校验后显式 touch manifest：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-front-proxy-client-certs/playbook.yml \
  -e restart_static_pods=true
```

## 重要警告

- 这个 recipe 会修改 kube-apiserver 静态 Pod manifest。在依赖它前，应先在非生产或可完整恢复的集群上测试。
- 修改 front-proxy client 证书配置前，应先备份 Kubernetes PKI 文件。
- 确保配置的证书和私钥相互匹配，并且被当前 requestheader CA 配置所信任。
- 除非已经验证更大批次的发布策略，否则应一次只处理一个控制平面节点。
