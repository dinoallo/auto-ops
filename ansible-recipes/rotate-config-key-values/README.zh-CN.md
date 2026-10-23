# 轮转 TOML/YAML Key-Value

英文版：`README.md`

这个 recipe 可以在不重新渲染整个配置文件的情况下，替换已有 TOML 或 YAML 配置中的标量值，同时保留其他内容。它适合轮转 registry 凭据、密码、地址等 key/value 配置。

## 文件

- `playbook.yml`: 可执行的 recipe
- `library/replace_config_key_values.py`: Ansible module 入口
- `module_utils/config_key_value_editor.py`: 保留格式的编辑器

## 前置要求

- 控制机已安装 Ansible
- 控制机可用 PyYAML；通常安装 Ansible 时会一并安装
- 可以通过 SSH 读取和替换远程配置文件，并具备所需权限
- 目标主机使用 Ansible 支持的 Python 解释器

目标主机不需要额外安装 TOML 或 YAML 命令行工具。recipe 会从目标主机读取文件，在控制机上定位并编辑，然后通过 Ansible 的原子 copy 机制写回目标主机。

## 变量

必填变量：

- `config_file`: 要修改的远程 TOML 或 YAML 文件
- `config_format`: `toml` 或 `yaml`
- `config_updates`: 非空的更新列表

可选变量：

- `target_hosts`: 目标 inventory 组，默认是 `all`
- `config_become`: 是否提权，默认是 `true`
- `backup_on_replace`: 替换前是否创建 Ansible 备份，默认是 `true`

每个 update 都包含路径列表和值：

```yaml
config_updates:
  - path:
      - top_level_key
      - nested_key
    value: "new value"
```

路径中的字符串表示 mapping key。值可以是字符串、布尔值、整数、浮点数；YAML 还支持 `null`。TOML 不支持 `null`。

### 选择 YAML 列表元素

可以用 `select` 按列表元素中的标量字段进行精确匹配。当 registry 顺序可能变化时，这比依赖列表下标更安全：

```yaml
config_updates:
  - path:
      - registries
      - select:
          address: "https://hub.usw-1.sealos.io"
      - auth
    value: "{{ registry_username }}:{{ registry_password }}"
```

只有当列表位置本身就是配置约定时，才使用 `index`：

```yaml
config_updates:
  - path:
      - registries
      - index: 0
      - auth
    value: "{{ registry_username }}:{{ registry_password }}"
```

selector 必须恰好匹配一个列表元素。如果匹配不到或匹配到多个元素，recipe 会在写文件前失败。

## TOML 示例

对于下面的配置：

```toml
[plugins."io.containerd.grpc.v1.cri".registry.configs."sealos.hub:5000".auth]
username = "admin"
password = "passw0rd"
```

每个 TOML key 使用一个路径片段。包含点号或冒号的带引号 TOML key 仍然要作为一个路径片段：

```yaml
config_file: /etc/containerd/config.toml
config_format: toml
config_updates:
  - path:
      - plugins
      - io.containerd.grpc.v1.cri
      - registry
      - configs
      - sealos.hub:5000
      - auth
      - password
    value: "{{ registry_password }}"
```

一次执行也可以更新多个值，例如同时更新同一个 table 下的 `username` 和 `password`。

## YAML 示例

对于下面的配置：

```yaml
registries:
  - address: https://hub.usw-1.sealos.io
    auth: admin:anotherpassw0rd
```

可以先按 registry 选择元素，再替换其中的 `auth` 标量值：

```yaml
config_file: /etc/registry/config.yaml
config_format: yaml
config_updates:
  - path:
      - registries
      - select:
          address: "https://hub.usw-1.sealos.io"
      - auth
    value: "{{ registry_username }}:{{ registry_password }}"
```

新字符串会输出为经过安全转义的双引号标量；已有注释和周围排版会保留。

## 用法

建议把凭据放在由 Ansible Vault 加密的变量文件中，不要直接写在命令行：

```bash
ansible-vault encrypt rotate-registry-vars.yml

ansible-playbook \
  -i inventory.ini \
  --ask-vault-pass \
  -e @rotate-registry-vars.yml \
  ansible-recipes/rotate-config-key-values/playbook.yml
```

先用 check mode 检查计划中的修改：

```bash
ansible-playbook \
  -i inventory.ini \
  --check \
  -e @rotate-registry-vars.yml \
  ansible-recipes/rotate-config-key-values/playbook.yml
```

编辑和写文件任务都使用 `no_log`，正常 Ansible 输出不会打印新凭据。凭据更新时不要使用 `--diff`。

## 行为和限制

- 每个路径必须恰好解析到一个标量值。如果 key 缺失或匹配不唯一，recipe 会在写文件前失败。
- YAML 使用 PyYAML 的节点位置定位，但只写回选中的标量片段，因此会保留注释和周围排版。
- YAML 输入必须只有一个 document。不支持作为目标的多行值。
- 支持 TOML table 路径和带引号的 key。目标 assignment 必须位于单行，并且只能出现一次。
- recipe 会保留原文件的 owner、group 和 mode，并使用 Ansible 原子的 `copy` 操作。
- 默认启用备份；只有在其他地方负责备份时才设置 `backup_on_replace: false`。
- recipe 只修改配置文件；验证新凭据后，请单独重启或 reload 对应服务。

## 验证

执行前先做语法检查：

```bash
ansible-playbook --syntax-check ansible-recipes/rotate-config-key-values/playbook.yml
```

请先在非生产 inventory 上测试，先使用 `--check`，然后确认受影响服务能够接受生成的配置，再重启服务。
