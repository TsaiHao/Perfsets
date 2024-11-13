SELECT 
    (ts - trace_start()) as ts_ns,
    dur,
    state,
    ucpu,
    utid
FROM thread_state 
WHERE state = 'Running'