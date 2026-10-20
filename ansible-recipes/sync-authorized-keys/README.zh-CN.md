# 同步 SSH Authorized Keys

English version: `README.md`

这个 recipe 会把指定账号的 SSH authorized keys 收敛为同一组公钥，并同步到
所有选中的目标节点。公钥可以直接通过变量传入，也可以从 Ansible 控制机上的
文件读取。

## 文件

- `playbook.yml`: recipe 主体

## 这个 Recipe 会做什么

1. 校验只提供了一种 authorized key 来源。
2. 使用本地文件时，从 Ansible 控制机读取并规范化公钥内容。
3. 需要时创建目标用户的 `.ssh` 目录。
4. 按一次一台主机的方式同步每个目标节点上的 authorized keys。

默认情况下 `authorized_keys_exclusive` 为 `true`，不在输入集合中的旧 key 会被
移除。如果只希望确保指定 key 存在、保留其他已有 key，请设置为 `false`。

## 前置要求

- 安装了 `ansible.posix` collection 的 Ansible
- 可以通过 SSH 访问目标节点
- 如果管理其他用户（例如默认的 `root`），目标节点需要具备提权权限
- 一份每行一个 OpenSSH 公钥的文件，或通过变量传入公钥字符串/列表

## 变量

- `target_hosts`: inventory 主机模式，默认 `'all'`
- `authorized_keys`: 一个 OpenSSH 公钥字符串或公钥列表；不能与
  `authorized_keys_file` 同时使用
- `authorized_keys_file`: Ansible 控制机上的本地文件路径，文件包含要同步的
  公钥；不能与 `authorized_keys` 同时使用
- `authorized_key_user`: 要管理 authorized keys 的账号，默认 `'root'`
- `authorized_keys_path`: 可选的远程目标路径；不设置时由
  `ansible.posix.authorized_key` 使用目标用户的默认路径
- `authorized_keys_exclusive`: 是否移除输入集合之外的 key，默认 `true`
- `authorized_keys_manage_dir`: 需要时是否创建目标用户的 `.ssh` 目录，默认
  `true`

## 用法

校验 playbook 语法：

```bash
ansible-playbook --syntax-check ansible-recipes/sync-authorized-keys/playbook.yml
```

推荐把公钥保存在 Ansible 控制机的本地文件中，每行一个 key：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/sync-authorized-keys/playbook.yml \
  -e target_hosts=all \
  -e authorized_keys_file=./files/cluster-authorized_keys
```

管理非 root 账号：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/sync-authorized-keys/playbook.yml \
  -e target_hosts=workers \
  -e authorized_key_user=deploy \
  -e authorized_keys_file=./files/deploy-authorized_keys
```

直接传入少量公钥：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/sync-authorized-keys/playbook.yml \
  -e '{"authorized_keys":["ssh-ed25519 AAAA... operator@example"]}'
```

只添加指定 key，同时保留其他已有 key：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/sync-authorized-keys/playbook.yml \
  -e authorized_keys_file=./files/additional-authorized_keys \
  -e authorized_keys_exclusive=false
```

## 重要提醒

- 如果使用 exclusive 同步，请把当前 Ansible 连接使用的 SSH 公钥保留在同步集合
  中，否则下一次连接可能失败。
- `authorized_keys_file` 从 Ansible 控制机读取，不是从目标节点读取。
- 这个 recipe 只管理公钥，不会生成、复制或删除私钥。
- 使用 `authorized_keys_exclusive=true` 前请检查 key 文件，因为未纳入集合的其他
  访问方式可能会被移除。
