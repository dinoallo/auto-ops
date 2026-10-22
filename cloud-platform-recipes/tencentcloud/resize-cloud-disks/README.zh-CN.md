# 在腾讯云上批量扩容云硬盘

英文版：`README.md`

状态：已实现

这个 recipe 在控制机上执行，通过腾讯云 CBS 的 `ResizeDisk` API 批量扩容多块云硬盘。它只负责云平台侧的容量变更，不会登录 CVM，也不会修改来宾操作系统里的分区、LVM physical volume 或文件系统。

针对目标容量，这个流程具有幂等行为：

- 已经达到目标容量的磁盘会标记为 `already_at_target`
- 小于目标容量的磁盘会执行扩容
- 大于目标容量的磁盘会在提交任何扩容请求前失败
- 不会尝试缩容，因为腾讯云云硬盘容量不可减少

## 文件

- `playbook.yml`：可执行的 Ansible playbook
- `tencentcloud_resize_disks_recipe.py`：被 playbook 调用的本地 Python workflow helper

## 依赖要求

- 控制机上可用的 Ansible
- 运行 `ansible-playbook` 的同一个 Python 环境里安装好腾讯云 SDK
- 腾讯云凭据具备查询和扩容 CBS 云硬盘的权限
- 用于先验证的非生产账号或地域

把 SDK 安装到运行 `ansible-playbook` 的 Python 环境中：

```bash
python -m pip install \
  tencentcloud-sdk-python-common \
  tencentcloud-sdk-python-cbs
```

## 必填变量

所有磁盘使用同一个目标容量时：

- `disk_ids`：非空的 CBS 云硬盘 ID 列表
- `target_disk_size_gb`：`disk_ids` 中每块磁盘的目标容量，单位 GB

如果每块磁盘的目标容量不同，也可以使用：

- `disk_resize_requests`：非空对象列表，每个对象包含 `disk_id` 和 `target_size_gb`

以下变量始终必填：

- `tencentcloud_region`：目标 CBS 地域

两种输入方式不能同时使用。

## 可选变量

- `target_hosts`：执行主机组，默认 `localhost`
- `wait_for_disk_ready`：是否等待每块磁盘达到目标容量并离开 `EXPANDING` 状态，默认 `true`
- `disk_ready_timeout_seconds`：整个流程的等待超时时间，默认 `1800`
- `disk_poll_interval_seconds`：轮询间隔，默认 `10`
- `tencentcloud_secret_id`：可选的显式凭据覆盖
- `tencentcloud_secret_key`：可选的显式凭据覆盖
- `tencentcloud_token`：可选的临时凭据 token

## 认证方式

推荐在执行 playbook 前，通过当前 shell 导出凭据：

```bash
export TENCENTCLOUD_SECRET_ID=AKIDEXAMPLE
export TENCENTCLOUD_SECRET_KEY=SECRETEXAMPLE
```

如果使用临时凭据，还要设置：

```bash
export TENCENTCLOUD_TOKEN=TOKENEXAMPLE
```

凭据需要在目标地域具备以下 CBS API 权限：

- `DescribeDisks`
- `ResizeDisk`

不要把访问密钥写入并提交到变量文件。

## 用法

语法检查：

```bash
ansible-playbook -i localhost, --syntax-check \
  cloud-platform-recipes/tencentcloud/resize-cloud-disks/playbook.yml
```

把多块磁盘扩容到相同容量：

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/tencentcloud/resize-cloud-disks/playbook.yml \
  -e '{"disk_ids":["disk-111","disk-222"],"target_disk_size_gb":200,"tencentcloud_region":"ap-guangzhou"}'
```

为不同磁盘指定不同目标容量：

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/tencentcloud/resize-cloud-disks/playbook.yml \
  -e '{"disk_resize_requests":[{"disk_id":"disk-111","target_size_gb":200},{"disk_id":"disk-222","target_size_gb":500}],"tencentcloud_region":"ap-guangzhou"}'
```

如果只想提交请求、不等待云平台操作结束，可以设置
`wait_for_disk_ready=false`。此时输出状态为 `resize_submitted`，不代表磁盘已经达到目标容量。

## 输出

playbook 会输出以下结果：

- `requested_disk_count`
- `resized_count` 和 `skipped_count`
- `results[]`，包括磁盘 ID、扩容前容量、请求的目标容量、观测到的容量、云平台状态和请求 ID

## 来宾操作系统后续处理

CBS 云硬盘扩容完成后，来宾操作系统可能还需要重新扫描设备，并扩展分区、LVM volume 或文件系统。这个 recipe 有意不执行这些主机内操作。

## 校验说明和注意事项

- 支持 `--syntax-check`。
- 不支持 `--check`，因为 `ResizeDisk` 会修改云硬盘容量。
- 扩容不可逆，请在执行前确认每个目标容量。
- 多个 API 请求可能出现前面的磁盘成功、后面的请求失败的部分完成情况。重跑前请先查询磁盘状态；使用相同目标容量重跑时，已经达到目标的磁盘会被跳过。
- 请先在非生产账号或地域中验证。
