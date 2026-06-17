# 激活预置的 front-proxy CA

英文版：`README.md`

这个 recipe 会把预置的 Kubernetes front-proxy CA 文件提升为当前生效的 front-proxy CA 文件名，并把 kube-apiserver 的 requestheader 信任收敛回当前生效 CA。默认场景是 kubeadm 管理的控制平面，PKI 文件位于 `/etc/kubernetes/pki`。

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 使用提权权限在 `masters` inventory 组中的主机上运行，每次处理一台主机。
2. 检查预置 CA 文件、续签后的 front-proxy client 文件和 kube-apiserver manifest 是否存在。
3. 在移除 trust bundle 之前，先检查 kube-apiserver 是否已经使用预置的 front-proxy client 证书路径，除非设置 `require_staged_front_proxy_client_certs=false`。
4. 将 kube-apiserver 静态 Pod manifest 备份到 manifest 目录之外。
5. 将当前生效的 `front-proxy-ca.crt` 和 `front-proxy-ca.key` 移动为带时间戳的备份文件名。
6. 将 `front-proxy-ca-new.crt` 和 `front-proxy-ca-new.key` 移动到当前生效的 front-proxy CA 文件名。
7. 将 `--requestheader-client-ca-file` 配置为指向当前生效的 front-proxy CA 证书。
8. 打印当前生效 front-proxy CA 证书里的证书数量、subject、issuer、有效期和 SHA256 指纹。

## 要求

- kubeadm 管理的 Kubernetes 控制平面，或等价的 PKI 布局
- inventory 中存在名为 `masters` 的主机组
- `/etc/kubernetes/pki` 下已经存在当前生效的 front-proxy CA 证书和私钥
- `/etc/kubernetes/pki` 下已经存在预置的替换 front-proxy CA 证书和私钥
- `/etc/kubernetes/pki` 下已经存在续签后的 front-proxy client 证书和私钥
- kubeadm 风格的 kube-apiserver 静态 Pod manifest 位于 `/etc/kubernetes/manifests`
- 每台目标主机上可以使用 `mv`、`grep`、`awk` 和 `openssl`
- 具备 SSH 连接和提权权限，因为 PKI 文件通常归 root 所有

当 kubeadm 默认路径和预置 CA 文件名符合你的环境时，不需要额外变量。

## 可选变量

- `target_hosts`: 目标主机组，默认 `masters`
- `front_proxy_ca_rollout_serial`: 每批处理的主机数量，默认 `1`
- `manifest_dir`: 静态 Pod manifest 目录，默认 `'/etc/kubernetes/manifests'`
- `pki_dir`: Kubernetes PKI 目录，默认 `'/etc/kubernetes/pki'`
- `front_proxy_ca_active_cert`: 当前生效 CA 证书文件名，默认 `'front-proxy-ca.crt'`
- `front_proxy_ca_active_key`: 当前生效 CA 私钥文件名，默认 `'front-proxy-ca.key'`
- `front_proxy_ca_staged_cert`: 预置 CA 证书文件名，默认 `'front-proxy-ca-new.crt'`
- `front_proxy_ca_staged_key`: 预置 CA 私钥文件名，默认 `'front-proxy-ca-new.key'`
- `front_proxy_ca_backup_cert`: 备份 CA 证书文件名，默认使用带时间戳的 `front-proxy-ca-backup-*.crt`
- `front_proxy_ca_backup_key`: 备份 CA 私钥文件名，默认使用带时间戳的 `front-proxy-ca-backup-*.key`
- `front_proxy_ca_active_cert_path`: kube-apiserver 中使用的当前生效 CA 证书路径，默认 `pki_dir + '/' + front_proxy_ca_active_cert`
- `front_proxy_client_cert_path`: 预期当前使用的 front-proxy client 证书，默认 `pki_dir + '/front-proxy-client-new.crt'`
- `front_proxy_client_key_path`: 预期当前使用的 front-proxy client 私钥，默认 `pki_dir + '/front-proxy-client-new.key'`
- `kube_apiserver_manifest`: kube-apiserver manifest 路径，默认 `manifest_dir + '/kube-apiserver.yaml'`
- `require_staged_front_proxy_client_certs`: 激活 CA 前是否要求 kube-apiserver 已使用预置 client 证书，默认 `true`
- `manifest_backup_dir`: manifest 备份目录，默认 `'/etc/kubernetes/manifest-backups'`
- `manifest_backup_suffix`: 备份后缀，默认使用当前 Ansible 时间戳加 `.bak`
- `restart_static_pods`: 校验后是否 touch 已更新的 manifest，默认 `false`

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

激活第二批预置 client 证书：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/activate-front-proxy-ca/playbook.yml \
  -e front_proxy_client_cert_path=/etc/kubernetes/pki/front-proxy-client-next.crt \
  -e front_proxy_client_key_path=/etc/kubernetes/pki/front-proxy-client-next.key
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
- 这个 recipe 会改变当前生效的 front-proxy CA 文件，并更新 kube-apiserver 静态 Pod manifest。只能把它作为经过测试的证书轮换流程的一部分来执行。
- 备份文件会写到 kubelet 静态 Pod manifest 目录之外，避免 kubelet 把备份文件也当成静态 Pod。
- 这个 recipe 不会重启 kubelet。只有在 `restart_static_pods=true` 时，它才会 touch kube-apiserver 静态 Pod manifest。
- 这个 recipe 不会创建预置 CA 文件。执行前需要先生成并分发这些文件。
- 执行本 recipe 前应先运行 `configure-front-proxy-client-certs` 并确认聚合 API 行为正常。否则 playbook 默认会失败，而不是在 kube-apiserver 仍指向旧 client 证书时移除旧 CA。
- 执行前应先备份 Kubernetes PKI 文件。
