# Safely Copying Files

英文版：`README.md`

这个 recipe 会把控制机上的一个本地文件复制到远程机器，并按下面的规则执行：

1. 先检查本地源文件是否存在，不存在则直接失败。
2. 如果远程目标文件不存在，直接复制。
3. 如果远程目标文件存在且内容一致，不做任何改动。
4. 如果远程目标文件存在且内容不一致，提示用户确认是否覆盖。

由于这个 recipe 需要交互确认，它会按主机顺序执行，避免多台机器同时弹出确认提示。

## 文件

- `playbook.yml`: recipe 主体

## 需要传入的变量

- `source_file`: 控制机上的本地文件路径，必填
- `dest_file`: 远程机器上的目标文件路径，必填

## 可选变量

- `target_hosts`: 目标主机组，默认 `all`
- `checksum_algorithm`: 用于比较文件内容的哈希算法，默认 `sha256`
- `backup_on_replace`: 当确认覆盖时，是否为远程原文件创建备份，默认 `false`
- `safe_copy_owner`: 复制后设置的 owner
- `safe_copy_group`: 复制后设置的 group
- `safe_copy_mode`: 复制后设置的 mode

## 用法示例

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/safely-copying-files/playbook.yml \
  -e source_file=./files/app.conf \
  -e dest_file=/etc/myapp/app.conf \
  -e target_hosts=web
```

如果要指定连接使用的 SSH key：

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/safely-copying-files/playbook.yml \
  -e source_file=./files/app.conf \
  -e dest_file=/etc/myapp/app.conf \
  -e target_hosts=web
```

如果目标文件已存在且内容不同，playbook 会在执行时询问：

```text
host.example.com already has /etc/myapp/app.conf with different contents.
Replace it with ./files/app.conf? Type 'yes' to continue
```

只有输入 `yes` 或 `y` 才会执行覆盖，其他输入都会跳过。
