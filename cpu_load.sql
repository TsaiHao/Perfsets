WITH 
desired_span AS (
  SELECT
    trace_start() + 6200 * 1000000 AS span_start_ns, -- Start time of the span
    trace_start() + 6500 * 1000000 AS span_end_ns -- End time of the span
),
cpu_count AS (
  SELECT
    COUNT(DISTINCT ucpu) AS num_cpus
  FROM
    cpu
),
overlapping_slices AS (
  SELECT
    th.ts AS slice_start_ns,
    th.ts + th.dur AS slice_end_ns
  FROM
    thread_state th,
    desired_span ds
  WHERE
    th.state = 'Running'
    AND th.ts < ds.span_end_ns
    AND (th.ts + th.dur) > ds.span_start_ns
),
overlapped_durations AS (
  SELECT
    CASE
      WHEN slice_start_ns < ds.span_start_ns THEN ds.span_start_ns
      ELSE slice_start_ns
    END AS effective_start_ns,
    CASE
      WHEN slice_end_ns > ds.span_end_ns THEN ds.span_end_ns
      ELSE slice_end_ns
    END AS effective_end_ns
  FROM
    overlapping_slices,
    desired_span ds
),
total_running_ns AS (
  SELECT
    SUM(effective_end_ns - effective_start_ns) AS total_running_ns
  FROM
    overlapped_durations
)
SELECT
  (
    1 - total_running_ns / (cpu_count.num_cpus * 1000000000.0)
  ) * 100 AS cpu_load_percentage
FROM
  total_running_ns,
  cpu_count;