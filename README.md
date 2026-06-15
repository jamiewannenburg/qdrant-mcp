# Qdrant MCP Server

A [FastMCP](https://gofastmcp.com) server that provides semantic memory capabilities using the [Qdrant](https://qdrant.tech) vector database with configurable embedding providers. Tools are exposed over stdio (for local MCP clients) or streamable HTTP (for Docker and Google Cloud Run).

## Features

- **Multiple Embedding Providers**:
  - OpenAI (`text-embedding-3-small`, `text-embedding-3-large`, `text-embedding-ada-002`)
  - Sentence Transformers (`all-MiniLM-L6-v2`, `all-mpnet-base-v2`, and more)
- **Semantic Search**: Store and retrieve information using vector similarity
- **Namespaced Tools**: Default `NAMESPACE=qdrant` exposes `qdrant_store`, `qdrant_find`, etc.
- **Flexible Configuration**: Environment variables for all settings
- **HTTP + stdio**: Run locally with stdio or deploy to Cloud Run over streamable HTTP

## Installation

### Via uvx (Recommended for MCP)

The server is designed to be lightweight by default. When using OpenAI embeddings:

```bash
# For OpenAI embeddings (lightweight, no ML dependencies)
uvx qdrant-mcp
```

For local embeddings with Sentence Transformers:

```bash
# For local embeddings (includes torch and other ML libraries)
uvx --with sentence-transformers qdrant-mcp
```

### Via pip (Development)

```bash
git clone https://github.com/andrewlwn77/qdrant-mcp.git
cd qdrant-mcp

# Basic install (OpenAI embeddings only)
pip install -e .

# With local embeddings support
pip install -e . sentence-transformers
```

## Configuration

### Required Environment Variables

- `EMBEDDING_PROVIDER`: Choose between `openai` or `sentence-transformers`
- `EMBEDDING_MODEL`: Model name for the chosen provider
- `OPENAI_API_KEY`: Required when using OpenAI embeddings

### Optional Environment Variables

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant server URL |
| `QDRANT_API_KEY` | *(none)* | Qdrant API key |
| `COLLECTION_NAME` | `mcp_memory` | Qdrant collection name |
| `NAMESPACE` | `qdrant` | Prefix for MCP tool names |
| `DEVICE` | auto-detect | Device for sentence transformers |
| `DEFAULT_LIMIT` | `10` | Default search results limit |
| `SCORE_THRESHOLD` | `0.0` | Minimum similarity score |
| `AUTH_BEARER_TOKEN` | *(none)* | Bearer token required on HTTP requests |
| `FASTMCP_HOST` | `0.0.0.0` | HTTP bind address |
| `FASTMCP_PORT` | `8000` | HTTP listen port |
| `FASTMCP_TRANSPORT` | `streamable-http` | HTTP transport mode |

### Example Configuration

```bash
# OpenAI embeddings
export EMBEDDING_PROVIDER=openai
export EMBEDDING_MODEL=text-embedding-3-small
export OPENAI_API_KEY=your-api-key
export QDRANT_URL=https://your-qdrant.example.com
export QDRANT_API_KEY=your-qdrant-api-key
export NAMESPACE=qdrant
```

## Namespacing

Tools are registered with short names (`store`, `find`, `delete`, `list_collections`, `collection_info`) and prefixed at runtime using FastMCP's [`Namespace`](https://gofastmcp.com/servers/transforms/namespace) transform. By default `NAMESPACE=qdrant`, so clients see:

| Internal name | Exposed tool name |
| ------------- | ----------------- |
| `store` | `qdrant_store` |
| `find` | `qdrant_find` |
| `delete` | `qdrant_delete` |
| `list_collections` | `qdrant_list_collections` |
| `collection_info` | `qdrant_collection_info` |

Set a different prefix when running multiple MCP servers in one client:

```bash
export NAMESPACE=memory
# Tools become: memory_store, memory_find, ...
```

Disable prefixing (expose bare `find`, `store`, etc.):

```bash
export NAMESPACE=
```

Or pass `--namespace` when running the HTTP server directly:

```bash
python -m qdrant_mcp.server --namespace memory
```

## Supported Embedding Models

### OpenAI Models
- `text-embedding-3-small` (1536 dimensions) — Default
- `text-embedding-3-large` (3072 dimensions)
- `text-embedding-ada-002` (1536 dimensions) — Legacy

### Sentence Transformers Models
- `all-MiniLM-L6-v2` (384 dimensions) — Fast and efficient
- `all-mpnet-base-v2` (768 dimensions) — Higher quality
- Any other Sentence Transformers model from Hugging Face

## Usage

### stdio (local MCP clients)

```bash
qdrant-mcp
# or
python -m qdrant_mcp.server
```

### HTTP (Docker / remote clients)

```bash
python -m qdrant_mcp.server
# MCP endpoint: http://localhost:8000/mcp
```

### Docker

```bash
docker compose up --build
```

This starts Qdrant on port `6333` and the MCP server on port `8000`. Copy `.env.example` to `.env` and set your API keys before starting.

```bash
docker build -t qdrant-mcp .
docker run --rm -p 8000:8000 --env-file .env qdrant-mcp
```

### MCP Tools

With the default namespace, tools are named `qdrant_store`, `qdrant_find`, etc.

#### qdrant_store
Store content with semantic embeddings:

```json
{
  "content": "The capital of France is Paris",
  "metadata": "{\"category\": \"geography\", \"type\": \"fact\"}",
  "id": "optional-custom-id"
}
```

#### qdrant_find
Search for relevant information:

```json
{
  "query": "What is the capital of France?",
  "limit": 5,
  "filter": "{\"category\": \"geography\"}",
  "score_threshold": 0.7
}
```

#### qdrant_delete
Delete stored items:

```json
{
  "ids": "id1,id2,id3"
}
```

#### qdrant_list_collections
List all collections in Qdrant.

#### qdrant_collection_info
Get information about the current collection.

## Integration with Claude Desktop

### For OpenAI Embeddings (stdio)

```json
{
  "mcpServers": {
    "qdrant-memory": {
      "command": "uvx",
      "args": ["qdrant-mcp"],
      "env": {
        "EMBEDDING_PROVIDER": "openai",
        "EMBEDDING_MODEL": "text-embedding-3-small",
        "OPENAI_API_KEY": "your-api-key",
        "QDRANT_URL": "https://your-instance.qdrant.io",
        "QDRANT_API_KEY": "your-qdrant-api-key",
        "NAMESPACE": "qdrant"
      }
    }
  }
}
```

### For HTTP (Cursor / remote)

```json
{
  "mcpServers": {
    "qdrant-memory": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

## Deploy to Google Cloud Run

Cloud Run can host this MCP server as a stateless HTTP service. Qdrant itself should run separately (see [Setting up Qdrant on Google Cloud](#setting-up-qdrant-on-google-cloud) below); point `QDRANT_URL` at that instance.

### Prerequisites

1. Install and authenticate the Google Cloud CLI:

   ```bash
   gcloud auth login
   gcloud config set project PROJECT_ID
   ```

2. Enable required APIs:

   ```bash
   gcloud services enable run.googleapis.com secretmanager.googleapis.com
   ```

3. Create a dedicated service account (recommended):

   ```bash
   gcloud iam service-accounts create qdrant-mcp \
     --display-name="qdrant-mcp Cloud Run"

   SA_EMAIL="qdrant-mcp@PROJECT_ID.iam.gserviceaccount.com"
   ```

4. Optional: store secrets in Secret Manager.

   Create secrets for API keys the server needs at runtime:

   ```bash
   printf "%s" "your-openai-key" | gcloud secrets create openai-api-key \
     --replication-policy="automatic" --data-file=-

   printf "%s" "your-qdrant-key" | gcloud secrets create qdrant-api-key \
     --replication-policy="automatic" --data-file=-

   AUTH_TOKEN="$(openssl rand -base64 48)"
   printf "%s" "${AUTH_TOKEN}" | gcloud secrets create qdrant-mcp-auth-token \
     --replication-policy="automatic" --data-file=-

   for SECRET in openai-api-key qdrant-api-key qdrant-mcp-auth-token; do
     gcloud secrets add-iam-policy-binding "${SECRET}" \
       --member="serviceAccount:${SA_EMAIL}" \
       --role="roles/secretmanager.secretAccessor"
   done
   ```

   Save `AUTH_TOKEN` in your password manager; MCP clients must send `Authorization: Bearer TOKEN` on every request when `AUTH_BEARER_TOKEN` is set.

### Deploy from source

```bash
gcloud run deploy qdrant-mcp \
  --source . \
  --region REGION \
  --port 8000 \
  --service-account="${SA_EMAIL}" \
  --min-instances 0 \
  --set-env-vars "EMBEDDING_PROVIDER=openai,EMBEDDING_MODEL=text-embedding-3-small,QDRANT_URL=https://YOUR_QDRANT_URL,COLLECTION_NAME=mcp_memory,NAMESPACE=qdrant" \
  --set-secrets "OPENAI_API_KEY=openai-api-key:latest,QDRANT_API_KEY=qdrant-api-key:latest,AUTH_BEARER_TOKEN=qdrant-mcp-auth-token:latest"
```

Omit `--set-secrets AUTH_BEARER_TOKEN=...` if you do not want application-level bearer authentication.

If your MCP client cannot mint Google Cloud Run IAM tokens and you rely on `AUTH_BEARER_TOKEN`, add `--allow-unauthenticated`. The application middleware still rejects requests without the correct bearer token.

Keep the service private (default) when clients can authenticate with Cloud Run IAM instead.

### Deploy a pre-built image

```bash
docker build -t gcr.io/PROJECT_ID/qdrant-mcp:latest .
docker push gcr.io/PROJECT_ID/qdrant-mcp:latest

gcloud run deploy qdrant-mcp \
  --image gcr.io/PROJECT_ID/qdrant-mcp:latest \
  --region REGION \
  --port 8000 \
  --service-account="${SA_EMAIL}" \
  --set-env-vars "EMBEDDING_PROVIDER=openai,EMBEDDING_MODEL=text-embedding-3-small,QDRANT_URL=https://YOUR_QDRANT_URL,NAMESPACE=qdrant" \
  --set-secrets "OPENAI_API_KEY=openai-api-key:latest,QDRANT_API_KEY=qdrant-api-key:latest,AUTH_BEARER_TOKEN=qdrant-mcp-auth-token:latest"
```

After deployment, connect your MCP client to:

```text
https://SERVICE_URL/mcp
```

Get the service URL:

```bash
gcloud run services describe qdrant-mcp \
  --region REGION \
  --format='value(status.url)'
```

### Cursor configuration (Cloud Run)

```json
{
  "mcpServers": {
    "qdrant-memory": {
      "url": "https://SERVICE_URL/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_AUTH_TOKEN"
      }
    }
  }
}
```

References:

- [Cloud Run deploy reference](https://cloud.google.com/sdk/gcloud/reference/run/deploy)
- [Cloud Run secrets](https://cloud.google.com/run/docs/configuring/services/secrets)

## Setting up Qdrant on Google Cloud

This MCP server is a **client** of Qdrant. You need a running Qdrant instance before deploying the MCP server. Choose an option based on workload size and durability requirements.

### Option 1: Qdrant Cloud (managed, recommended for production)

[Qdrant Cloud](https://cloud.qdrant.io/) is the simplest path: fully managed clusters with backups, scaling, and a stable HTTPS endpoint.

1. Create a cluster at [cloud.qdrant.io](https://cloud.qdrant.io/).
2. Copy the cluster URL and API key.
3. Set in your MCP server environment:

   ```bash
   QDRANT_URL=https://xxxxxxxx.qdrant.io
   QDRANT_API_KEY=your-cluster-api-key
   ```

No GCP infrastructure to manage; billing is through Qdrant Cloud.

### Option 2: Qdrant on Cloud Run (dev / small workloads)

You can run the official `qdrant/qdrant` container on Cloud Run for low-traffic or development use. Qdrant keeps indexes in memory and writes data to disk, so treat this as **single-instance only**.

Important constraints:

- Set `--min-instances 1` to avoid cold starts reloading large HNSW indexes.
- Set `--max-instances 1` — Qdrant is a single-writer store; multiple Cloud Run instances cannot safely share one collection.
- Use a **Cloud Storage volume mount** (GCS FUSE) for persistence across restarts. Ephemeral container disk alone will lose data when the instance is recycled.

Example deploy:

```bash
gcloud services enable run.googleapis.com storage.googleapis.com

# Bucket for Qdrant storage
gcloud storage buckets create gs://QDRANT_BUCKET --location=REGION

gcloud iam service-accounts create qdrant-db \
  --display-name="Qdrant database Cloud Run"
QDRANT_SA="qdrant-db@PROJECT_ID.iam.gserviceaccount.com"

gcloud storage buckets add-iam-policy-binding gs://QDRANT_BUCKET \
  --member="serviceAccount:${QDRANT_SA}" \
  --role="roles/storage.objectAdmin"

QDRANT_API_KEY="$(openssl rand -base64 32)"

gcloud run deploy qdrant-db \
  --image docker.io/qdrant/qdrant:latest \
  --region REGION \
  --port 6333 \
  --execution-environment gen2 \
  --min-instances 1 \
  --max-instances 1 \
  --memory 2Gi \
  --cpu 2 \
  --service-account="${QDRANT_SA}" \
  --set-env-vars "QDRANT__SERVICE__API_KEY=${QDRANT_API_KEY}" \
  --add-volume name=qdrant-storage,type=cloud-storage,bucket=QDRANT_BUCKET \
  --add-volume-mount volume=qdrant-storage,mount-path=/qdrant/storage
```

After deploy, use the Cloud Run service URL as `QDRANT_URL` (include `https://`) and the API key you generated.

References:

- [Cloud Run Cloud Storage volume mounts](https://cloud.google.com/run/docs/configuring/services/cloud-storage-volume-mounts)
- [Qdrant configuration via environment variables](https://qdrant.tech/documentation/guides/configuration/)

### Option 3: Qdrant on GKE (production / HA)

For production workloads needing persistent SSD storage, rolling updates, and optional distributed mode, deploy Qdrant on [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine).

Google publishes an official tutorial: [Deploy a Qdrant vector database on GKE](https://cloud.google.com/kubernetes-engine/docs/tutorials/deploy-qdrant).

High-level steps:

1. Create a GKE cluster (Standard or Autopilot).
2. Add the Qdrant Helm chart repository:

   ```bash
   helm repo add qdrant https://qdrant.github.io/qdrant-helm
   helm repo update
   ```

3. Deploy Qdrant as a StatefulSet with a persistent volume:

   ```bash
   helm install qdrant qdrant/qdrant \
     --set persistence.size=50Gi \
     --set apiKey=true
   ```

4. Expose Qdrant inside the VPC (internal Load Balancer or port-forward for testing):

   ```bash
   kubectl port-forward svc/qdrant 6333:6333
   ```

5. Point the MCP server at the internal service URL from Cloud Run (via VPC connector) or from clients inside the same VPC.

Use GKE when you need durable storage, more than 1 vCPU / 2 GiB RAM, or Qdrant's distributed cluster mode. Cloud Run is simpler but limited to a single instance.

### Option 4: Compute Engine VM (simple self-managed)

For a single-node setup with a persistent disk and minimal orchestration:

```bash
gcloud compute instances create qdrant-vm \
  --zone=ZONE \
  --machine-type=e2-standard-2 \
  --boot-disk-size=50GB \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud

# SSH in, install Docker, run:
# docker run -p 6333:6333 -v /mnt/qdrant:/qdrant/storage qdrant/qdrant
```

Restrict firewall rules to your MCP server IP or VPC only. Assign a static internal IP or use Cloud NAT for private access from Cloud Run via a [VPC connector](https://cloud.google.com/vpc/docs/configure-serverless-vpc-access).

### Choosing an option

| Option | Best for | Persistence | Scaling |
| ------ | -------- | ----------- | ------- |
| Qdrant Cloud | Production without ops overhead | Managed | Managed |
| Cloud Run | Dev / prototypes | GCS FUSE mount | Single instance only |
| GKE | Production on GCP | Regional SSD PVCs | StatefulSet / distributed |
| Compute Engine | Simple self-hosted | Attached disk | Manual |

## Development

### Running Tests

```bash
pip install -e ".[dev]"
pytest

# Type checking
mypy src/

# Linting
ruff check src/
```

### Project Structure

```
qdrant-mcp/
├── src/
│   └── qdrant_mcp/
│       ├── server.py           # MCP server (stdio + HTTP)
│       ├── settings.py         # Configuration management
│       ├── qdrant_memory.py    # Qdrant operations
│       └── embeddings/
│           ├── base.py
│           ├── factory.py
│           ├── openai.py
│           └── sentence_transformers.py
├── Dockerfile
├── docker-compose.yml
└── tests/
```

## License

Apache License 2.0

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
