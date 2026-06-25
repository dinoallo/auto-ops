# 归档并提升更新后的 Kubernetes PKI

英文版：`README.md`

这个 recipe 会把当前正在使用的 Kubernetes PKI 文件归档，然后把 renew
生成的、带日期小时的 staged 文件移动回 kubeadm 默认的原始文件名。

支持三个 PKI 范围：

- `root`：Kubernetes Root CA、API server 叶子证书和系统 kubeconfig
- `front-proxy`：front-proxy CA、bundle 和 front-proxy client 证书
- `etcd`：etcd CA、bundle 和 etcd 叶子证书

默认情况下，这个 playbook 还会把 kube-apiserver、kube-controller-manager
和/或 etcd static Pod manifest 中的证书参数收敛回 kubeadm 原始路径。只有在
其他 playbook 或人工步骤已经负责 manifest 收敛时，才设置
`canonicalize_manifests=false`。

最终 cutover/archive 阶段应在兼容期和 leaf 证书切换后运行这个 playbook，
不要再对同一个 scope 额外运行已经会提升 staged CA 文件的 activate playbook。
同一个 scope 同时运行两者通常没有必要，因为 staged CA 文件会在 promotion
过程中被移动到原始文件名。

当 `promotion_scope` 包含 `front-proxy`、`canonicalize_manifests` 为 `true` 且 `restart_metrics_server` 为 `true` 时，本 playbook 还会等待 kube-apiserver 重新发布 `extension-apiserver-authentication` ConfigMap，然后对 `metrics-server` Deployment 执行滚动重启，确保 metrics-server 重新加载 front-proxy CA 并信任新的 aggregator 客户端证书。

## 用法

提升所有范围，使用当前小时默认 renewal ID：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/archive-renewed-k8s-pki/playbook.yml \
  -e restart_static_pods=true
```

只提升指定日期生成的 front-proxy 文件：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/archive-renewed-k8s-pki/playbook.yml \
  -e promotion_scope=front-proxy \
  -e renewal_id=2026062208 \
  -e restart_static_pods=true
```

同一小时内第二次轮转时，显式指定同一个 renewal ID：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/archive-renewed-k8s-pki/playbook.yml \
  -e renewal_id=2026062208-2 \
  -e restart_static_pods=true
```

## 默认命名

renew playbook 现在默认生成带日期小时的 staged 文件。默认
`renewal_id=YYYYMMDDHH`，所以本 playbook 会查找类似这些路径：

- `/etc/kubernetes/pki/ca-new-2026062208.crt`
- `/etc/kubernetes/pki/front-proxy-ca-new-2026062208.crt`
- `/etc/kubernetes/pki/etcd/ca-new-2026062208.crt`
- `/etc/kubernetes/pki/etcd/server-new-2026062208.crt`

提升前会先把原始文件名对应的 active 文件复制到归档目录，再把 renewed 文件
移动到原始文件名。如果 renewed 源文件已经和 active 目标文件一致，会直接删除
重复的 renewed 源文件，不再重复归档 active 文件。默认归档目录：

- `/etc/kubernetes/pki/archive/root-<renewal_id>`
- `/etc/kubernetes/pki/archive/front-proxy-<renewal_id>`
- `/etc/kubernetes/pki/archive/etcd-<renewal_id>`

归档文件后缀默认是 `<ansible_date_time.iso8601_basic_short>.bak`。

## 变量

- `promotion_scope`：`all`、`root`、`front-proxy` 或 `etcd`，默认 `all`。
- `renewal_id`：renew 和 promote 共用的日期小时或自定义 ID，默认目标主机日期小时 `YYYYMMDDHH`。
- `archive_suffix`：归档文件后缀，默认 `<ansible_date_time.iso8601_basic_short>.bak`。
- `archive_promote_serial`：每个范围的串行滚动数量，默认 `1`。
- `require_active_files`：active 目标文件不存在时是否失败，默认 `true`。
- `require_renewed_sources`：所选 scope 没有任何 renewed 源文件时是否失败，默认 `true`。
- `canonicalize_manifests`：提升后是否把 static Pod manifest 证书参数收敛回 kubeadm 原始路径，默认 `true`。
- `restart_static_pods`：manifest 收敛后是否 touch static Pod manifest 触发重启，默认 `false`。
- `restart_metrics_server`：提升 front-proxy PKI 后是否滚动重启 metrics-server
  Deployment，使其从 `extension-apiserver-authentication` ConfigMap 重新加载
  front-proxy CA。默认：`true`。
- `metrics_server_namespace`：metrics-server Deployment 所在的命名空间。
  默认：`kube-system`。
- `metrics_server_deployment`：metrics-server Deployment 的名称。
  默认：`metrics-server`。
- `metrics_server_rollout_timeout`：传给 `kubectl rollout status` 的超时时间。
  默认：`300s`。
- `kubeconfig`：重启 metrics-server 时 kubectl 使用的 kubeconfig 文件路径。
  默认：`/etc/kubernetes/admin.conf`。
- `kubectl_retries`：等待 kube-apiserver 发布更新后的
  `extension-apiserver-authentication` ConfigMap 时的重试次数。默认：`30`。
- `kubectl_delay`：kubectl 重试之间的间隔秒数。默认：`10`。
- `remove_duplicate_sources`：renewed 源文件已和 active 目标一致时是否删除重复源文件，默认 `true`。
- `root_target_hosts`、`front_proxy_target_hosts`、`etcd_target_hosts`：分别覆盖三个范围的目标主机。
- `root_archive_dir`、`front_proxy_archive_dir`、`etcd_archive_dir`：分别覆盖归档目录。
- `root_promotions`、`front_proxy_promotions`、`etcd_promotions`：覆盖默认提升文件清单，每项必须包含 `label`、`src`、`dest`。

## 注意

如果轮转跨小时执行，或者同一小时执行多次轮转，请在 renew、configure、audit、
kubelet、leaf 证书切换和 archive/promote playbook 中显式传入同一个 `renewal_id`。
