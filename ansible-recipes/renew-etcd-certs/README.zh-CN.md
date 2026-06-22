# 使用预置新 CA 续签 etcd 叶子证书

英文版：`README.md`

这个 recipe 使用已经预置的新 etcd CA 来续签 kubeadm 管理的 etcd 叶子证书。它会把续签后的文件以带日期小时的 `-new-<renewal_id>` 文件名写到现有证书旁边，因此这个 playbook 不会直接替换当前正在使用的证书。

## 文件

- `playbook.yml`: recipe 主体

## 这个 Recipe 会做什么

1. 使用提权权限在 `etcd_members` inventory 组中的主机上运行，并且每次只处理一台主机。
2. 重新创建一个临时 kubeadm 证书续签 staging 目录。
3. 从 kube-apiserver 和 etcd 静态 Pod manifest 读取当前正在使用的 etcd 叶子证书路径，再把这些证书和私钥复制到 staging 目录，作为 kubeadm 续签模板。
4. 将预置的新 etcd CA `ca-new-<renewal_id>.crt` 和 `ca-new-<renewal_id>.key` 复制到 staging 目录，作为 kubeadm 签发证书使用的 CA。
5. 针对 etcd 相关叶子证书目标执行 `kubeadm certs renew`。
6. 将续签后的证书和私钥以带日期小时的文件名安装到 Kubernetes PKI 目录下。
7. 打印续签证书的 subject、issuer、有效期和 Subject Alternative Name 信息。

## 前置要求

- kubeadm 管理的 Kubernetes 控制平面，并使用本地 etcd 证书
- inventory 中存在名为 `etcd_members` 的主机组
- 每台目标主机上都可以使用 `kubeadm`、`openssl`、`cp` 和 `install`
- 配置的 PKI 目录下已经存在当前 etcd 叶子证书和私钥
- 每台目标主机上都已经预置 `/etc/kubernetes/pki/etcd/ca-new-<renewal_id>.crt` 和 `/etc/kubernetes/pki/etcd/ca-new-<renewal_id>.key`
- Ansible 具备 SSH 连接和提权能力，因为源 PKI 路径和目标 PKI 路径通常归 root 所有

如果你的环境符合 kubeadm 默认路径，并且预置 CA 文件名也符合默认值，这个 recipe 不需要额外传入变量。

## 可选变量

- `stage_dir`: 临时 kubeadm 续签目录，默认 `'/tmp/kubeadm-etcd-leaf-renew'`
- `pki_dir`: Kubernetes PKI 根目录，默认 `'/etc/kubernetes/pki'`
- `etcd_pki_dir`: etcd PKI 目录，默认 `'/etc/kubernetes/pki/etcd'`
- `manifest_dir`: 静态 Pod manifest 目录，默认 `'/etc/kubernetes/manifests'`
- `kube_apiserver_manifest`: kube-apiserver manifest 路径，默认 `manifest_dir + '/kube-apiserver.yaml'`
- `etcd_manifest`: etcd manifest 路径，默认 `manifest_dir + '/etcd.yaml'`
- `renewal_id`: 预置文件名中的日期小时或自定义 ID，默认 `YYYYMMDDHH`
- `staged_etcd_ca_cert`: 预置 etcd CA 证书，默认 `etcd_pki_dir + '/ca-new-<renewal_id>.crt'`
- `staged_etcd_ca_key`: 预置 etcd CA 私钥，默认 `etcd_pki_dir + '/ca-new-<renewal_id>.key'`
- `healthcheck_client_cert_template`: healthcheck client 模板证书，默认 `etcd_pki_dir + '/healthcheck-client.crt'`
- `healthcheck_client_key_template`: healthcheck client 模板私钥，默认 `etcd_pki_dir + '/healthcheck-client.key'`
- `apiserver_etcd_client_cert_output`: 续签后的 apiserver-etcd-client 证书输出路径，默认 `pki_dir + '/apiserver-etcd-client-new-<renewal_id>.crt'`
- `apiserver_etcd_client_key_output`: 续签后的 apiserver-etcd-client 私钥输出路径，默认 `pki_dir + '/apiserver-etcd-client-new-<renewal_id>.key'`
- `healthcheck_client_cert_output`: 续签后的 healthcheck client 证书输出路径，默认 `etcd_pki_dir + '/healthcheck-client-new-<renewal_id>.crt'`
- `healthcheck_client_key_output`: 续签后的 healthcheck client 私钥输出路径，默认 `etcd_pki_dir + '/healthcheck-client-new-<renewal_id>.key'`
- `etcd_peer_cert_output`: 续签后的 etcd peer 证书输出路径，默认 `etcd_pki_dir + '/peer-new-<renewal_id>.crt'`
- `etcd_peer_key_output`: 续签后的 etcd peer 私钥输出路径，默认 `etcd_pki_dir + '/peer-new-<renewal_id>.key'`
- `etcd_server_cert_output`: 续签后的 etcd server 证书输出路径，默认 `etcd_pki_dir + '/server-new-<renewal_id>.crt'`
- `etcd_server_key_output`: 续签后的 etcd server 私钥输出路径，默认 `etcd_pki_dir + '/server-new-<renewal_id>.key'`
- `prevent_overwrite_active_etcd_leaf_certs`: 如果输出路径当前正被静态 Pod manifest 使用则失败，默认 `true`
- `kubeadm_renew_targets`: 要续签的 kubeadm 证书目标，默认包含 `apiserver-etcd-client`、`etcd-healthcheck-client`、`etcd-peer` 和 `etcd-server`

inventory 示例：

```ini
[etcd_members]
cp1
cp2
cp3
```

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/renew-etcd-certs/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-etcd-certs/playbook.yml
```

如果要使用自定义 PKI 路径：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-etcd-certs/playbook.yml \
  -e pki_dir=/etc/kubernetes/pki \
  -e etcd_pki_dir=/etc/kubernetes/pki/etcd
```

如果当前 manifest 已经在使用默认的 `*-new` 证书路径，可以把第二批预置证书写到其它文件名：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-etcd-certs/playbook.yml \
  -e apiserver_etcd_client_cert_output=/etc/kubernetes/pki/apiserver-etcd-client-next.crt \
  -e apiserver_etcd_client_key_output=/etc/kubernetes/pki/apiserver-etcd-client-next.key \
  -e healthcheck_client_cert_output=/etc/kubernetes/pki/etcd/healthcheck-client-next.crt \
  -e healthcheck_client_key_output=/etc/kubernetes/pki/etcd/healthcheck-client-next.key \
  -e etcd_peer_cert_output=/etc/kubernetes/pki/etcd/peer-next.crt \
  -e etcd_peer_key_output=/etc/kubernetes/pki/etcd/peer-next.key \
  -e etcd_server_cert_output=/etc/kubernetes/pki/etcd/server-next.crt \
  -e etcd_server_key_output=/etc/kubernetes/pki/etcd/server-next.key
```

如果需要指定 SSH key：

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/renew-etcd-certs/playbook.yml
```

## 重要提醒

- 这个 recipe 会处理私钥和证书 CA 材料，应妥善保护目标主机、日志和生成文件。
- 这个 recipe 不会创建新的 etcd CA。每台目标主机上都必须已经存在 `ca-new-<renewal_id>.crt` 和 `ca-new-<renewal_id>.key`。
- 这个 recipe 不会替换当前正在使用的证书文件，也不会重启 etcd 或 kube-apiserver。它只会为后续受控切换准备 `*-new-<renewal_id>.crt` 和 `*-new-<renewal_id>.key` 文件。
- 执行前应先备份 etcd 数据和 Kubernetes PKI 文件。
- 在使用续签证书前，请先核对输出中的 issuer、有效期和 SAN 信息。
- 在依赖这套流程前，请先在非生产或可完整恢复的集群上测试完整轮换和回滚流程。
