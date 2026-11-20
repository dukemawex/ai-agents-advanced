# Module 07: Production deploy with Docker and CI

**Time:** about 2 hours. **You need:** [Docker](https://docs.docker.com/get-started/get-docker/) for the container steps.

## Objectives

- Turn the intermediate API into a production-shaped service: config from the environment, health and readiness checks, request ids, structured logs and rate limits.
- Package it in a small, non-root Docker image.
- Build a CI pipeline that lints, tests offline, builds the image and publishes it.
- Plan a safe rollout and rollback.

## Concepts in plain English

"It works on my laptop" is not a deployment. Production adds a few habits, each simple on its own:

- **Twelve-factor config.** Settings (model, provider URL, keys, limits) come from **environment variables**, never from code. The same image runs in staging and production with different settings. Secrets come from your host's secret store, not from the image.
- **Health vs readiness.** `/healthz` says "the process is alive" (restart me if this fails). `/readyz` says "I can serve traffic now" (for example, the model provider is reachable). Load balancers use readiness to decide where to send requests.
- **Request ids.** Every request gets an `X-Request-ID`, returned in the response and written in every log line, so you can find one user's problem in a sea of logs.
- **Structured logs.** One JSON object per line with fields like `request_id`, `status` and `latency_ms`. Machines can search them. Do not log prompts or keys by default.
- **Rate limits.** A **token bucket** per API key: each key gets a bucket of N requests that refills steadily. Over the limit returns `429` with `Retry-After`. This protects your wallet and your provider quota.
- **Containers.** A Docker image bundles Python, your packages and your code. Use a slim base image, install dependencies before copying code (faster rebuilds), run as a **non-root user**, and add a health check.
- **CI/CD.** On every pull request: lint and offline tests. On main: build the image, tag it with the commit SHA, and push it to a registry such as GitHub Container Registry. Deploy by changing which tag runs, so **rollback** is just running the previous tag.

## Step by step

1. Run the service locally:
   ```bash
   export SERVICE_API_KEY=dev-key-change-me
   cd modules/07-production-deploy/solution
   uvicorn --factory service:create_app --port 8000
   ```
   Call it with `curl -H "X-API-Key: $SERVICE_API_KEY" -H "Content-Type: application/json" -d '{"message":"hi"}' localhost:8000/v1/chat` and look at the JSON logs.
2. Build and run the container (from the `solution/` folder):
   ```bash
   docker build -t course-agent:dev .
   docker run --rm -p 8000:8000 -e SERVICE_API_KEY=dev-key-change-me \
     -e LLM_BASE_URL=https://api.groq.com/openai/v1 -e LLM_API_KEY="$GROQ_API_KEY" \
     -e LLM_MODEL=llama-3.3-70b-versatile course-agent:dev
   ```
   To reach Ollama on your own machine from inside Docker, use `LLM_BASE_URL=http://host.docker.internal:11434/v1` (on Linux also add `--add-host=host.docker.internal:host-gateway`).
3. Read `solution/ci-example.yml`. Copy it to `.github/workflows/` in your own service repo to lint, test, build and push to GHCR.
4. In `starter/service.py`, complete `TokenBucket.allow()` and the request-id and logging middleware.
5. Test offline:
   ```bash
   TARGET=starter pytest modules/07-production-deploy
   ```

## Exercises

1. Add a `/metrics` endpoint with request counts and average latency (or use the OpenTelemetry metrics SDK).
2. Move the rate limiter's state to Redis so it works across several containers.
3. Deploy the image to a container host of your choice. Roll out a new tag, then roll back to the previous one.
4. Add a Docker image scan (for example `docker scout` or Trivy) to the CI example.

## Checkpoint quiz

1. What is the difference between `/healthz` and `/readyz`?
2. Why run the container as a non-root user?
3. Where should the API key for the model provider live in production?
4. How does tagging images with the commit SHA make rollback easy?

<details><summary>Answers</summary>

1. Health means the process is alive; readiness means it can serve requests right now (dependencies reachable).
2. If an attacker gets code execution, they get fewer permissions inside the container.
3. In the hosting platform's secret store, injected as an environment variable at runtime, never in the image or repo.
4. Every build has a unique, unchanging tag, so rolling back is just running the previous tag again.
</details>

## Further reading

- [The Twelve-Factor App](https://12factor.net/)
- FastAPI, [FastAPI in containers](https://fastapi.tiangolo.com/deployment/docker/)
- Docker, [Building best practices](https://docs.docker.com/build/building/best-practices/)
- GitHub Docs, [Publishing Docker images](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images)
- Uvicorn, [Deployment](https://uvicorn.dev/deployment/)
