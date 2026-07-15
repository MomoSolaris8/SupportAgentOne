# Private Cloud Deployment

SupportAgent is split into stateless application services and managed stateful services:

- `frontend`: Next.js UI and API proxy.
- `backend`: FastAPI, RAG, MCP client, auth, uploads, memory.
- `postgres`: PostgreSQL with pgvector for RAG chunks, memory, sessions, MCP config, audit logs.
- `object storage`: MinIO/S3-compatible storage for uploaded images.

## Recommended Private Cloud Shape

```text
Browser
  -> Ingress / Nginx / Traefik
  -> Next.js frontend service
  -> FastAPI backend service
  -> PostgreSQL + pgvector
  -> MinIO / S3-compatible object storage
```

The frontend and backend are stateless containers. PostgreSQL and object storage are stateful services.
Secrets should be injected through Vault, Kubernetes Secrets, or the private cloud platform secret manager.

## Local Private-Cloud-Style Compose

Create a production env file outside git:

```bash
cp .env.example .env.prod
```

Set at least:

```env
POSTGRES_PASSWORD=replace-with-password
MINIO_ROOT_USER=supportagent
MINIO_ROOT_PASSWORD=replace-with-long-secret

EMBEDDING_API_KEY=replace-with-dashscope-key
EMBEDDING_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
CHAT_MODEL=qwen-plus
VISION_MODEL=qwen-vl-plus

FRONTEND_URL=https://supportagent.example.internal
NEXT_PUBLIC_BACKEND_API_URL=https://supportagent-api.example.internal

MICROSOFT_CLIENT_ID=replace-with-client-id
MICROSOFT_CLIENT_SECRET=replace-with-client-secret
MICROSOFT_TENANT=consumers
MICROSOFT_REDIRECT_URI=https://supportagent-api.example.internal/auth/microsoft/callback
```

Run:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up --build
```

For a single VM demo, open:

```text
http://localhost:3000
```

MinIO console:

```text
http://localhost:9001
```

## Supabase vs Private Cloud

For public cloud demos, use:

```env
FILE_STORAGE_PROVIDER=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=replace-with-service-role-key
SUPABASE_STORAGE_BUCKET=supportagent-uploads
DATABASE_URL=postgresql://...
```

For private cloud, use:

```env
FILE_STORAGE_PROVIDER=s3
S3_ENDPOINT_URL=http://minio:9000
S3_REGION=us-east-1
S3_BUCKET=supportagent-uploads
S3_ACCESS_KEY_ID=supportagent
S3_SECRET_ACCESS_KEY=replace-with-secret
DATABASE_URL=postgresql://supportagent:password@postgres:5432/supportagent
```

The frontend does not need to know which storage provider is used. It uploads to the backend, and the backend writes to Supabase or S3-compatible storage through the storage abstraction.

## Kubernetes Mapping

Use the same service split:

- `Deployment/supportagent-frontend`
- `Deployment/supportagent-backend`
- `StatefulSet/postgres` or enterprise managed PostgreSQL
- `StatefulSet/minio` or enterprise S3-compatible object storage
- `Ingress/supportagent`
- `Secret/supportagent-secrets`
- `ConfigMap/supportagent-config`

Health checks:

```text
GET /health  -> process is alive
GET /ready   -> database connection is ready
```

Backend probe examples:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
readinessProbe:
  httpGet:
    path: /ready
    port: 8000
```

## Interview Explanation

In production private cloud, do not store uploaded images on local disk and do not hardcode secrets in `.env`.
The application containers stay stateless, PostgreSQL/pgvector stores structured state, MinIO stores binary uploads, and MCP servers are registered as internal services. Tool calls are audited in Postgres and write operations require confirmation.
