# 生成新的 front-proxy CA 和信任 bundle

英文版：`README.md`

这个 recipe 会在一台源 master 上生成替换用的 Kubernetes front-proxy CA，构建包含当前和新 front-proxy CA 证书的信任 bundle，并把生成的文件分发到所有目标 master 节点。

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 使用提权权限在目标 master 主机上运行。
2. 验证所有目标主机一开始使用相同的当前生效 front-proxy CA 证书。
3. 在配置的源主机上生成新的 front-proxy CA 私钥和证书。
4. 在源主机上构建包含当前和新 front-proxy CA 证书的 bundle。
5. 设置生成的 CA 文件权限。
6. 从源主机读取生成文件，并安装到所有目标主机。
7. 打印 bundle 中的证书数量和新 CA 证书详情。

## 要求

- kubeadm 管理的 Kubernetes 控制平面，或等价的 PKI 布局
- inventory 中存在名为 `masters` 的主机组，除非覆盖 `target_hosts`
- 存在名为 `master0` 的源主机，除非覆盖 `front_proxy_ca_source_host`
- 每台目标主机的配置 PKI 目录下都已经存在当前生效的 front-proxy CA 证书
- 目标主机上可以使用 `openssl`、`grep` 和 `cat`
- 具备 SSH 连接和提权权限，因为 PKI 文件通常归 root 所有

当默认值符合你的环境时，不需要额外变量。

## 可选变量

- `target_hosts`: 目标主机组，默认 `masters`
- `front_proxy_ca_source_host`: 生成新 CA 的源主机，默认 `master0`
- `pki_dir`: Kubernetes PKI 目录，默认 `'/etc/kubernetes/pki'`
- `front_proxy_ca_current_cert`: 当前生效 front-proxy CA 证书文件名，默认 `'front-proxy-ca.crt'`
- `front_proxy_ca_new_key`: 新 front-proxy CA 私钥文件名，默认 `'front-proxy-ca-new.key'`
- `front_proxy_ca_new_cert`: 新 front-proxy CA 证书文件名，默认 `'front-proxy-ca-new.crt'`
- `front_proxy_ca_bundle`: 信任 bundle 文件名，默认 `'front-proxy-ca-bundle.crt'`
- `front_proxy_ca_key_bits`: 新 CA key 位数，默认 `4096`
- `front_proxy_ca_valid_days`: 新 CA 有效期天数，默认 `3650`
- `front_proxy_ca_subject`: 新 CA subject，默认 `'/CN=kubernetes-front-proxy-ca'`
- `front_proxy_ca_digest`: 证书摘要算法名称，默认 `'sha256'`
- `front_proxy_ca_basic_constraints`: CA basic constraints 扩展
- `front_proxy_ca_key_usage`: CA key usage 扩展
- `front_proxy_ca_new_key_mode`: 私钥权限，默认 `'0600'`
- `front_proxy_ca_new_cert_mode`: 证书权限，默认 `'0644'`
- `front_proxy_ca_bundle_mode`: bundle 权限，默认 `'0644'`
- `openssl_command`: `openssl` 的命令名或路径，默认 `'openssl'`
- `grep_command`: `grep` 的命令名或路径，默认 `'grep'`
- `cat_command`: `cat` 的命令名或路径，默认 `'cat'`
- `shell_executable`: 构建 bundle 时使用的 shell，默认 `'/bin/bash'`

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/renew-front-proxy-ca/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-front-proxy-ca/playbook.yml
```

使用不同的源主机：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-front-proxy-ca/playbook.yml \
  -e front_proxy_ca_source_host=cp1
```

使用自定义生成文件名：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-front-proxy-ca/playbook.yml \
  -e front_proxy_ca_new_key=front-proxy-ca-2026.key \
  -e front_proxy_ca_new_cert=front-proxy-ca-2026.crt \
  -e front_proxy_ca_bundle=front-proxy-ca-bundle-2026.crt
```

## 重要警告

- 这个 recipe 会创建并分发证书颁发机构私钥材料。请妥善保护目标主机、日志和备份文件。
- 这个 recipe 不会激活新的 front-proxy CA。它只为后续激活步骤准备预置文件。
- 这个 recipe 不会续签 front-proxy client 证书，也不会重启 Kubernetes 组件。
- 所有目标主机一开始必须使用相同的当前生效 front-proxy CA 证书。
- 执行前应先备份 Kubernetes PKI 文件。
- 应在非生产或可完整恢复的集群上测试完整的轮换和回滚流程。
