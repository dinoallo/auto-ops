# 在火山引擎上创建虚拟机磁盘快照

English version: `README.md`

状态：已实现

这个配方在控制节点上运行，发现指定 ECS 实例挂载的磁盘，并为这些磁盘创建火山引擎 EBS 快照。

支持两种模式：

- `use_consistency_group_snapshot=false`：独立磁盘快照
- `use_consistency_group_snapshot=true`：云平台原生快照一致性组

一致性组路径用于单台 ECS 实例内多磁盘的崩溃一致性捕获，不提供来宾操作系统内的应用一致性。

## 文件

- `playbook.yml`：可执行的火山引擎快照 playbook
- `volcengine_snapshot_recipe.py`：playbook 调用的本地 Python 工作流辅助脚本

## 依赖

- 控制节点上可用的 Ansible
- 与 `ansible-playbook` 相同 Python 环境中的火山引擎 SDK
- 具备查询 ECS 实例和创建 EBS 快照权限的火山引擎凭证
- 用于验证的非生产账号或区域

在运行 `ansible-playbook` 的 Python 环境中安装 SDK：

```bash
python -m pip install volcengine-python-sdk
```

## 必填变量

- `target_instances`：非空 ECS 实例 ID 列表
- `snapshot_name_prefix`：非空快照名前缀
- `volcengine_region`：ECS 实例所在区域

## 可选变量

- `target_hosts`：执行主机组，默认 `localhost`
- `include_boot_disk`：是否为启动盘创建快照，默认 `true`
- `data_disk_ids`：需要包含的数据盘 ID 列表；过滤时磁盘名也可以匹配
- `use_consistency_group_snapshot`：是否创建火山引擎快照一致性组，默认 `false`
- `wait_for_snapshot_ready`：是否等待快照完成，默认 `true`
- `snapshot_description`：可选的快照或快照组描述
- `snapshot_tags`：标签映射，例如 `{"env":"dev"}`，或 `{Key, Value}` 对象列表
- `snapshot_ready_timeout_seconds`：等待快照完成的超时时间，默认 `1800`
- `snapshot_poll_interval_seconds`：轮询间隔，默认 `10`
- `volcengine_project_name`：可选的火山引擎项目名，会传给 ECS 和 EBS API
- `volcengine_access_key`：可选的显式凭证覆盖
- `volcengine_secret_key`：可选的显式凭证覆盖
- `volcengine_session_token`：可选的临时凭证令牌

## 认证

推荐做法是在执行 playbook 前导出环境变量：

```bash
export VOLCENGINE_ACCESS_KEY=EXAMPLE
export VOLCENGINE_SECRET_KEY=EXAMPLE
```

如果使用临时凭证，再设置：

```bash
export VOLCENGINE_SESSION_TOKEN=TOKENEXAMPLE
```

也可以通过 playbook 变量传入 `volcengine_access_key`、`volcengine_secret_key` 和 `volcengine_session_token`。

## 一致性组支持

支持状态：已实现。

当前行为和约束：

- `use_consistency_group_snapshot=true` 会调用火山引擎 `CreateSnapshotGroup`
- 配方会强制要求 `target_instances | length == 1`
- 返回的是来宾崩溃一致性，不是应用一致性
- 功能可用性仍可能受账号权限和区域发布状态影响

## 使用方式

语法检查：

```bash
ansible-playbook -i localhost, --syntax-check cloud-platform-recipes/volcengine/create-vm-disk-snapshots/playbook.yml
```

为单台实例的所有磁盘创建独立快照：

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/volcengine/create-vm-disk-snapshots/playbook.yml \
  -e '{"target_instances":["i-abc12345"],"snapshot_name_prefix":"daily-20260429","volcengine_region":"cn-beijing"}'
```

为单台实例创建快照一致性组并等待完成：

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/volcengine/create-vm-disk-snapshots/playbook.yml \
  -e '{"target_instances":["i-abc12345"],"snapshot_name_prefix":"daily-20260429","volcengine_region":"cn-beijing","use_consistency_group_snapshot":true}'
```

只为指定数据盘创建快照并跳过启动盘：

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/volcengine/create-vm-disk-snapshots/playbook.yml \
  -e '{"target_instances":["i-abc12345"],"snapshot_name_prefix":"daily-20260429","volcengine_region":"cn-beijing","include_boot_disk":false,"data_disk_ids":["vol-111","vol-222"]}'
```

## 输出

playbook 会打印统一格式的结果结构，包含：

- `provider`
- `region`
- `consistency_mode`
- `consistency_group_id`
- `created_snapshot_count`
- `results[]`：其中包含实例 ID、磁盘 ID、快照 ID、快照名、状态和可用区

## 验证说明

- 支持 `--syntax-check`
- 不支持 `--check`，因为该配方会真实创建快照
- 请先在非生产账号或项目中验证

## 警告

- 这个配方会修改火山引擎快照状态。
- 快照保留与清理不在当前范围内。
- 云平台原生快照组不等同于来宾侧应用一致性。
