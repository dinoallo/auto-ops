# 生成预置 Kubernetes Root CA 和 ServiceAccount Key Pair

英文版：`README.md`

这个 recipe 会生成预置的 Kubernetes root CA 替换材料和预置 ServiceAccount 签名 key pair。它会默认在 play 的第一台控制平面主机上写入 `ca-new.crt`、`ca-new.key`、`ca-bundle.crt`、`sa-new.key` 和 `sa-new.pub`，然后把生成文件分发到其他目标主机。

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 使用提权权限在控制平面节点上运行。
2. 默认使用 play 中第一台主机作为生成源。
3. 校验所有目标主机起始时使用相同的当前 `ca.crt`。
4. 生成新的 root CA 私钥和自签证书。
5. 用当前 `ca.crt` 加 `ca-new.crt` 生成 `ca-bundle.crt`。
6. 生成 `sa-new.key` 并推导 `sa-new.pub`。
7. 将生成文件分发到所有目标主机，并为私钥设置受限权限。
8. 打印 bundle 中的证书数量和新 root CA 证书详情。

## 要求

- inventory 中存在名为 `masters` 的主机组，除非覆盖 `target_hosts`
- `/etc/kubernetes/pki/ca.crt` 下存在当前 root CA 证书
- 目标主机上可以使用 `openssl`、`grep` 和 `cat`
- 具备 SSH 连接和提权权限

## 可选变量

- `target_hosts`: 目标主机组，默认 `masters`
- `k8s_ca_source_host`: 生成源主机，默认 play 中第一台主机
- `pki_dir`: Kubernetes PKI 目录，默认 `'/etc/kubernetes/pki'`
- `k8s_ca_valid_days`: 新 root CA 有效期天数，默认 `3650`
- `k8s_ca_subject`: 新 root CA subject，默认 `'/CN=kubernetes-ca'`
- `service_account_key_bits`: ServiceAccount key 长度，默认 `4096`

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/renew-k8s-ca/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-k8s-ca/playbook.yml
```

## 重要警告

- 这个 recipe 会创建 root CA 私钥材料和 ServiceAccount 签名私钥材料。请妥善保护目标主机和备份文件。
- 生成的文件只是预置材料；这个 recipe 不会修改静态 Pod manifest 或当前生效的 Kubernetes 身份文件。
- 在依赖此流程前，应先在非生产或可完整恢复的集群上测试完整轮换和回滚流程。
