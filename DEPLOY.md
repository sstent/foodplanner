# Deploy App Workflow

This document defines the deployment configuration for the **Meal Planner (`foodplanner`)** application across development and production environments.

The actual deployment steps are handled centrally by the `deploy-app` agent skill.

---

## Environment Matrix

| Property | Development (`dev`) | Production (`main`) |
| :--- | :--- | :--- |
| **Git Branch** | `dev` | `main` |
| **Nomad Job** | `foodplanner-dev` | `foodplanner` |
| **Consul Service** | `foodplanner-dev` | `foodplanner` |
