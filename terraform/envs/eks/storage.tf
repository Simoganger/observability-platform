# =============================================================================
# Object storage for logs & traces + least-privilege IRSA roles.
# =============================================================================
locals {
  telemetry_stores = {
    loki  = { bucket = "${var.cluster_name}-${data.aws_caller_identity.current.account_id}-loki-chunks", sa = "loki", retention_days = 31 }
    tempo = { bucket = "${var.cluster_name}-${data.aws_caller_identity.current.account_id}-tempo-traces", sa = "tempo", retention_days = 14 }
  }
}

resource "aws_s3_bucket" "telemetry" {
  for_each      = local.telemetry_stores
  bucket        = each.value.bucket
  force_destroy = true # lab convenience — set false in production
}

resource "aws_s3_bucket_public_access_block" "telemetry" {
  for_each                = aws_s3_bucket.telemetry
  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "telemetry" {
  for_each = aws_s3_bucket.telemetry
  bucket   = each.value.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Safety net: the apps enforce retention; lifecycle removes anything older.
resource "aws_s3_bucket_lifecycle_configuration" "telemetry" {
  for_each = aws_s3_bucket.telemetry
  bucket   = each.value.id
  rule {
    id     = "expire"
    status = "Enabled"
    filter {}
    expiration {
      days = local.telemetry_stores[each.key].retention_days + 7
    }
  }
}

resource "aws_iam_role" "telemetry" {
  for_each = local.telemetry_stores
  name     = "${var.cluster_name}-${each.key}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = module.eks.oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringLike = {
          "${module.eks.oidc_provider}:sub" = "system:serviceaccount:observability:${each.value.sa}*"
        }
        StringEquals = {
          "${module.eks.oidc_provider}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "telemetry" {
  for_each = local.telemetry_stores
  name     = "s3-access"
  role     = aws_iam_role.telemetry[each.key].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:ListBucket", "s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:GetObjectTagging", "s3:PutObjectTagging"]
      Resource = [aws_s3_bucket.telemetry[each.key].arn, "${aws_s3_bucket.telemetry[each.key].arn}/*"]
    }]
  })
}
