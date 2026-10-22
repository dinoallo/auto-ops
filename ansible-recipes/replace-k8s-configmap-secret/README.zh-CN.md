# 替换 Kubernetes ConfigMap 或 Secret 的值

English version: `README.md`

这个 recipe 使用本地 kubeconfig 文件，在多个 Kubernetes 集群中替换同一个
ConfigMap 或 Secret 的指定 key/value。它会读取 `kc_dir` 目录下的每一个普通文件，
并针对每个文件执行一次 `kubectl patch`。

patch 只包含用户给出的 key/value，因此资源中的其他 key 会保留。ConfigMap 使用
`data` 更新，Secret 使用 `stringData` 更新，调用方可以直接提供明文字符串值。

## 文件

- `playbook.yml`：recipe playbook

## 使用要求

- Ansible 和 `kubectl` 已安装在本地 Ansible 控制机上
- `kc_dir` 下每个目标集群的 kubeconfig 都可读
- 目标命名空间中的 ConfigMap 或 Secret 已经存在
- 对每个目标集群都有 patch 该资源的 Kubernetes 权限

playbook 在 `localhost` 上使用本地连接执行，不会通过 SSH 连接 Kubernetes 节点。

## 变量

- `kc_dir`：存放 kubeconfig 文件的本地目录，默认是 playbook 同级的 `kc/`
- `kubectl_command`：kubectl 可执行文件或绝对路径，默认是 `kubectl`
- `resource_kind`：`configmap` 或 `secret`，默认是 `configmap`
- `resource_name`：目标 ConfigMap 或 Secret 名称，必填
- `namespace`：目标命名空间，默认是 `default`
- `cluster_resources`：可选，以 kubeconfig 文件名为 key 的集群级资源覆盖配置；支持
  `resource_kind`、`resource_name` 和 `namespace`，未声明的字段继续使用全局值
- `key_values`：可选，应用到每个集群的公共 key/value 映射
- `cluster_key_values`：可选，以 kubeconfig 文件名为 key 的集群映射；其中的值会覆盖公共
  `key_values`

每个集群映射的 key 必须使用 kubeconfig 的文件名。例如，
`cluster-a.kubeconfig` 对应 `kc/cluster-a.kubeconfig`。如果某个 kubeconfig 没有
`cluster_resources` 配置，就使用全局资源目标；如果声明了集群级配置，则覆盖其中
提供的字段。每个 kubeconfig 最终必须从 `key_values` 或 `cluster_key_values` 中获得
至少一个待替换的值。

## 用法

先检查 playbook 语法：

```bash
ansible-playbook --syntax-check \
  ansible-recipes/replace-k8s-configmap-secret/playbook.yml
```

假设本地目录如下：

```text
kc/
├── cluster-a.kubeconfig
└── cluster-b.kubeconfig
```

为两个集群分别替换不同的值：

```bash
ansible-playbook \
  -i localhost, \
  ansible-recipes/replace-k8s-configmap-secret/playbook.yml \
  -e kc_dir="$PWD/kc" \
  -e resource_kind=configmap \
  -e resource_name=app-settings \
  -e namespace=demo \
  -e 'cluster_key_values={"cluster-a.kubeconfig":{"APP_ENV":"production","API_URL":"https://api-a.example.invalid"},"cluster-b.kubeconfig":{"APP_ENV":"staging","API_URL":"https://api-b.example.invalid"}}'
```

上面的命令会分别使用 `cluster-a.kubeconfig` 和 `cluster-b.kubeconfig` 执行一次
patch；两个集群的 `APP_ENV` 值互不影响。

如果希望 `cluster-a` 使用全局资源，而 `cluster-b` 使用另一个资源，可以增加集群级
资源覆盖配置。只需要声明不同的字段即可：

```yaml
resource_kind: configmap
resource_name: app-settings
namespace: demo
cluster_resources:
  cluster-b.kubeconfig:
    resource_kind: secret
    resource_name: app-credentials-b
```

此时 `cluster-a.kubeconfig` 使用全局的 `configmap/app-settings`，
`cluster-b.kubeconfig` 使用 `secret/app-credentials-b`，两个集群都使用全局的
`demo` 命名空间。

如果大部分集群使用相同值、只有某个集群需要覆盖其中一个 key，可以这样写：

```bash
ansible-playbook \
  -i localhost, \
  ansible-recipes/replace-k8s-configmap-secret/playbook.yml \
  -e kc_dir="$PWD/kc" \
  -e resource_name=app-settings \
  -e 'key_values={"LOG_LEVEL":"info","FEATURE_FLAG":"disabled"}' \
  -e 'cluster_key_values={"cluster-b.kubeconfig":{"LOG_LEVEL":"debug"}}'
```

替换 Secret 时，将 `resource_kind` 设为 `secret`，并避免把明文 Secret 放进 shell
历史和进程列表。建议使用 Ansible Vault 保护的 extra-vars 文件，而不是直接在 `-e`
参数中写明文：

```yaml
# secret-values.yml —— 使用 ansible-vault 保护此文件
kc_dir: /secure/path/kc
resource_kind: secret
resource_name: app-credentials
namespace: demo
cluster_key_values:
  cluster-a.kubeconfig:
    username: app-a
    password: "{{ vault_cluster_a_password }}"
  cluster-b.kubeconfig:
    username: app-b
    password: "{{ vault_cluster_b_password }}"
cluster_resources:
  cluster-b.kubeconfig:
    resource_name: app-credentials-b
```

```bash
ansible-playbook \
  -i localhost, \
  ansible-recipes/replace-k8s-configmap-secret/playbook.yml \
  -e @secret-values.yml --ask-vault-pass
```

playbook 会通过 `no_log` 隐藏包含 Secret 值的任务输出。不要把真实 kubeconfig、token
或包含 Secret 的变量文件提交到仓库。

## 重要提示

- 这个 recipe 会执行会修改集群的 `kubectl patch`，请先在非生产集群验证，并逐个确认
  所有集群的结果。
- 它只替换指定的 key，不会删除未指定的 key。
- 如果发现某个 kubeconfig 没有对应的值，playbook 会在执行 patch 前失败。
- `ansible-playbook --check` 不能为这个 recipe 提供 Kubernetes dry-run。请使用语法检查，
  并在一次性的或非生产集群上验证。
