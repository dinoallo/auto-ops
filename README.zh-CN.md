# auto-ops

英文版：`README.md`

`auto-ops` 是一个小型运维自动化仓库，目前主要收录可直接执行的 Ansible playbook recipe。

整个仓库围绕 [`ansible-recipes/`](ansible-recipes/) 下的独立 recipe 组织。每个 recipe 尽量做到自包含，把 playbook 和使用说明放在一起，方便单独评审和执行。

## 仓库结构

- `ansible-recipes/README.md`: recipe 集合的主说明文档
- `ansible-recipes/README.zh-CN.md`: 主说明文档的中文版
- `ansible-recipes/<recipe-name>/playbook.yml`: 可执行的 playbook
- `ansible-recipes/<recipe-name>/README.md`: 对应 recipe 的英文说明
- `AGENTS.md`: 贡献约定，包括目录结构、风格和校验要求

## 快速开始

在本地创建一个 Ansible 运行环境：

```bash
cd ansible-recipes
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip ansible
```

结合 inventory 执行 playbook：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/safely-copying-files/playbook.yml \
  -e source_file=./files/app.conf \
  -e dest_file=/etc/myapp/app.conf
```

正式执行前先做语法检查：

```bash
ansible-playbook --syntax-check ansible-recipes/safely-copying-files/playbook.yml
```

## 当前可用的 Recipes

### `safely-copying-files`

把控制机上的本地文件复制到远程主机。如果目标文件已存在且内容不同，playbook 会在覆盖前提示确认。变量和示例见 [`ansible-recipes/safely-copying-files/README.md`](ansible-recipes/safely-copying-files/README.md)。

### `rotate-k8s-files`

备份 Kubernetes 控制平面相关文件，在 master 节点上重新生成 CA 和组件证书，分发共享 PKI 材料，并让 worker 节点重新加入集群。这个 playbook 会修改集群证书和身份材料，应该只在非生产环境或可完整恢复的集群里先验证。

## 说明

- 不要把真实 inventory、SSH key、token 或生产主机信息提交到仓库里。
- recipe 行为变更时，英文和中文文档应同时更新。
- YAML 里统一使用 `true` 和 `false`，不要使用 `yes` 和 `no`。

如果要查看 recipe 编写方式和贡献要求，见 [`AGENTS.md`](AGENTS.md)。
