import os
import argparse

import pandas as pd
from perfetto.trace_processor import TraceProcessor, TraceProcessorConfig

log_priority = {
    0: ['N', 'ANDROID_LOG_UNKNOWN'],
    1: ['T', 'ANDROID_LOG_DEFAULT'],
    2: ['V', 'ANDROID_LOG_VERBOSE'],
    3: ['D', 'ANDROID_LOG_DEBUG'],
    4: ['I', 'ANDROID_LOG_INFO'],
    5: ['W', 'ANDROID_LOG_WARN'],
    6: ['E', 'ANDROID_LOG_ERROR'],
    7: ['F', 'ANDROID_LOG_FATAL'],
    8: ['S', 'ANDROID_LOG_SILENT']
}

def write_logcat(df, log_path):
    # add a colomn for log priority string
    df['prio_str'] = df['prio'].apply(lambda x: log_priority[x][0])

    with open(log_path, 'w') as f:
        for _, row in df.iterrows():
            f.write(f"{row['ts']} {row['prio_str']}/{row['tag']}: {row['msg']}\n")

    print(f"Logcat written to {log_path}")


def main():
    parser = argparse.ArgumentParser(description='Extract logcat from trace')
    parser.add_argument('-f', '--file', help='Path to trace file', required=True)
    parser.add_argument('-o', '--output', help='Path to output file', required=True)
    parser.add_argument('-b', '--binary', help='Path to trace_processor binary', required=True)
    args = parser.parse_args()

    config = TraceProcessorConfig(bin_path=args.binary)
    try:
        processor = TraceProcessor(trace=args.file, config=config)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize TraceProcessor: {e}")

    sql_path = os.path.join(
        os.path.dirname(__file__), "sql", "select_logcat.sql"
    )
    with open(sql_path, "r") as f:
        query = f.read()

    # Execute the query and convert to DataFrame
    try:
        df = processor.query(query).as_pandas_dataframe()
    except Exception as e:
        processor.close()
        raise RuntimeError(f"Failed to execute SQL query: {e}")

    processor.close()

    print(f"Extracted {len(df)} logcat entries")

    expected_columns = [
        'id', 'type', 'ts', 'utid', 'prio', 'tag', 'msg', 'time_diff'
    ]

    if not all(col in df.columns for col in expected_columns):
        processor.close()
        raise RuntimeError(f"Missing columns in logcat DataFrame: {df.columns}")

    write_logcat(df, args.output)

if __name__ == "__main__":
    main()
