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

    # Prestart restore task
    task "restore" {
      driver = "docker"
      lifecycle {
        hook    = "prestart"
        sidecar = false
      }
      config {
        image   = "litestream/litestream:latest"
        args = [
          "restore",
          "-if-replica-exists",
          "-if-db-not-exists",
          "-o", "/alloc/tmp/meal_planner.db",
          "sftp://root:odroid@192.168.4.63/mnt/Shares/litestream/foodplanner.db"
        ]
        volumes = [
         "/opt/nomad/data:/data"
        ]
      }
    }

    task "app" {
      driver = "docker"

      config {
        image = "ghcr.io/sstent/foodplanner:main"
        ports = ["http"]
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

    # Litestream sidecar for continuous replication
    task "litestream" {
      driver = "docker"
      lifecycle {
        hook    = "poststart" # runs after main task starts
        sidecar = true
      }
      config {
        image   = "litestream/litestream:latest"
        args = [
          "replicate",
          "/alloc/tmp/meal_planner.db",
          "sftp://root:odroid@192.168.4.63/mnt/Shares/litestream/foodplanner.db"
        ]
        volumes = [
         "/opt/nomad/data:/data"
        ]
      }
    }
  }
}