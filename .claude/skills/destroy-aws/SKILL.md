---
name: destroy-aws
description: AWS リソースを Terraform destroy で削除。課金停止のために実験後に必ず実行
allowed-tools: Bash
disable-model-invocation: true
---
AWS リソースを削除します。この操作は取り消せません。

現在のリソース一覧: !`cd terraform && terraform show 2>/dev/null | grep 'resource "' || echo "リソースなし"`

実行前に必ず確認: 削除してよいですか? (yes と入力して続行)

1. ユーザー確認を取得
2. terraform destroy -auto-approve
3. リソース削除の確認
