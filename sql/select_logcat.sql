SELECT
  *,
  (ts - trace_start()) as time_diff
FROM android_logs
ORDER BY time_diff DESC
