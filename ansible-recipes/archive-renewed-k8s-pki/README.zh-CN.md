# 归档并提升更新后的 Kubernetes PKI

英文版：`README.md`

这个 recipe 会把当前正在使用的 Kubernetes PKI 文件归档，然后把 renew
生成的、带日期小时的 staged 文件移动回 kubeadm 默认的原始文件名。

支持三个 PKI 范围：

- `root`：Kubernetes Root CA、ServiceAccount key、API server 叶子证书和系统 kubeconfig
- `front-proxy`：front-proxy CA、bundle 和 front-proxy client 证书
- `etcd`：etcd CA、bundle 和 etcd 叶子证书

这个 playbook 只移动文件，不修改 static Pod manifest，也不重启组件。manifest
切换和组件重启仍然由对应的 configure / activate playbook 负责。
如果某个 scope 的 activate playbook 已经移动了同一批 staged CA 文件，不要再
对同一个 scope 执行这个 playbook，因为带日期小时的源文件已经不存在。

## 用法

提升所有范围，使用当前小时默认 renewal ID：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/archive-renewed-k8s-pki/playbook.yml
```

只提升指定日期生成的 front-proxy 文件：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/archive-renewed-k8s-pki/playbook.yml \
  -e promotion_scope=front-proxy \
  -e renewal_id=2026062208
```

同一小时内第二次轮转时，显式指定同一个 renewal ID：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/archive-renewed-k8s-pki/playbook.yml \
  -e renewal_id=2026062208-2
```

## 默认命名

renew playbook 现在默认生成带日期小时的 staged 文件。默认
`renewal_id=YYYYMMDDHH`，所以本 playbook 会查找类似这些路径：

- `/etc/kubernetes/pki/ca-new-2026062208.crt`
- `/etc/kubernetes/pki/front-proxy-ca-new-2026062208.crt`
- `/etc/kubernetes/pki/etcd/ca-new-2026062208.crt`
- `/etc/kubernetes/pki/etcd/server-new-2026062208.crt`

提升前会先把原始文件名对应的 active 文件复制到归档目录，再把 renewed 文件
移动到原始文件名。默认归档目录：

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
- `root_target_hosts`、`front_proxy_target_hosts`、`etcd_target_hosts`：分别覆盖三个范围的目标主机。
- `root_archive_dir`、`front_proxy_archive_dir`、`etcd_archive_dir`：分别覆盖归档目录。
- `root_promotions`、`front_proxy_promotions`、`etcd_promotions`：覆盖默认提升文件清单，每项必须包含 `label`、`src`、`dest`。

## 注意

如果轮转跨小时执行，或者同一小时执行多次轮转，请在 renew、configure、activate、
audit、kubelet 和 archive/promote playbook 中显式传入同一个 `renewal_id`。
