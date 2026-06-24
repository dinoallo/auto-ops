# 续签 etcd CA

英文版：`README.md`

这个 recipe 会为 kubeadm 管理的 etcd PKI 生成一个预置的新 etcd CA 和信任 bundle。它会先在一个源主机上生成一套共享的 `ca-new-<renewal_id>.key`、`ca-new-<renewal_id>.crt` 和 `ca-bundle-<renewal_id>.crt`，再把同一套文件安装到每台目标主机上。当前正在使用的 `ca.crt` 和 `ca.key` 不会被替换。

## 文件

- `playbook.yml`: recipe 主体

## 这个 Recipe 会做什么

1. 使用提权权限在 `target_hosts` 上运行，默认目标是 `etcd_members` inventory 组。
2. 校验 etcd CA 文件名和证书生成参数。
3. 检查每台目标主机上当前 etcd CA 证书是否存在。
4. 检查所有目标主机的当前 etcd CA 证书是否一致。
5. 在 `etcd_ca_source_host` 上只生成一次新的 etcd CA 私钥，默认源主机是 `master0`。
6. 使用配置的 subject、有效期、摘要算法、basic constraints 和 key usage 生成新的自签名 etcd CA 证书。
7. 将当前 etcd CA 证书和新 etcd CA 证书拼接成信任 bundle。
8. 将同一套生成的私钥、证书和 bundle 文件安装到每台目标主机上。
9. 打印 bundle 中的证书数量和新 CA 证书详情，便于人工核对。

## 前置要求

- kubeadm 管理的 Kubernetes 控制平面，并使用本地 etcd PKI 文件
- inventory 中存在名为 `etcd_members` 的主机组，除非你覆盖 `target_hosts`
- 每台目标主机上都存在一致的当前生效 etcd CA 证书，默认是 `/etc/kubernetes/pki/etcd/ca.crt`
- 每台目标主机上都可以使用 `openssl`、`grep` 和 `cat`
- Ansible 具备 SSH 连接和提权能力，因为默认 PKI 目录通常归 root 所有

如果你的环境符合 kubeadm 默认路径，这个 recipe 不需要额外传入变量。

## 可选变量

- `target_hosts`: 目标主机组，默认 `'etcd_members'`
- `etcd_ca_source_host`: 生成共享 CA 文件的源主机，默认 `'master0'`
- `etcd_pki_dir`: etcd PKI 目录，默认 `'/etc/kubernetes/pki/etcd'`
- `etcd_ca_current_cert`: 当前生效的 CA 证书文件名，默认 `'ca.crt'`
- `renewal_id`: 生成文件名中的日期小时或自定义 ID，默认 `YYYYMMDDHH`
- `etcd_ca_new_key`: 预置的新 CA 私钥文件名，默认 `'ca-new-<renewal_id>.key'`
- `etcd_ca_new_cert`: 预置的新 CA 证书文件名，默认 `'ca-new-<renewal_id>.crt'`
- `etcd_ca_bundle`: 旧 CA 加新 CA 的 bundle 文件名，默认 `'ca-bundle-<renewal_id>.crt'`
- `etcd_ca_key_bits`: 私钥长度，默认 `4096`
- `etcd_ca_valid_days`: 证书有效天数，默认 `3650`；99 年可使用 `36135`
- `etcd_ca_subject`: 证书 subject，默认 `'/CN=etcd-ca'`
- `etcd_ca_digest`: OpenSSL 摘要参数后缀，默认 `'sha256'`
- `etcd_ca_basic_constraints`: OpenSSL basic constraints 扩展，默认 `'basicConstraints=critical,CA:TRUE'`
- `etcd_ca_key_usage`: OpenSSL key usage 扩展，默认 `'keyUsage=critical,keyCertSign,cRLSign'`
- `etcd_ca_new_key_mode`: 预置私钥文件权限，默认 `'0600'`
- `etcd_ca_new_cert_mode`: 预置证书文件权限，默认 `'0644'`
- `etcd_ca_bundle_mode`: CA bundle 文件权限，默认 `'0644'`
- `openssl_command`: OpenSSL 命令名或路径，默认 `'openssl'`
- `grep_command`: grep 命令名或路径，默认 `'grep'`
- `cat_command`: cat 命令名或路径，默认 `'cat'`
- `shell_executable`: 创建 bundle 时使用的 shell，默认 `'/bin/bash'`

inventory 示例：

```ini
[etcd_members]
cp1
cp2
cp3
```

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/renew-etcd-ca/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-etcd-ca/playbook.yml
```

如果要使用自定义 CA 文件名或不同 subject：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-etcd-ca/playbook.yml \
  -e etcd_ca_new_key=ca-2026.key \
  -e etcd_ca_new_cert=ca-2026.crt \
  -e etcd_ca_bundle=ca-2026-bundle.crt \
  -e etcd_ca_subject=/CN=etcd-ca-2026
```

如果要生成 99 年有效期的预置 etcd CA：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-etcd-ca/playbook.yml \
  -e etcd_ca_valid_days=36135
```

如果要指定目标主机组：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-etcd-ca/playbook.yml \
  -e target_hosts=cp1
```

如果要指定生成共享 CA 文件的源主机：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-etcd-ca/playbook.yml \
  -e etcd_ca_source_host=master0
```

如果需要指定 SSH key：

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/renew-etcd-ca/playbook.yml
```

## 重要提醒

- 这个 recipe 会生成并分发 CA 私钥材料，应妥善保护目标主机、日志、备份和生成文件。
- 这个 recipe 不会替换当前生效的 etcd CA 文件，只会预置新 CA 并生成信任 bundle。
- 这个 recipe 不会续签 etcd 叶子证书。应在预置新 CA 之后、移除旧 CA 信任之前续签叶子证书。
- 源主机必须包含在本次目标主机集合中。默认情况下，`master0` 必须包含在 `target_hosts` 里。
- 所有目标主机必须从同一份当前 etcd CA 证书开始。如果当前 CA 证书 checksum 不一致，recipe 会失败。
- 执行任何 CA 轮换流程前，应先备份 etcd 数据和 Kubernetes PKI 目录。
- 在使用生成文件前，请核对输出中的 subject、issuer、有效期、fingerprint 和 bundle 证书数量。
- 在依赖这套流程前，请先在非生产或可完整恢复的集群上测试完整的 CA 续签、证书续签、激活、重启和回滚流程。
