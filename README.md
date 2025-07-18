# AWS Bedrock Agent Core アプリケーション

このリポジトリは、AWS Bedrock Agent Core と Strands Framework を使用して、Claude Sonnet 4 を活用した AI アシスタントを構築するためのテンプレートプロジェクトです。

## 概要

このプロジェクトは、AWS Bedrock を通じて Anthropic Claude Sonnet 4 モデルにアクセスし、ユーザーからの入力に対して応答を返すシンプルな API エンドポイントを提供します。OpenTelemetry による監視機能も組み込まれています。

## 前提条件

- Python 3.13
- [uv](https://github.com/astral-sh/uv) パッケージマネージャー
- AWS アカウントと Bedrock へのアクセス権
- AWS CLI（設定済み）

## セットアップ手順

### 1. 環境のセットアップ

```bash
# 仮想環境の作成と有効化
uv venv
source .venv/bin/activate
uv init

# 依存関係のインストール
uv pip install -r requirements.txt

# 特定のパッケージを追加する場合
uv add [パッケージ名]
```

### 2. ローカルでの実行

```bash
# アプリケーションの実行
uv run main.py

# APIエンドポイントのテスト
curl -X POST http://localhost:8080/invocations -H "Content-Type: application/json" -d '{"prompt": "こんにちは!"}'
```

### 3. AWS IAM ロールの設定

```bash
# 1. 信頼ポリシーファイルの作成
cat > trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "bedrock-agentcore.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

# 2. 実行権限ポリシーファイルの作成
cat > execution-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ECRImageAccess",
            "Effect": "Allow",
            "Action": [
                "ecr:BatchGetImage",
                "ecr:GetDownloadUrlForLayer"
            ],
            "Resource": [
                "arn:aws:ecr:us-east-1:YOUR_ACCOUNT_ID:repository/agentcore-test"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:*"
            ],
            "Resource": [
                "arn:aws:logs:us-east-1:YOUR_ACCOUNT_ID:*"
            ]
        },
        {
            "Sid": "ECRTokenAccess",
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "xray:*"
            ],
            "Resource": [ "*" ]
        },
        {
            "Effect": "Allow",
            "Resource": "*",
            "Action": "cloudwatch:*"
        },
        {
            "Sid": "GetAgentAccessToken",
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:*"
            ],
            "Resource": "*"
        },
        {
            "Sid": "BedrockModelInvocation",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/*",
                "arn:aws:bedrock:us-east-1:YOUR_ACCOUNT_ID:*"
            ]
        }
    ]
}
EOF

# 3. IAMロールの作成
aws iam create-role \
    --role-name BedrockAgentCoreExecutionRole \
    --assume-role-policy-document file://trust-policy.json \
    --region us-east-1

# 4. インラインポリシーのアタッチ
aws iam put-role-policy \
    --role-name BedrockAgentCoreExecutionRole \
    --policy-name BedrockAgentCoreExecutionPolicy \
    --policy-document file://execution-policy.json \
    --region us-east-1

# 5. ロールARNの取得（後で使用）
aws iam get-role \
    --role-name BedrockAgentCoreExecutionRole \
    --query 'Role.Arn' \
    --output text
```

### 4. ECR リポジトリの作成

```bash
aws ecr create-repository \
    --repository-name agentcore-test \
    --region us-east-1
```

### 5. Bedrock Agent Core の設定とデプロイ

```bash
# IAMロールARNを環境変数に設定
export IAM_ROLE_ARN=<ステップ5で取得したARN>

# Bedrock Agent Coreの設定
agentcore configure --entrypoint main.py -er $IAM_ROLE_ARN

# 必要に応じて.bedrock_agentcore.yamlのリージョンを修正

aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws

# エージェントの起動
agentcore launch
```

## プロジェクト構成

- `main.py`: アプリケーションのエントリーポイント
- `requirements.txt`: プロジェクトの依存関係
- `pyproject.toml`: Python プロジェクトの設定
- `.bedrock_agentcore.yaml`: AWS Bedrock Agent Core の設定
- `Dockerfile`: デプロイ用のコンテナ定義

## カスタマイズ方法

`main.py`の`system_prompt`を変更することで、AI アシスタントの振る舞いをカスタマイズできます：

```python
agent = Agent(model=bedrock_model,
 system_prompt="You are a helpful AI assistant")  # ここを変更
```

### リージョンの確認

`.bedrock_agentcore.yaml`ファイル内のリージョン設定が正しいことを確認してください。特に、以下の項目が一致している必要があります：

```yaml
aws:
  region: us-east-1 # 使用するリージョン
  ecr_repository: YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/agentcore-test # 同じリージョン
```

## SAMを使用したAPI Gateway + Lambda構成

### 必要なツール

SAMを使用するためには、以下のツールが必要です：

```bash
# SAM CLIのインストール
pip install aws-sam-cli

# または、Homebrewを使用（macOS）
brew install aws-sam-cli
```

### SAMのビルドとデプロイ

```bash
# sam-lambdaディレクトリに移動
cd sam-lambda

# SAMアプリケーションのビルド
sam build

# ローカルでAPIを起動（テスト用）
sam local start-api

# AWSへのデプロイ
sam deploy --guided
```

### API Gatewayエンドポイントの使用方法

デプロイ後、以下のようにAPI Gatewayエンドポイントを使用できます：

```bash
# API Gatewayエンドポイントを使用したテスト
curl -X POST https://your-api-gateway-url/prod/invoke \
  -H "Content-Type: application/json" \
  -d '{"prompt": "こんにちは、元気ですか？"}'
```

### レスポンス形式

APIは以下の形式でレスポンスを返します：

```json
{
  "result": "AI からの応答メッセージ",
  "sessionId": "自動生成されたセッションID"
}
```

### SAM構成ファイル

SAM関連のファイルは `sam-lambda/` ディレクトリに整理されています：

- `sam-lambda/template.yaml`: SAMテンプレート（API Gateway + Lambda定義）
- `sam-lambda/lambda_handler.py`: Lambda関数のメインハンドラー
- `sam-lambda/requirements.txt`: Lambda用の依存関係

## ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

