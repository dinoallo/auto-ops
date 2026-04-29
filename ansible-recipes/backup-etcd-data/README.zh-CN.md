# 备份 etcd 数据

英文版：`README.md`

这个 recipe 使用 `etcdctl snapshot save` 创建一个时间点一致的 etcd 快照。默认场景是 kubeadm 管理的控制平面：etcd 监听在 `https://127.0.0.1:2379`，TLS 文件位于 `/etc/kubernetes/pki/etcd`。

## 文件

- `playbook.yml`: recipe 主体

## 这个 Recipe 会做什么

1. 确保整次执行只针对一个 etcd 成员。
2. 检查目标主机上是否存在 `etcdctl` 和所需的 TLS 文件。
3. 如果远程备份目录不存在，就先创建它。
4. 使用 `ETCDCTL_API=3` 保存一个带时间戳的快照文件。
5. 验证快照文件已经生成，并且不是空文件。
6. 可选地把快照再拉回到 Ansible 控制机。

## 前置要求

- 每次执行只能针对一台目标主机
- 目标主机上可以使用 `etcdctl`
- 目标主机能够连通配置里的 etcd endpoint
- 已准备好可以访问 etcd 的 TLS CA、客户端证书和私钥
- 如果证书路径或备份目录需要 root 权限，Ansible 需要具备提权能力

如果你的环境符合 kubeadm 默认路径，这个 recipe 不需要额外传入变量。

## 可选变量

- `target_hosts`: 目标主机组，默认 `all`
- `etcd_backup_dir`: 远程保存快照的目录，默认 `'/var/backups/etcd'`
- `etcd_snapshot_basename`: 快照文件名前缀，默认 `'etcd-snapshot'`
- `etcd_endpoint`: 用于生成快照的单个 etcd endpoint，默认 `'https://127.0.0.1:2379'`
- `etcdctl_command`: `etcdctl` 的命令名或路径，默认 `'etcdctl'`
- `etcd_cacert`: etcd TLS CA 证书路径，默认 `'/etc/kubernetes/pki/etcd/ca.crt'`
- `etcd_cert`: etcd TLS 客户端证书路径，默认 `'/etc/kubernetes/pki/etcd/healthcheck-client.crt'`
- `etcd_key`: etcd TLS 客户端私钥路径，默认 `'/etc/kubernetes/pki/etcd/healthcheck-client.key'`
- `fetch_snapshot_to_controller`: 是否把快照拉回到 Ansible 控制机，默认 `false`
- `controller_snapshot_dir`: 拉回控制机时使用的本地目录，默认 `'/tmp/etcd-snapshots'`

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/backup-etcd-data/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/backup-etcd-data/playbook.yml \
  -e target_hosts=cp1
```

如果还要把快照拉回到 Ansible 控制机：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/backup-etcd-data/playbook.yml \
  -e target_hosts=cp1 \
  -e fetch_snapshot_to_controller=true \
  -e controller_snapshot_dir=/tmp/etcd-snapshots
```

如果不是 kubeadm 默认路径，或者 etcd endpoint 不一样：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/backup-etcd-data/playbook.yml \
  -e target_hosts=etcd1 \
  -e etcd_endpoint=https://10.0.0.11:2379 \
  -e etcd_cacert=/etc/etcd/pki/ca.crt \
  -e etcd_cert=/etc/etcd/pki/client.crt \
  -e etcd_key=/etc/etcd/pki/client.key
```

如果需要指定 SSH key：

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/backup-etcd-data/playbook.yml \
  -e target_hosts=cp1
```

## 重要提醒

- 快照文件里包含敏感的集群数据，应妥善保护，并在合适的场景下加密保存。
- 这个 recipe 有意限制为每次只对一个 etcd 成员生成快照。通常一份有效快照就足够用于整组 etcd 的恢复。
- 只把快照留在源主机上，不能算可靠备份。应该再拉回控制机或转存到独立存储。
- 对 kubeadm 管理的集群，建议把 etcd 的 PKI 文件和静态 Pod manifest 也一起备份，避免灾难恢复时缺少关键文件。
