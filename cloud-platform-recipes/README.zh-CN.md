# 云平台配方

English version: `README.md`

这个目录包含面向云平台 API 的运维配方，不通过 SSH 登录到来宾操作系统执行操作。

当前范围：

- 为指定虚拟机实例创建磁盘快照
- 每个云平台保持一个独立配方
- 当平台支持且配方已实现时，支持云平台原生一致性组快照

当前状态：

- `aliyun/create-vm-disk-snapshots` 已实现
- `gcp/create-vm-disk-snapshots` 已实现
- `tencentcloud/create-vm-disk-snapshots` 已实现
- `volcengine/create-vm-disk-snapshots` 已实现

## 目录结构

- `IMPLEMENTATION-PLAN.md`：这一组配方的实现说明
- `aliyun/create-vm-disk-snapshots/`：阿里云 ECS 快照配方
- `gcp/create-vm-disk-snapshots/`：GCP Compute Engine 快照配方
- `tencentcloud/create-vm-disk-snapshots/`：腾讯云 CVM/CBS 快照配方
- `volcengine/create-vm-disk-snapshots/`：火山引擎 ECS/EBS 快照配方

## 通用执行模型

这些配方应当：

1. 在控制节点上运行，通常是 `localhost`
2. 使用本地凭证源认证到云平台
3. 解析显式指定的目标虚拟机实例
4. 发现已挂载磁盘
5. 为每个磁盘创建快照，或在请求且平台支持时创建原生一致性组快照
6. 返回统一格式的快照结果

## 共享变量

各平台实现对齐于以下公共约定：

- `target_instances`：非空的目标实例标识或引用列表
- `snapshot_name_prefix`：用于构建快照名的非空前缀
- `include_boot_disk`：可选，默认 `true`
- `data_disk_ids`：可选，用于限制快照范围
- `use_consistency_group_snapshot`：可选，默认 `false`
- `wait_for_snapshot_ready`：可选，默认 `true`
- `snapshot_description`：可选的描述文本
- `snapshot_tags`：可选的云平台标签或 labels

每个平台的配方还需要平台特定上下文，例如区域、项目或账号范围。

## 一致性组支持

已根据 2026-04-28 的官方文档核对：

- `aliyun`：支持，适用于同一实例上的合格云盘
- `gcp`：标准磁盘快照不支持
- `tencentcloud`：支持，同一 CVM 实例挂载磁盘可使用快照组
- `volcengine`：支持，通过快照一致性组实现

对 `gcp` 来说，这个快照配方会拒绝 `use_consistency_group_snapshot=true`。如果需要 GCP 上的多磁盘崩溃一致性备份，更合适的做法是单独实现 machine-image 配方，而不是扩展这个磁盘快照配方。

## 验证

每个平台配方至少应支持：

```bash
ansible-playbook -i localhost, --syntax-check cloud-platform-recipes/<provider>/create-vm-disk-snapshots/playbook.yml
```

功能验证请使用非生产云账号或项目。

## 说明

- 云平台原生一致性组快照不同于来宾侧应用一致性备份。
- 快照保留和清理不在这一组配方的范围内。
- GCP 的目标实例引用可以是实例名、`zone/name` 或完整 self-link。
