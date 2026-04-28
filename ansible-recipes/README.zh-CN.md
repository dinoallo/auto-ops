# Ansible Recipes

英文版：`README.md`

这个目录存放可直接执行的 Ansible recipe。每个 recipe 一般是一个独立目录，里面至少包含：

- `playbook.yml`: 可执行的 playbook
- `README.md`: recipe 的用途、变量和示例

## 环境配置

如果你不想把 Ansible 直接装到系统 Python 里，可以在当前目录里基于系统自带的 `python3` 创建一个本地虚拟环境：

```bash
cd ansible-recipes
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ansible
```

安装完成后，可以在虚拟环境里确认命令是否可用：

```bash
ansible --version
ansible-playbook --version
```

之后每次回到这个项目准备执行 recipe 前，先重新激活虚拟环境：

```bash
cd ansible-recipes
source .venv/bin/activate
```

如果要退出虚拟环境：

```bash
deactivate
```

## 使用前准备

执行 recipe 前，需要先准备：

1. 已安装 `ansible-playbook`
2. 一份可用的 inventory，例如 `inventory.ini`
3. 可以连接到目标主机的 SSH 配置和权限

一个最基本的执行形式是：

```bash
ansible-playbook \
  -i inventory.ini \
  path/to/playbook.yml \
  -e key=value
```

如果需要指定连接时使用的 SSH key：

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  path/to/playbook.yml \
  -e key=value
```

## 当前可用的 Recipes

### safely-copying-files

路径：`ansible-recipes/safely-copying-files/playbook.yml`

更详细的说明见 `ansible-recipes/safely-copying-files/README.md`。

### rotate-k8s-files

路径：`ansible-recipes/rotate-k8s-files/playbook.yml`

更详细的说明见 `ansible-recipes/rotate-k8s-files/README.md`。
