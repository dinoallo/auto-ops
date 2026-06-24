# ensure-etcdctl

确保每台 master 节点上都存在 `etcdctl`。Playbook 会先在每台目标节点的
`PATH` 中查找 `etcdctl`；已经存在的节点只有通过
`ETCDCTL_API=3 etcdctl version` 验证时才会保留。

缺失节点支持两种修复方式：

- `copy`：从 `etcdctl_host` 上复制一个已验证可用的 `etcdctl`，经由 Ansible
  控制端分发到缺失节点。默认方式，通常设置 `etcdctl_host=master0`。
- `download`：在缺失节点上从互联网下载 upstream etcd release 包，并安装其中的
  `etcdctl` 二进制。

## 用法

从源 master 复制：

```bash
ansible-playbook -i inventory.ini ansible-recipes/ensure-etcdctl/playbook.yml \
  -e etcdctl_install_method=copy \
  -e etcdctl_host=master0
```

从互联网下载：

```bash
ansible-playbook -i inventory.ini ansible-recipes/ensure-etcdctl/playbook.yml \
  -e etcdctl_install_method=download \
  -e etcdctl_download_version=v3.5.17
```

## 常用变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `target_hosts` | `masters` | 要管理的 inventory group 或 host pattern。 |
| `etcdctl_command` | `etcdctl` | 检查已有 `PATH` 时使用的命令名。 |
| `etcdctl_api` | `3` | 源节点和目标节点版本检查使用的 `ETCDCTL_API` 值。 |
| `etcdctl_install_method` | `copy` | 缺失节点的安装来源：`copy` 或 `download`。 |
| `etcdctl_install_path` | `/usr/local/bin/etcdctl` | 缺失节点安装二进制的目标路径。 |

## 复制模式变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `etcdctl_host` | `masters` 中第一台 | 已存在 `etcdctl` 的源主机。 |
| `etcdctl_source_path` | 空 | 显式指定源二进制路径；为空时在 `etcdctl_host` 上执行 `command -v etcdctl`。 |
| `etcdctl_controller_cache_dir` | `/tmp/ansible-etcdctl` | Ansible 控制端的临时缓存目录。 |

## 下载模式变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `etcdctl_download_version` | `v3.5.17` | upstream etcd release 版本。 |
| `etcdctl_download_url` | 根据版本、OS 和架构推导 | 覆盖下载 URL，可用于镜像或内部制品库。 |
| `etcdctl_download_checksum` | 空 | 传给 `get_url` 的可选 checksum，例如 `sha256:<digest>`。 |
| `etcdctl_download_os` | 远端 `ansible_system | lower` | release 包 OS 字段。 |
| `etcdctl_download_arch` | 根据 `ansible_architecture` 映射 | release 包架构字段。 |
| `etcdctl_download_tmp_dir` | `/tmp/ansible-etcdctl-download` | 每台目标节点上的临时下载目录。 |
| `etcdctl_download_cleanup` | `true` | 安装后删除临时下载目录。 |
