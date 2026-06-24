# 使用预置 CA 续签 front-proxy-client 证书

英文版：`README.md`

这个 recipe 使用预置的 front-proxy CA 文件续签 kubeadm 管理的 `front-proxy-client` 证书。它会把续签后的证书和私钥写成带日期小时的 `-new-<renewal_id>` 文件名，因此不会直接替换当前正在使用的文件。

## 文件

- `playbook.yml`: recipe playbook

## 这个 Recipe 做什么

1. 使用提权权限在 `masters` inventory 组中的主机上运行，每次处理一台主机。
2. 重建临时 kubeadm staging 目录。
3. 从 kube-apiserver 静态 Pod manifest 读取当前正在使用的 `front-proxy-client` 证书和私钥路径，再把这些文件复制到 staging 目录作为续签模板。
4. 将 `front-proxy-ca-new-<renewal_id>.crt` 和 `front-proxy-ca-new-<renewal_id>.key` 复制到 staging 目录作为 kubeadm 签发 CA。
5. 写入一个临时 kubeadm 配置。`kubeadm_config_api_version=v1beta3` 时不写证书有效期字段；`v1beta4` 时可以选择写入有效期字段。
6. 执行 `kubeadm certs renew front-proxy-client`。
7. 将续签后的证书和私钥安装为 `front-proxy-client-new-<renewal_id>.crt` 和 `front-proxy-client-new-<renewal_id>.key`。
8. 打印续签证书的 subject、issuer、有效期和 extended key usage。

## 要求

- kubeadm 管理的 Kubernetes 控制平面
- inventory 中存在名为 `masters` 的主机组
- 每台目标主机上可以使用 `kubeadm`、`openssl` 和 `install`
- 配置的 PKI 目录下已经存在 `front-proxy-client.crt` 和 `front-proxy-client.key`
- 已预置 front-proxy CA 文件 `front-proxy-ca-new-<renewal_id>.crt` 和 `front-proxy-ca-new-<renewal_id>.key`
- 具备 SSH 连接和提权权限，因为 PKI 文件通常归 root 所有

当 kubeadm 默认路径和预置 CA 文件名符合你的环境时，不需要额外变量。

## 可选变量

- `stage_dir`: 临时 kubeadm 续签目录，默认 `'/tmp/kubeadm-front-proxy-leaf-renew'`
- `pki_dir`: Kubernetes PKI 目录，默认 `'/etc/kubernetes/pki'`
- `manifest_dir`: 静态 Pod manifest 目录，默认 `'/etc/kubernetes/manifests'`
- `kube_apiserver_manifest`: kube-apiserver manifest 路径，默认 `manifest_dir + '/kube-apiserver.yaml'`
- `renewal_id`: 预置文件名中的日期小时或自定义 ID，默认 `YYYYMMDDHH`
- `staged_front_proxy_ca_cert`: 预置 front-proxy CA 证书，默认 `pki_dir + '/front-proxy-ca-new-<renewal_id>.crt'`
- `staged_front_proxy_ca_key`: 预置 front-proxy CA 私钥，默认 `pki_dir + '/front-proxy-ca-new-<renewal_id>.key'`
- `front_proxy_client_cert_output`: 续签后的 front-proxy client 证书输出路径，默认 `pki_dir + '/front-proxy-client-new-<renewal_id>.crt'`
- `front_proxy_client_key_output`: 续签后的 front-proxy client 私钥输出路径，默认 `pki_dir + '/front-proxy-client-new-<renewal_id>.key'`
- `prevent_overwrite_active_front_proxy_client_certs`: 如果输出路径当前正被 kube-apiserver manifest 使用则失败，默认 `true`
- `kubeadm_config_api_version`: 续签时使用的 kubeadm 配置 API，默认 `'v1beta3'`；只有 kubeadm 支持时才设置为 `'v1beta4'`
- `kubeadm_config_file`: 临时 kubeadm 配置路径，默认 `stage_dir + '/kubeadm-config.yaml'`
- `kubeadm_certificate_validity_period`: 可选的叶子证书有效期，例如 `'867240h'`；只在 `kubeadm_config_api_version=v1beta4` 时支持
- `kubeadm_ca_certificate_validity_period`: 可选的 CA 证书有效期，例如 `'867240h'`；只在 `kubeadm_config_api_version=v1beta4` 时支持
- `kubeadm_cluster_name`: 写入临时 kubeadm 配置的集群名称，默认 `'kubernetes'`
- `kubeadm_kubernetes_version`: 可选的 Kubernetes 版本，写入临时 kubeadm 配置，默认空

## 用法

```bash
ansible-playbook --syntax-check ansible-recipes/renew-front-proxy-certs/playbook.yml

ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-front-proxy-certs/playbook.yml
```

使用自定义 PKI 路径：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-front-proxy-certs/playbook.yml \
  -e pki_dir=/etc/kubernetes/pki
```

如果 kubeadm 版本支持 `kubeadm.k8s.io/v1beta4`，可以请求 99 年 front-proxy-client 证书：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-front-proxy-certs/playbook.yml \
  -e kubeadm_config_api_version=v1beta4 \
  -e kubeadm_certificate_validity_period=867240h
```

如果当前 manifest 已经在使用默认的 `*-new` 证书路径，可以把第二批预置证书写到其它文件名：

```bash
ansible-playbook \
  -i inventory.ini \
  ansible-recipes/renew-front-proxy-certs/playbook.yml \
  -e front_proxy_client_cert_output=/etc/kubernetes/pki/front-proxy-client-next.crt \
  -e front_proxy_client_key_output=/etc/kubernetes/pki/front-proxy-client-next.key
```

指定 SSH key 运行：

```bash
ansible-playbook \
  -i inventory.ini \
  --private-key ~/.ssh/deploy_key \
  ansible-recipes/renew-front-proxy-certs/playbook.yml
```

## 重要警告

- 这个 recipe 会处理私钥和 front-proxy CA 材料。请妥善保护目标主机、日志和生成文件。
- 这个 recipe 不会创建预置的 front-proxy CA 文件。
- 这个 recipe 不会替换当前生效的 `front-proxy-client.*` 文件，也不会重启 Kubernetes 组件。
- 默认情况下，如果续签输出路径正被 kube-apiserver manifest 使用，本 recipe 会失败，避免覆盖当前使用中的文件。
- kubeadm 配置 API `v1beta3` 不支持证书有效期字段。只有 kubeadm 版本支持时才使用 `kubeadm_config_api_version=v1beta4`；否则 kubeadm 会因为严格配置解码失败。
- 激活或使用续签证书前，应先核对打印出的 issuer 和有效期。
- 执行前应先备份 Kubernetes PKI 文件。
