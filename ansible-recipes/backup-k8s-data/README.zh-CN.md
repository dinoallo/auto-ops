# 备份 Kubernetes PKI 和控制平面配置

英文版：`README.md`

这个 recipe 会在远程主机上创建一个带时间戳的 kubeadm 风格 Kubernetes 控制平面文件备份。它会在 `masters` inventory 组中的主机上打包 Kubernetes PKI 目录、kubeconfig 文件和静态 Pod manifest。

## 文件

- `playbook.yml`: recipe 主体

## 这个 Recipe 会做什么

1. 使用提权权限在 `masters` inventory 组中的主机上运行。
2. 创建一个带时间戳的备份目录，默认路径类似 `/root/k8s-pki-rotation-<timestamp>`。
3. 将 `/etc/kubernetes/pki` 打包为 `kubernetes-pki.tgz`。
4. 将 `/etc/kubernetes/*.conf` 和 `/etc/kubernetes/manifests` 打包为 `kubernetes-config.tgz`。
5. 将生成归档的 SHA-256 校验和写入 `SHA256SUMS`。

## 前置要求

- 目标节点采用 kubeadm 管理的 Kubernetes 控制平面目录结构
- inventory 中存在名为 `masters` 的主机组
- 每台目标 master 节点上都存在 `/etc/kubernetes/pki`
- 每台目标 master 节点上都存在 `/etc/kubernetes/*.conf` 和 `/etc/kubernetes/manifests`
- 每台目标主机上都可以使用 `tar` 和 `sha256sum`
- Ansible 具备 SSH 连接和提权能力，因为默认源路径和备份路径通常归 root 所有

如果你的环境符合默认路径，这个 recipe 不需要额外传入变量。

## 可选变量

- `backup_dir`: 远程保存归档文件的目录，默认 `'/root/k8s-pki-rotation-{{ ansible_date_time.iso8601_basic_short }}'`

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/backup-k8s-data/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/backup-k8s-data/playbook.yml
```

如果要把备份写入自定义远程目录：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/backup-k8s-data/playbook.yml \
  -e backup_dir=/var/backups/kubernetes/control-plane-files
```

如果需要指定 SSH key：

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/backup-k8s-data/playbook.yml
```

## 重要提醒

- 生成的归档中包含私钥和 kubeconfig 文件，应妥善保护，并在合适的场景下加密保存。
- 这个 recipe 只会把备份保存在远程目标主机上。真正用于灾难恢复时，应再复制到独立、持久的存储位置。
- 这个 recipe 不会创建 etcd 快照。如果还需要备份 etcd 数据，请使用 `ansible-recipes/backup-etcd-data/playbook.yml`。
- 在证书轮换或灾难恢复流程中依赖这套备份前，请先验证归档文件可以被正确恢复。
