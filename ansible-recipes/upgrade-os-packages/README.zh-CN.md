# 升级 Ubuntu 系统软件包

英文版：`README.md`

这个 recipe 使用 `apt` 升级 Ubuntu 主机上已经安装的操作系统软件包。当前只支持 Ubuntu，并且默认一次只处理一台主机，以降低软件包变更和可选重启带来的影响范围。

## 文件

- `playbook.yml`: recipe 主体

## 这个 Recipe 会做什么

1. 校验目标主机确实是使用 `apt` 的 Ubuntu 系统。
2. 刷新本地 apt 软件包索引。
3. 默认执行一次常规的软件包升级。
4. 可选执行 `autoremove` 和 `autoclean`。
5. 升级后检查 `/var/run/reboot-required` 是否存在。
6. 当检测到需要重启时，可选自动重启主机。

## 前置要求

- 目标主机是 Ubuntu
- Ansible 控制机可以通过 SSH 访问目标主机
- 执行软件包升级和可选重启所需的提权权限
- 目标主机能够访问其配置好的 Ubuntu 软件源

基础执行不需要额外变量。

## 可选变量

- `target_hosts`: 目标主机组，默认 `all`
- `upgrade_mode`: apt 升级模式，只允许 `yes` 和 `dist`，默认 `yes`
- `apt_cache_valid_time`: apt 元数据在多少秒内视为仍然有效，默认 `3600`
- `apt_lock_timeout`: 等待 apt/dpkg 锁的秒数，默认 `300`
- `autoremove_packages`: 是否执行 `apt autoremove`，默认 `false`
- `autoclean_packages`: 是否执行 `apt autoclean`，默认 `false`
- `reboot_if_required`: 当存在 `/var/run/reboot-required` 时是否自动重启，默认 `false`
- `reboot_timeout`: 重启后等待主机恢复连接的秒数，默认 `1800`

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/upgrade-os-packages/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/upgrade-os-packages/playbook.yml \
  -e target_hosts=ubuntu
```

如果要按 `dist-upgrade` 语义升级，并清理不再需要的软件包：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/upgrade-os-packages/playbook.yml \
  -e target_hosts=ubuntu \
  -e upgrade_mode=dist \
  -e autoremove_packages=true
```

如果升级后需要自动重启：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/upgrade-os-packages/playbook.yml \
  -e target_hosts=ubuntu \
  -e reboot_if_required=true
```

如果需要指定 SSH key：

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/upgrade-os-packages/playbook.yml \
  -e target_hosts=ubuntu
```

## 重要提醒

- 当前这个 recipe 只支持 Ubuntu，遇到其他 Linux 发行版会直接失败。
- playbook 使用 `serial: 1`，默认按主机逐台升级。
- `upgrade_mode=dist` 可能会为了满足依赖而安装或移除软件包，使用前应明确接受这个行为。
- 默认情况下，即使升级后留下 `/var/run/reboot-required`，recipe 也不会自动重启主机。
