# PerfSets

It's a toolset to help dealing with `perfetto` tools:
- Automate executing & managing perfetto tracing sessions: [perf](#perf);
- Enhanced post process functions of tracing files: [draw_cpu](#draw_cpu);
- Extract logcat from a perfetto trace file that recorded with `logcat` data source enabled: [extract_logcat](#extract_logcat).

## perf
- Run perfetto tracing on an Android device.
- Collect tracing results from the device.
- Support detach mode and stop tracing by specific events

### Usage
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

## draw_cpu
Calculate and visualize CPU load from Perfetto trace files.

### Installation

Ensure you have Python 3.6 or higher installed. Install the required dependencies using `pip`:

```bash
python3 -m pip install pandas tqdm matplotlib perfetto-trace-processor
```

Install `trace_processor_shell` from the github release page: https://github.com/google/perfetto/releases.

Download the latest release package according to your platform, extract all files and path of the `trace_process_shell` will be passed to the script later.

### Usage
Run the `draw_cpu.py` script with the necessary arguments:

Options:

- `-f`, `--file`: Absolute path to the trace file. (Required)
- `-b`, `--binary`: Absolute path to the trace processor binary. (Required)
- `--window_size_ms`: Window size in milliseconds. If not provided, it is automatically calculated to have approximately 200 points.
- `--window_move_ms`: Window move (step) in milliseconds. If not provided, it is calculated based on the window size.
- `--output`: Base path to save the CPU load DataFrames as CSV files. (Optional)
Example:
```bash
python3 draw_cpu.py -f example/example.pb -b /path/to/trace_processor_shell
```
Example output:
![example output](media/example.png)

### Caveats
- **Trace File**: Ensure that the trace file is recorded with `sched/sched_switch` and `sched/sched_wakeup` categories enabled.
- **Trace Processor Binary**: Ensure that the trace processor binary path provided with the -b option is correct and executable.
- **Performance**: Processing very large trace files may consume significant memory and processing time.
- **Visualization**: Installing matplotlib is optional but required if you want to visualize the CPU load curves. If not installed, the script will skip the plotting step.
- **CPU Load Capping**: The script caps CPU load percentage at 100% to avoid unrealistic values.

## extract_logcat

Extract logcat from a perfetto trace file that recorded with `logcat` data source enabled.

### Installation

See the installation instructions for `draw_cpu`.

### Usage

Run the `extract_logcat.py` script with the necessary arguments:
```bash
python3 extract_logcat.py -f example/example.pb -b /path/to/trace_processor_shell -o output.log
```

## Todo
- [ ] `draw_cpu.py`: accelerate calculations by employing multi-threading.
