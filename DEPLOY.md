# Deploy App Workflow

This document defines the standard procedure for deploying the **Meal Planner (`foodplanner`)** application across development and production environments.

---

## Environment Matrix

| Property | Development (`dev`) | Production (`main`) |
| :--- | :--- | :--- |
| **Git Branch** | `dev` | `main` |
| **Nomad Job** | `foodplanner-dev` | `foodplanner` |
| **Nomad Job File** | `foodplanner-dev.nomad` | `foodplanner.nomad` |
| **Docker Image Tag** | `ghcr.io/sstent/foodplanner:dev` and `:<sha>` | `ghcr.io/sstent/foodplanner:latest` and `:<sha>` |
| **Database** | `meal_planner_dev` (PostgreSQL) | `meal_planner` (PostgreSQL) |
| **Consul Service** | `foodplanner-dev` | `foodplanner` |
| **CI Build Workflow** | `Build and Push Docker Image (DEV)` (`build-and-push-dev.yml`) | `Build and Push Docker Image` (`build-and-push.yml`) |
| **CD Deploy Workflow** | `Deploy to Nomad (DEV)` (`nomad-deploy-dev.yml`) | `Deploy to Nomad` (`nomad-deploy.yml`) |

---

## Step 1: Branch Selection, Commit, and Push

1. Determine the target environment:
   - **Development**: Use the `dev` branch for testing new features, bug fixes, or database migrations.
   - **Production**: Merge verified changes into the `main` branch.
2. Check uncommitted changes:
   ```bash
   git status
   ```
3. Stage and commit changes with a conventional commit message:
   ```bash
   git add .
   git commit -m "feat/fix: <description of change>"
   ```
4. Push to the appropriate branch:
   - **For Dev**:
     ```bash
     git push origin dev
     ```
   - **For Production**:
     ```bash
     git checkout main
     git merge dev
     git push origin main
     ```
5. Record the pushed commit SHA (`git rev-parse HEAD`).

---

## Step 2: Monitor CI/CD Workflows

The CI/CD pipeline runs multi-stage automated workflows:
1. **Build & Push**: Builds the multi-architecture Docker image (`linux/amd64,linux/arm64`), pushes tags (`<branch>` and `<sha>`), and uploads build cache.
2. **Deploy to Nomad**: Triggered automatically on successful completion of the build workflow. It invokes `nomad job run` passing `-var="container_version=<sha>"`.

### Monitoring Steps
1. Open the repository Actions tab (GitHub or Gitea UI) or query the workflow status.
2. Ensure both the **Build and Push** and subsequent **Deploy to Nomad** workflow runs complete with status `success`.
3. **If CI fails**:
   - Inspect build/deploy logs in the Actions UI.
   - Investigate compile/dependency errors, Docker buildx issues, or Nomad connection timeouts (`NOMAD_ADDR`).
   - Do **not** proceed to Step 3 until CI succeeds.

---

## Step 3: Monitor Orchestration (Nomad)

Once the CD workflow runs `nomad job run`, Nomad pulls the new container image version and initiates rolling placement.

### Monitoring Commands
Use the `nomad-management` helper script or the native Nomad CLI:

- **Check Job Status**:
  ```bash
  # Dev:
  python skills/nomad-management/scripts/nomad.py status foodplanner-dev
  # or: nomad status foodplanner-dev

  # Production:
  python skills/nomad-management/scripts/nomad.py status foodplanner
  # or: nomad status foodplanner
  ```

- **List Allocations**:
  ```bash
  # Dev:
  python skills/nomad-management/scripts/nomad.py allocs foodplanner-dev

  # Production:
  python skills/nomad-management/scripts/nomad.py allocs foodplanner
  ```

- **Verify Allocation Transition**:
  - Locate the newest allocation ID matching the deployed commit SHA.
  - Confirm the allocation state transitions from `pending` -> `running`.
  - *Note*: Database migrations run automatically on container startup during FastAPI's lifespan event (`run_migrations()`).

### Troubleshooting Failing Allocations
If the allocation enters `failed` or task restarts:
1. Fetch allocation logs (stdout and stderr):
   ```bash
   python skills/nomad-management/scripts/nomad.py logs <alloc_id> app --tail 50
   # or: nomad alloc logs <alloc_id>
   ```
2. Diagnose common root causes:
   - Database connection errors or pending PostgreSQL migrations.
   - Missing environment variables or port binding conflicts.
   - Unhandled startup exceptions in `main.py` lifespan handler.

---

## Step 4: Post-Deployment Health Check & Service Discovery

After the Nomad allocation reaches `running` status, verify application responsiveness over the network.

> [!IMPORTANT]
> **Dynamic Port Allocation**: Do NOT hardcode host IP or port numbers. The application uses Nomad dynamic port mapping registered into Consul.

1. **Resolve Service Endpoint via Consul**:
   Use the `consul-management` helper script or query the Consul Catalog API:
   ```bash
   # Dev:
   python skills/consul-management/scripts/consul.py resolve foodplanner-dev

   # Production:
   python skills/consul-management/scripts/consul.py resolve foodplanner
   ```
   *(Alternative via HTTP API: `curl -s http://<consul-node>:8500/v1/catalog/service/foodplanner[-dev]`)*

2. **Execute Health Check**:
   Send an HTTP request to the dynamically resolved IP and Port:
   ```bash
   # Root route / dashboard check:
   curl.exe -s -I http://<SERVICE_IP>:<SERVICE_PORT>/

   # OpenAPI docs endpoint check:
   curl.exe -s -I http://<SERVICE_IP>:<SERVICE_PORT>/docs
   ```

3. **Validation**:
   - Verify HTTP status code returns `200 OK` (or `307/302` if redirection is configured).
   - If the endpoint fails to respond or returns 5xx errors, inspect container logs and Consul health check status (`python skills/consul-management/scripts/consul.py health`).
