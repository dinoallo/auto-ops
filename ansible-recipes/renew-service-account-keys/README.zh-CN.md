# 生成预置 Kubernetes ServiceAccount Key Pair

英文版：`README.md`

这个 recipe 会生成预置的 Kubernetes ServiceAccount 签名 key pair。它会在一台源控制平面主机上写入 `sa-new-<renewal_id>.key` 和 `sa-new-<renewal_id>.pub`，校验 key pair 后分发到其他目标主机。

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 在控制平面主机上以提权方式运行。
2. 默认使用 play 中第一台主机作为生成源。
3. 校验当前 `sa.key` 和 `sa.pub` 是否匹配。
4. 生成新的 ServiceAccount 签名私钥。
5. 推导匹配的公钥。
6. 把预置 key pair 分发到每台目标主机，并给私钥设置限制权限。
7. 在每台目标主机上校验预置 key pair。

## 要求

- inventory 中有 `masters` 组，除非覆盖 `target_hosts`
- `/etc/kubernetes/pki/sa.key` 和 `/etc/kubernetes/pki/sa.pub` 当前存在
- 目标主机上有 `openssl` 和 `diff`
- SSH 访问和提权权限

## 可选变量

- `target_hosts`: 目标主机组，默认 `masters`
- `service_account_source_host`: 生成源主机，默认 play 中第一台主机
- `pki_dir`: Kubernetes PKI 目录，默认 `'/etc/kubernetes/pki'`
- `renewal_id`: staged 文件名使用的日期小时或自定义 ID，默认 `YYYYMMDDHH`
- `service_account_key_bits`: ServiceAccount key 长度，默认 `4096`

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/renew-service-account-keys/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-service-account-keys/playbook.yml \
  -e renewal_id=${RENEWAL_ID}
```

## 重要警告

- 这个 recipe 会创建 ServiceAccount 签名私钥材料。请妥善保护目标主机和备份文件。
- 生成文件只是预置文件；这个 recipe 不会修改静态 Pod manifest 或当前生效的 Kubernetes 身份文件。
- 在依赖它之前，请先在非生产或可完整恢复的集群中测试完整轮转和回滚流程。
