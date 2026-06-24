# 生成预置 Kubernetes Root CA

英文版：`README.md`

这个 recipe 会生成预置的 Kubernetes root CA 替换材料。它会在一台源控制平面主机上写入 `ca-new-<renewal_id>.crt`、`ca-new-<renewal_id>.key` 和 `ca-bundle-<renewal_id>.crt`，然后把生成文件分发到其他目标主机。

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 在控制平面主机上以提权方式运行。
2. 默认使用 play 中第一台主机作为生成源。
3. 校验每台目标主机的当前 `ca.crt` 是否一致。
4. 生成新的 root CA 私钥和自签证书。
5. 用当前 `ca.crt` 加 `ca-new-<renewal_id>.crt` 构建 `ca-bundle-<renewal_id>.crt`。
6. 把生成文件分发到每台目标主机，并给私钥设置限制权限。
7. 输出 bundle 中的证书数量和新 root CA 证书详情。

## 要求

- inventory 中有 `masters` 组，除非覆盖 `target_hosts`
- `/etc/kubernetes/pki/ca.crt` 当前存在
- 目标主机上有 `openssl`、`grep` 和 `cat`
- SSH 访问和提权权限

## 可选变量

- `target_hosts`: 目标主机组，默认 `masters`
- `k8s_ca_source_host`: 生成源主机，默认 play 中第一台主机
- `pki_dir`: Kubernetes PKI 目录，默认 `'/etc/kubernetes/pki'`
- `renewal_id`: 生成文件名使用的日期小时或自定义 ID，默认 `YYYYMMDDHH`
- `k8s_ca_valid_days`: 新 root CA 有效期天数，默认 `3650`；99 年可使用 `36135`
- `k8s_ca_subject`: 新 root CA subject，默认 `'/CN=kubernetes-ca'`

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/renew-k8s-ca/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-k8s-ca/playbook.yml \
  -e renewal_id=${RENEWAL_ID}
```

如果要生成 99 年有效期的预置 root CA：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-k8s-ca/playbook.yml \
  -e renewal_id=${RENEWAL_ID} \
  -e k8s_ca_valid_days=36135
```

## 重要警告

- 这个 recipe 会创建 root CA 私钥材料。请妥善保护目标主机和备份文件。
- 生成文件只是预置文件；这个 recipe 不会修改静态 Pod manifest 或当前生效的 Kubernetes 身份文件。
- ServiceAccount 签名 key 使用独立的 `renew-service-account-keys`、`configure-service-account-keys` 和 `activate-service-account-keys` recipe 轮转。
- 在依赖它之前，请先在非生产或可完整恢复的集群中测试完整轮转和回滚流程。
