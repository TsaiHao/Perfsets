SELECT 
    (ts - trace_start()) as ts_ns,
    (ts - trace_start() + dur) as ts_end_ns,
    ucpu
FROM thread_state 
WHERE state = 'Running'
