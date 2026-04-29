# 在 GCP 上创建虚拟机磁盘快照

English version: `README.md`

状态：已实现

这个配方在控制节点上运行，发现指定 Compute Engine 实例挂载的磁盘，并为这些磁盘创建 GCP 磁盘快照。

只支持一种模式：

- `use_consistency_group_snapshot=false`：独立磁盘快照

GCP 标准磁盘快照不提供云平台原生的一致性组快照能力。如果需要多磁盘崩溃一致性捕获，应单独实现基于 machine image 的工作流，而不是在这个磁盘快照配方里处理。

## 文件

- `playbook.yml`：可执行的 GCP 快照 playbook
- `gcp_snapshot_recipe.py`：playbook 调用的本地 Python 工作流辅助脚本

## 依赖

- 控制节点上可用的 Ansible
- 与 `ansible-playbook` 相同 Python 环境中的 Google Cloud Compute SDK
- 具备查询 Compute Engine 实例和创建快照权限的 GCP 凭证
- 用于验证的非生产项目

在运行 `ansible-playbook` 的 Python 环境中安装 SDK：

```bash
python -m pip install google-cloud-compute google-auth
```

## 必填变量

- `target_instances`：非空实例引用列表
- `snapshot_name_prefix`：非空快照名前缀
- `gcp_project_id`：目标 Google Cloud 项目 ID

支持的 `target_instances` 格式：

- 实例名，前提是在项目内跨可用区唯一
- `zone/name`
- 完整实例 self-link

## 可选变量

- `target_hosts`：执行主机组，默认 `localhost`
- `include_boot_disk`：是否为启动盘创建快照，默认 `true`
- `data_disk_ids`：需要包含的数据盘标识列表；磁盘名、数字磁盘 ID 和 self-link 都可以匹配
- `wait_for_snapshot_ready`：是否等待快照到达 `READY`，默认 `true`
- `snapshot_description`：可选的快照描述
- `snapshot_tags`：映射或 `{Key, Value}` 对象列表；这个配方会把它们写成 GCP snapshot labels
- `snapshot_ready_timeout_seconds`：等待快照完成的超时时间，默认 `1800`
- `snapshot_poll_interval_seconds`：轮询间隔，默认 `10`
- `gcp_credentials_file`：可选的服务账号 JSON 凭证文件路径

## 不支持的变量

- `use_consistency_group_snapshot`：这个配方会拒绝 `true`，因为 GCP 标准快照不支持云平台原生一致性组快照

## 认证

推荐做法：使用 Application Default Credentials。

```bash
gcloud auth application-default login
```

如果是本地使用服务账号 JSON 文件：

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

也可以通过 playbook 变量传入 `gcp_credentials_file`。

## 范围说明

当前行为和约束：

- 配方会为每个选中的磁盘分别创建一个快照
- 同时支持已挂载的 zonal 和 regional 持久磁盘
- 没有关联持久磁盘源的挂载盘会被忽略
- 结果只提供逐盘快照输出，不提供原生多磁盘一致性组模式

## 使用方式

语法检查：

```bash
ansible-playbook -i localhost, --syntax-check cloud-platform-recipes/gcp/create-vm-disk-snapshots/playbook.yml
```

按实例名为单台实例的所有磁盘创建独立快照：

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/gcp/create-vm-disk-snapshots/playbook.yml \
  -e '{"target_instances":["app-1"],"snapshot_name_prefix":"daily-20260429","gcp_project_id":"example-project"}'
```

使用分区引用创建独立快照：

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/gcp/create-vm-disk-snapshots/playbook.yml \
  -e '{"target_instances":["us-central1-a/app-1"],"snapshot_name_prefix":"daily-20260429","gcp_project_id":"example-project"}'
```

只为指定数据盘创建快照并跳过启动盘：

```bash
ansible-playbook \
  -i localhost, \
  cloud-platform-recipes/gcp/create-vm-disk-snapshots/playbook.yml \
  -e '{"target_instances":["app-1"],"snapshot_name_prefix":"daily-20260429","gcp_project_id":"example-project","include_boot_disk":false,"data_disk_ids":["data-disk-1","data-disk-2"]}'
```

## 输出

playbook 会打印统一格式的结果结构，包含：

- `provider`
- `project`
- `consistency_mode`
- `created_snapshot_count`
- `results[]`：其中包含实例 ID、磁盘 ID、快照 ID、快照名、状态和可用区

## 验证说明

- 支持 `--syntax-check`
- 不支持 `--check`，因为该配方会真实创建快照
- 请先在非生产项目中验证

## 警告

- 这个配方会修改 GCP 快照状态。
- 快照保留与清理不在当前范围内。
- GCP machine image 是单独的能力，这个配方不实现它。
