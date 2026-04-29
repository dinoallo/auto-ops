# 在腾讯云上创建虚拟机磁盘快照

英文版：`README.md`

状态：已实现

这个 recipe 在控制机上执行，发现显式指定的 CVM 实例在同一 region 下所挂载的磁盘，并为这些磁盘创建腾讯云 CBS 快照。

支持两种模式：

- `use_consistency_group_snapshot=false` 时，为每块磁盘分别创建快照
- `use_consistency_group_snapshot=true` 时，走腾讯云原生快照组路径

快照组路径用于同一台 CVM 实例内多盘的 crash-consistent 捕获，不提供来宾机内部应用一致性。

## 文件

- `playbook.yml`: 可执行的腾讯云快照 playbook
- `tencentcloud_snapshot_recipe.py`: 被 playbook 调用的本地 Python workflow helper

## 依赖要求

- 控制机上可用的 Ansible
- 运行 `ansible-playbook` 的同一个 Python 环境里安装好腾讯云 SDK
- 具备查询 CVM 实例和创建 CBS 快照权限的腾讯云凭据
- 用于先验证的非生产账号或地域

把下面这些 SDK 包安装到运行 `ansible-playbook` 的 Python 环境中：

```bash
python -m pip install \
  tencentcloud-sdk-python-common \
  tencentcloud-sdk-python-cvm \
  tencentcloud-sdk-python-cbs
```

## 必填变量

- `target_instances`: 非空的 CVM 实例 ID 列表
- `snapshot_name_prefix`: 非空的快照名称前缀
- `tencentcloud_region`: 目标 CVM 所在 region

## 可选变量

- `target_hosts`: 执行主机组，默认 `localhost`
- `include_boot_disk`: 是否包含系统盘，默认 `true`
- `data_disk_ids`: 需要包含的已挂载数据盘 ID 列表；不传时表示包含全部已挂载数据盘
- `use_consistency_group_snapshot`: 是否创建腾讯云快照组，默认 `false`
- `wait_for_snapshot_ready`: 是否等待直到快照进入 `NORMAL`，默认 `true`
- `snapshot_tags`: 标签映射，例如 `{"env":"dev"}`，或者 `{Key, Value}` 对象列表
- `snapshot_ready_timeout_seconds`: 等待快照完成的超时时间，默认 `1800`
- `snapshot_poll_interval_seconds`: 等待期间的轮询间隔，默认 `10`
- `tencentcloud_secret_id`: 可选的显式凭据覆盖
- `tencentcloud_secret_key`: 可选的显式凭据覆盖
- `tencentcloud_token`: 可选的临时凭据 token

## 不支持的变量

- `snapshot_description`: 当前 recipe 使用的腾讯云快照 API 不支持这个字段，因此 playbook 会直接拒绝。

## 认证方式

推荐做法：在运行 playbook 之前，先在当前 shell 中导出凭据。

```bash
export TENCENTCLOUD_SECRET_ID=AKIDEXAMPLE
export TENCENTCLOUD_SECRET_KEY=SECRETEXAMPLE
```

如果使用临时凭据，还要额外设置：

```bash
export TENCENTCLOUD_TOKEN=TOKENEXAMPLE
```

也可以把 `tencentcloud_secret_id`、`tencentcloud_secret_key`、`tencentcloud_token` 作为 playbook 变量传入，但对于本地执行场景，优先使用环境变量通常更干净。

## 一致性组支持情况

支持状态：已实现。

当前行为和限制：

- `use_consistency_group_snapshot=true` 时会调用腾讯云 `CreateSnapshotGroup`
- 所选磁盘必须挂载在同一台 CVM 实例上
- recipe 会对快照组模式强制校验 `target_instances | length == 1`
- 得到的是来宾机 crash consistency，不是应用一致性
- 具体能力是否可用，仍可能受腾讯云账号或地域发布状态影响

## 用法

语法检查：

```bash
ansible-playbook -i localhost, --syntax-check cloud-platform-recipes/tencentcloud/create-vm-disk-snapshots/playbook.yml
```

为一台实例挂载的所有磁盘创建独立快照：

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/tencentcloud/create-vm-disk-snapshots/playbook.yml \
  -e '{"target_instances":["ins-abc12345"],"snapshot_name_prefix":"daily-20260428","tencentcloud_region":"ap-guangzhou"}'
```

为单台实例创建快照组并等待完成：

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/tencentcloud/create-vm-disk-snapshots/playbook.yml \
  -e '{"target_instances":["ins-abc12345"],"snapshot_name_prefix":"daily-20260428","tencentcloud_region":"ap-guangzhou","use_consistency_group_snapshot":true}'
```

只为指定已挂载数据盘创建快照，并跳过系统盘：

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/tencentcloud/create-vm-disk-snapshots/playbook.yml \
  -e '{"target_instances":["ins-abc12345"],"snapshot_name_prefix":"daily-20260428","tencentcloud_region":"ap-guangzhou","include_boot_disk":false,"data_disk_ids":["disk-111","disk-222"]}'
```

## 输出

playbook 会输出统一格式的结果结构，包含例如：

- `provider`
- `region`
- `consistency_mode`
- `consistency_group_id`
- `created_snapshot_count`
- `results[]`，其中包括 instance ID、disk ID、snapshot ID、snapshot name、state 和 zone

## 校验说明

- 支持 `--syntax-check`
- 不支持 `--check`，因为这个 recipe 会真正创建快照
- 功能验证应先在非生产账号或项目中完成

## 注意

- 这个 recipe 会修改腾讯云快照状态。
- 快照保留和清理不在当前范围内。
- 云平台原生快照组不等于来宾机内部应用一致性。
