variable "container_version" {
  default = "latest"
}

job "foodplanner" {
  datacenters = ["dc1"]

  type = "service"

  group "app" {
    count = 1

    network {
      port "http" {
        to = 8999
      }
    }

    service {
      name = "foodplanner"
      port = "http"

      check {
        type     = "http"
        path     = "/"
        interval = "10s"
        timeout  = "2s"
      }
    }


    task "app" {
      driver = "docker"

      config {
        image = "ghcr.io/sstent/foodplanner:${var.container_version}"
        ports = ["http"]
      }
      env {
        DATABASE_URL = "postgresql://postgres:postgres@master.postgres.service.dc1.consul/meal_planner"

      }
      resources {
        cpu    = 500
        memory = 1024
      }

      # Restart policy
      restart {
        attempts = 3
        interval = "10m"
        delay    = "15s"
        mode     = "fail"
      }
    }


  }
}