output "database_name" {
  description = "Glue catalog database name."
  value       = aws_glue_catalog_database.authpulse.name
}

output "auth_events_raw_table" {
  description = "Glue table name for raw auth events."
  value       = aws_glue_catalog_table.auth_events_raw.name
}

output "auth_events_curated_table" {
  description = "Glue table name for curated (risk-enriched) auth events."
  value       = aws_glue_catalog_table.auth_events_curated.name
}

output "user_behavior_hourly_table" {
  description = "Glue table name for per-user windowed feature aggregations."
  value       = aws_glue_catalog_table.user_behavior_hourly.name
}

output "host_popularity_daily_table" {
  description = "Glue table name for daily host access statistics."
  value       = aws_glue_catalog_table.host_popularity_daily.name
}
