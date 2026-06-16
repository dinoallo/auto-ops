# 配置 kubepods IO 限速

英文版：`README.md`

这个 recipe 会为 `kubepods.slice` 安装持久化的 cgroup v2 IO 限速配置。它会在 `/sys/fs/cgroup/kubepods.slice/io.max` 存在后，写入类似 `252:0 rbps=104857600 wbps=52428800` 的限速规则。

playbook 使用 `systemd.path` 监听 `kubepods.slice/io.max`，文件出现后再触发 oneshot service 写入限速规则。这样可以避开 udev rule 执行时 kubelet 或 systemd 还没有创建 `kubepods.slice` 的竞态问题。

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 接受块设备路径，例如 `/dev/vda`，或显式的 `major:minor` 值，例如 `252:0`。
2. 使用 `io_limit_device` 时，在每台目标主机上把设备路径解析成 `major:minor`。
3. 安装 `/usr/local/sbin/set-kubepods-io-limit.sh`。
4. 安装 `kubepods-io-limit.service`。service 使用 `RemainAfterExit=true`，成功执行一次后会保持 active，避免被 `PathExists` 反复触发。
5. 安装并启用 `kubepods-io-limit.path`，等待 `/sys/fs/cgroup/kubepods.slice/io.max` 出现后再运行 service。

## 要求

- 使用 cgroup v2 的 Linux 主机
- 由 systemd 管理的 Kubernetes 节点，并且 kubelet 会创建 `kubepods.slice`
- 具备提权能力的 SSH 访问
- 目标主机上有 `bash`、`stat`、`logger` 和 `systemd`

## 必填变量

设置以下变量之一：

- `io_limit_device`: 目标主机上的块设备路径，例如 `/dev/vda`
- `io_limit_major_minor`: 显式的 cgroup 设备选择器，例如 `252:0`

如果两个变量都设置，优先使用 `io_limit_major_minor`。

## 可选变量

- `target_hosts`: inventory 主机匹配模式，默认是 `all`
- `io_limit_rbps`: 读限速，单位是 bytes per second，默认是 `104857600`
- `io_limit_wbps`: 写限速，单位是 bytes per second，默认是 `52428800`
- `io_limit_cgroup_io_max`: cgroup 控制文件，默认是 `/sys/fs/cgroup/kubepods.slice/io.max`
- `io_limit_script_path`: 安装的脚本路径，默认是 `/usr/local/sbin/set-kubepods-io-limit.sh`
- `io_limit_systemd_unit_name`: systemd unit 基础名称，默认是 `kubepods-io-limit`
- `io_limit_run_immediately`: playbook 执行期间是否也立即启动 oneshot service，默认是 `false`

## 用法

执行前先做语法检查：

```bash
ansible-playbook --syntax-check ansible-recipes/configure-kubepods-io-limit/playbook.yml
```

用块设备路径执行：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-kubepods-io-limit/playbook.yml \
  -e io_limit_device=/dev/vda
```

用显式的 `major:minor` 执行：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-kubepods-io-limit/playbook.yml \
  -e io_limit_major_minor=252:0
```

覆盖 IO 限速值：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/configure-kubepods-io-limit/playbook.yml \
  -e io_limit_device=/dev/vda \
  -e io_limit_rbps=104857600 \
  -e io_limit_wbps=52428800
```

## 说明

- 脚本使用 `>` 写入 `io.max`，而不是 `>>`，因为 cgroup 控制文件会把每次写入当作一条配置命令处理。
- `io_limit_run_immediately` 默认是 `false`，避免在 `kubepods.slice` 尚未创建的节点上让 playbook 等待最多 300 秒。
- playbook 会用 `systemctl reset-failed` 清理之前可能出现的 `kubepods-io-limit.service` 的 `start-limit-hit` 状态。
- 如果设备名可能在重启后变化，建议使用 `/dev/disk/by-id/...` 这类稳定设备路径。
