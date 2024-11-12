# PerfSets

It's a toolset to help dealing with `perfetto` tools:
- arrage config parameters of `perfetto`;
- start `perfetto` tracing with the config and in different modes;
- stop `perfetto` by triggering specific events, such as logcat keywords, or frame drops;
- pull the trace file from the device;
- open trace files in the browser.

## Usage
### perf script
Regular mode: record a trace file in a specific duration.

```
options:
  -h, --help            show this help message and exit
  -a APP_NAME, --app_name APP_NAME
                        The name of the app to profile
  -p PREFIX, --prefix PREFIX
                        Prefix of the output file, the output file will be
                        {prefix}_{i}
  -f FLUSH_PERIOD_MS, --flush_period_ms FLUSH_PERIOD_MS
                        The flush period of the perfetto
  -o, --open_in_browser
                        Open the trace in browser, open_trace_in_ui must be in the
                        PATH
  -m, --memory          Enable memory profiling
  -b BUFFER_SIZE_KB, --buffer_size_kb BUFFER_SIZE_KB
                        The buffer size of the perfetto
  -d DURATION, --duration DURATION
                        The time to run the perfetto, in seconds
  -ws FILE_WRITE_PERIOD_MS, --file_write_period_ms FILE_WRITE_PERIOD_MS
                        The file write period of the perfetto
```

Detach mode: record a trace file until a specific event happens.

```
usage: perf detach [-h] [-a APP_NAME] [-p PREFIX] [-f FLUSH_PERIOD_MS] [-o] [-m]
                   [-e EVENT] [-b BUFFER_SIZE_KB] [-dl DELAY_SECONDS]
                   [-w WINDOW_SIZE] [-t THRESHOLD] [-k KEYWORD]

options:
  -h, --help            show this help message and exit
  -a APP_NAME, --app_name APP_NAME
                        The name of the app to profile
  -p PREFIX, --prefix PREFIX
                        Prefix of the output file, the output file will be
                        {prefix}_{i}
  -f FLUSH_PERIOD_MS, --flush_period_ms FLUSH_PERIOD_MS
                        The flush period of the perfetto
  -o, --open_in_browser
                        Open the trace in browser, open_trace_in_ui must be in the
                        PATH
  -m, --memory          Enable memory profiling
  -e EVENT, --event EVENT
                        The event to trigger stopping the perfetto. Available
                        events: frame_drop, log_keyword. Default value will be
                        guessed based on other arguments
  -b BUFFER_SIZE_KB, --buffer_size_kb BUFFER_SIZE_KB
                        The buffer size of the perfetto. This will be size of the
                        utimate output file, so keep it small. According to
                        experience, 1 second of trace is about 2-3MB
  -dl DELAY_SECONDS, --delay_seconds DELAY_SECONDS
                        Seconds to delay after the event is triggered and before
                        stopping the perfetto
  -w WINDOW_SIZE, --window-size WINDOW_SIZE
                        The window size to detect frame drop
  -t THRESHOLD, --threshold THRESHOLD
                        The threshold to detect frame drop
  -k KEYWORD, --keyword KEYWORD
                        The keyword to trigger stopping the perfetto
```

## Todo
- [ ] `cpu_load.sql`: a script to calculate the CPU load of the trace file