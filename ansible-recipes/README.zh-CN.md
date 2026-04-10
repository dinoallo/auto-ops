# Ansible Recipes

英文版：`README.md`

这个目录存放可直接执行的 Ansible recipe。每个 recipe 一般是一个独立目录，里面至少包含：

- `playbook.yml`: 可执行的 playbook
- `README.md`: recipe 的用途、变量和示例

## 使用前准备

执行 recipe 前，需要先准备：

1. 已安装 `ansible-playbook`
2. 一份可用的 inventory，例如 `inventory.ini`
3. 可以连接到目标主机的 SSH 配置和权限

一个最基本的执行形式是：

```bash
ansible-playbook \
  -i inventory.ini \
  path/to/playbook.yml \
  -e key=value
```

## 当前可用的 Recipes

### safely-copying-files

路径：`ansible-recipes/safely-copying-files/playbook.yml`

用途：把控制机上的一个本地文件复制到远程机器，并且在覆盖已有不同文件之前先询问用户确认。

行为：

1. 本地源文件不存在时，直接失败
2. 远程目标文件不存在时，直接复制
3. 远程目标文件存在且内容一致时，跳过
4. 远程目标文件存在且内容不一致时，提示是否覆盖

必填变量：

- `source_file`: 控制机上的本地文件路径
- `dest_file`: 远程机器上的目标文件路径

可选变量：

- `target_hosts`: 目标主机组，默认 `all`
- `checksum_algorithm`: 比较文件内容时使用的哈希算法，默认 `sha256`
- `backup_on_replace`: 确认覆盖时是否备份原文件，默认 `false`
- `safe_copy_owner`: 复制后的 owner
- `safe_copy_group`: 复制后的 group
- `safe_copy_mode`: 复制后的 mode

示例：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/safely-copying-files/playbook.yml \
  -e source_file=./files/app.conf \
  -e dest_file=/etc/myapp/app.conf \
  -e target_hosts=web
```

如果要在覆盖时保留远程原文件备份：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/safely-copying-files/playbook.yml \
  -e source_file=./files/app.conf \
  -e dest_file=/etc/myapp/app.conf \
  -e target_hosts=web \
  -e backup_on_replace=true
```

如果远程文件已存在且内容不同，执行时会提示确认。只有输入 `yes` 或 `y` 才会继续覆盖，其他输入都会跳过。

更详细的说明见 `ansible-recipes/safely-copying-files/README.md`。
