# 扫描 Next.js 进程版本

English version: `README.md`

这个 recipe 扫描进程名类似 `next-server (v14.2.35)` 的 Linux 进程，读取
括号内的字符串作为 Next.js 版本，然后读取进程 cgroup，并通过 `crictl` 使用
cgroup 中的 Kubernetes Pod UID 反查命名空间和 Pod 名称。

## 做什么

1. 读取每台目标主机上的 `/proc/<pid>/cmdline`。
2. 按 `<进程名> (<版本>)` 匹配第一个命令行参数。
3. 读取 `/proc/<pid>/cgroup`，兼容 cgroup v1 和 cgroup v2 路径中的 Kubernetes Pod UID。
4. 找到 Pod UID 时执行一次 `crictl pods --output=json`，再把 UID 映射为 `namespace/name`。
5. 每个匹配进程只输出 `namespace`、`pod` 和 `version`。

如果没有匹配进程、进程不属于 Kubernetes Pod，或可选的 Pod 反查不可用，扫描仍然成功；这些情况下 `namespace` 和 `pod` 输出为 `-`。

## 要求

- Linux 目标主机，并挂载 `/proc`
- 每台目标主机上有 Python 3
- 具备 root 权限，以便检查所有进程
- 只有在需要反查 Pod 名称时才要求已配置并能访问节点 CRI runtime 的 `crictl`

## 变量

- `target_hosts`：inventory 主机模式，默认 `'all'`
- `next_js_process_name`：进程标题前缀，默认 `'next-server'`
- `next_js_proc_root`：proc 文件系统路径，默认 `'/proc'`
- `next_js_python_interpreter`：目标主机上的 Python 路径，默认 `'/usr/bin/python3'`
- `next_js_lookup_cri_pods`：是否通过 `crictl` 反查 Pod UID，默认 `true`
- `next_js_crictl_command`：crictl 命令或路径，默认 `'crictl'`
- `next_js_output_file`：目标主机上的结果文件路径，默认为空；设置后每次执行都会覆盖写入

## 用法

校验 playbook 语法：

```bash
ansible-playbook --syntax-check ansible-recipes/scan-next-js-version/playbook.yml
```

扫描 inventory 中的所有主机：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/scan-next-js-version/playbook.yml
```

把结果写入每台目标主机上的文件：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/scan-next-js-version/playbook.yml \
  -e next_js_output_file=/var/tmp/next-js-versions.txt
```

只扫描 worker 节点并跳过 CRI Pod 反查：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/scan-next-js-version/playbook.yml \
  -e target_hosts=workers \
  -e next_js_lookup_cri_pods=false
```

示例输出：

```text
namespace=demo pod=web-7c9d6d8f6f-abcde version=v14.2.35
```

设置 `next_js_output_file` 后，同样的内容也会写入该文件。
