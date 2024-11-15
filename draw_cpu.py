import os
import argparse
import math

import pandas as pd
from perfetto.trace_processor import TraceProcessor, TraceProcessorConfig

from tqdm import tqdm  # Ensure tqdm is installed


def calculate_cpu_load_sliding_window_base(
    df: pd.DataFrame,
    window_size_ns: int,
    window_move_ns: int,
    num_cpus=None,
    per_core=False,
    progress_bar=None,
):
    """
    Calculate CPU load using a sliding window approach.

    Parameters:
    - df (pd.DataFrame): DataFrame containing running slices with columns ['ts_ns', 'dur', 'ucpu']
    - window_size_ns (int): Size of the window in nanoseconds.
    - window_move_ns (int): Step size to move the window in nanoseconds.
    - num_cpus (int): Number of unique CPU cores (required if per_core is False).
    - per_core (bool): Whether to calculate per-core CPU load.
    - progress_bar (tqdm.tqdm): Progress bar instance.

    Returns:
    - pd.DataFrame: DataFrame with window start time (ms) and CPU load percentage.
    """
    # Determine trace duration
    trace_end_ns = (df["ts_ns"] + df["dur"]).max()
    trace_start_ns = df["ts_ns"].min()

    # Total trace duration
    total_duration_ns = trace_end_ns - trace_start_ns

    # Generate window start times
    num_windows = (
        int(math.ceil((total_duration_ns - window_size_ns) / window_move_ns)) + 1
    ) - 4       # Last 4 windows are not accurate
    window_start_ns = [i * window_move_ns for i in range(num_windows)]

    # Initialize list to store CPU load per window
    cpu_loads = []

    def calculate_load_percentage(slice_df, start_ns, end_ns, num_cpus):
        overlapping = slice_df[
            (slice_df["ts_ns"] < end_ns)
            & ((slice_df["ts_ns"] + slice_df["dur"]) > start_ns)
        ]
        if overlapping.empty:
            return 0
        else:
            overlapping = overlapping.copy()
            overlapping["effective_start_ns"] = overlapping["ts_ns"].clip(
                lower=start_ns
            )
            overlapping["effective_end_ns"] = (
                overlapping["ts_ns"] + overlapping["dur"]
            ).clip(upper=end_ns)
            overlapping["overlap_ns"] = (
                overlapping["effective_end_ns"] - overlapping["effective_start_ns"]
            )
            overlapping["overlap_ns"] = overlapping["overlap_ns"].clip(lower=0)
            total_running_ns = overlapping["overlap_ns"].sum()
        cpu_load_percentage = (total_running_ns / (num_cpus * window_size_ns)) * 100
        cpu_load_percentage = min(cpu_load_percentage, 100.0)
        return cpu_load_percentage

    if per_core:
        cpu_list = sorted(df["ucpu"].unique())
        for ucpu in cpu_list:
            if progress_bar:
                window_iter = tqdm(
                    window_start_ns, desc=f"Calculating CPU {ucpu} Load", unit="win"
                )
            else:
                window_iter = window_start_ns
            for start_ns in window_iter:
                end_ns = start_ns + window_size_ns
                cpu_slices = df[df["ucpu"] == ucpu]

                cpu_load_percentage = calculate_load_percentage(
                    cpu_slices, start_ns, end_ns, 1
                )

                cpu_loads.append(
                    {
                        "window_start_ms": start_ns / 1_000_000,
                        "ucpu": ucpu,
                        "cpu_load_percentage": cpu_load_percentage,
                    }
                )
    else:
        if progress_bar:
            window_iter = tqdm(window_start_ns, desc="Calculating CPU Load", unit="win")
        else:
            window_iter = window_start_ns
        for start_ns in window_iter:
            end_ns = start_ns + window_size_ns
            cpu_load_percentage = calculate_load_percentage(df, start_ns, end_ns, num_cpus)
            cpu_loads.append(
                {
                    "window_start_ms": start_ns / 1_000_000,
                    "cpu_load_percentage": cpu_load_percentage,
                }
            )

    cpu_load_df = pd.DataFrame(cpu_loads)
    return cpu_load_df


def calculate_dynamic_window_params(total_duration_ns, desired_points=200):
    """
    Calculate window size and move in nanoseconds to achieve approximately desired_points.

    Parameters:
    - total_duration_ns (int): Total duration of the trace in nanoseconds.
    - desired_points (int): Desired number of points/windows.

    Returns:
    - tuple: (window_size_ns, window_move_ns)
    """
    # To have desired_points, window_move_ns = total_duration_ns / desired_points
    window_move_ns = total_duration_ns / desired_points

    # Set window_size_ns equal to window_move_ns for 100% overlap
    window_size_ns = window_move_ns

    return int(window_size_ns), int(window_move_ns)


def main():
    parser = argparse.ArgumentParser(
        description="Calculate CPU load over time from a Perfetto trace file."
    )
    parser.add_argument(
        "-f", "--file", help="Absolute path to trace", type=str, required=True
    )
    parser.add_argument(
        "-b",
        "--binary",
        help="Absolute path to a trace processor binary",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--window_size_ms",
        help="Window size in milliseconds. If not provided, calculated to have ~200 points.",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--window_move_ms",
        help="Window move (step) in milliseconds. If not provided, calculated based on window size.",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--output",
        help="Base path to save the CPU load DataFrames as CSV (optional)",
        type=str,
        default=None,
    )
    args = parser.parse_args()

    # Initialize TraceProcessor
    config = TraceProcessorConfig(bin_path=args.binary)
    try:
        print('Loading trace...')
        processor = TraceProcessor(trace=args.file, config=config)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize TraceProcessor: {e}")

    sql_path = os.path.join(
        os.path.dirname(__file__), "sql", "thread_running_slices.sql"
    )
    with open(sql_path, "r") as f:
        query = f.read()

    # Execute the query and convert to DataFrame
    try:
        df = processor.query(query).as_pandas_dataframe()
    except Exception as e:
        processor.close()
        raise RuntimeError(f"Failed to execute SQL query: {e}")

    print("Queried data frame: ")
    print("  size: ", df.shape)
    print("  columns: ", df.columns)
    print("  head: ", df.head())

    # Close the TraceProcessor
    processor.close()

    # Validate necessary columns
    required_columns = {"ts_ns", "dur", "ucpu"}
    if not required_columns.issubset(df.columns):
        raise ValueError(f"The DataFrame must contain columns: {required_columns}")

    # Determine trace duration
    trace_end_ns = (df["ts_ns"] + df["dur"]).max()
    trace_start_ns = df["ts_ns"].min()
    total_duration_ns = trace_end_ns - trace_start_ns

    # Check for excessively large durations
    max_windows = 2000
    if total_duration_ns <= 0:
        raise ValueError("Invalid trace duration calculated.")

    # Calculate window parameters
    if args.window_size_ms and args.window_move_ms:
        window_size_ns = args.window_size_ms * 1_000_000
        window_move_ns = args.window_move_ms * 1_000_000
        num_windows = (
            int(math.ceil((total_duration_ns - window_size_ns) / window_move_ns)) + 1
        )
    else:
        # Calculate window size and move to have approximately 200 points
        window_size_ns, window_move_ns = calculate_dynamic_window_params(
            total_duration_ns, desired_points=200
        )
        num_windows = (
            int(math.ceil((total_duration_ns - window_size_ns) / window_move_ns)) + 1
        )

    if num_windows > max_windows:
        raise ValueError(
            f"Number of windows ({num_windows}) exceeds the maximum allowed ({max_windows}). Please specify larger window size or larger window move."
        )

    # If window_size_ms or window_move_ms were not provided, convert the calculated values to ms
    if args.window_size_ms is None or args.window_move_ms is None:
        window_size_ms = window_size_ns / 1_000_000
        window_move_ms = window_move_ns / 1_000_000
        print(f"\nCalculated window parameters for ~200 points:")
        print(f"  Window Size: {window_size_ms:.2f} ms")
        print(f"  Window Move: {window_move_ms:.2f} ms")
    else:
        window_size_ms = args.window_size_ms
        window_move_ms = args.window_move_ms

    # Calculate number of CPUs
    num_cpus = df["ucpu"].nunique()
    if num_cpus == 0:
        raise ValueError("No CPUs found in the data.")

    # Calculate overall CPU load using sliding window with progress bar
    print("\nCalculating overall CPU load...")
    cpu_load_df = calculate_cpu_load_sliding_window_base(
        df,
        window_size_ns=window_size_ns,
        window_move_ns=window_move_ns,
        num_cpus=num_cpus,
        per_core=False,
        progress_bar=True,
    )
    print("Overall CPU Load Data Frame:")
    print(cpu_load_df.head())

    # Calculate per-CPU load using sliding window with progress bar
    print("\nCalculating per-CPU load...")
    cpu_load_per_core_df = calculate_cpu_load_sliding_window_base(
        df,
        window_size_ns=window_size_ns,
        window_move_ns=window_move_ns,
        num_cpus=num_cpus,
        per_core=True,
        progress_bar=True,
    )
    print("Per-CPU Load Data Frame:")
    print(cpu_load_per_core_df.head())

    # Optionally save the CPU load DataFrames to CSV files
    if args.output:
        try:
            # Ensure the output directory exists
            output_dir = os.path.dirname(args.output)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            # Save overall CPU load
            overall_output_path = args.output + "_overall.csv"
            cpu_load_df.to_csv(overall_output_path, index=False)
            print(f"\nOverall CPU load data saved to {overall_output_path}")

            # Save per-CPU load
            per_core_output_path = args.output + "_per_core.csv"
            cpu_load_per_core_df.to_csv(per_core_output_path, index=False)
            print(f"Per-CPU load data saved to {per_core_output_path}")
        except Exception as e:
            print(f"Failed to save CSV files: {e}")

    # Optionally, plot the CPU load curves
    try:
        import matplotlib.pyplot as plt

        # Create a figure with two subplots
        fig, axs = plt.subplots(2, 1, figsize=(15, 12), sharex=True)

        # Plot Overall CPU Load
        axs[0].plot(
            cpu_load_df["window_start_ms"],
            cpu_load_df["cpu_load_percentage"],
            marker="o",
            linestyle="-",
            color="blue",
            markersize=3,
        )
        axs[0].set_title("Overall CPU Load Over Time")
        axs[0].set_ylabel("CPU Load (%)")
        axs[0].grid(True)

        # Plot Per-CPU Load
        for ucpu in sorted(cpu_load_per_core_df["ucpu"].unique()):
            core_data = cpu_load_per_core_df[cpu_load_per_core_df["ucpu"] == ucpu]
            axs[1].plot(
                core_data["window_start_ms"],
                core_data["cpu_load_percentage"],
                marker="o",
                linestyle="-",
                label=f"CPU {ucpu}",
                markersize=3,
            )
        axs[1].set_title("Per-CPU Load Over Time")
        axs[1].set_xlabel("Time (ms)")
        axs[1].set_ylabel("CPU Load (%)")
        axs[1].legend()
        axs[1].grid(True)

        plt.tight_layout()
        plt.show()

    except ImportError:
        print(
            "\nmatplotlib is not installed. Install it to visualize the CPU load curves."
        )
    except Exception as e:
        print(f"\nFailed to plot CPU load curves: {e}")


if __name__ == "__main__":
    main()
