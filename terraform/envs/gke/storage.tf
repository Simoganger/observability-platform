# GCS buckets + one Google service account per backend, bound to the
# Kubernetes service accounts via Workload Identity (no keys anywhere).
locals {
  telemetry_stores = {
    loki  = { bucket = "${var.project_id}-${var.cluster_name}-loki-chunks", sa = "loki", retention_days = 31 }
    tempo = { bucket = "${var.project_id}-${var.cluster_name}-tempo-traces", sa = "tempo", retention_days = 14 }
  }
}

resource "google_storage_bucket" "telemetry" {
  for_each                    = local.telemetry_stores
  name                        = each.value.bucket
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true # lab convenience — false in production
  lifecycle_rule {
    condition {
      age = each.value.retention_days + 7
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_service_account" "telemetry" {
  for_each     = local.telemetry_stores
  account_id   = each.key
  display_name = "${each.key} object storage access"
}

resource "google_storage_bucket_iam_member" "telemetry" {
  for_each = local.telemetry_stores
  bucket   = google_storage_bucket.telemetry[each.key].name
  role     = "roles/storage.objectAdmin"
  member   = "serviceAccount:${google_service_account.telemetry[each.key].email}"
}

resource "google_service_account_iam_member" "workload_identity" {
  for_each           = local.telemetry_stores
  service_account_id = google_service_account.telemetry[each.key].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[observability/${each.value.sa}]"
  depends_on         = [google_container_cluster.this]
}
