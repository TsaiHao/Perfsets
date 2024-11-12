import argparse

from perfetto.trace_processor import TraceProcessor, TraceProcessorConfig


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help="Absolute path to trace", type=str)
    parser.add_argument(
        "-b", "--binary", help="Absolute path to a trace processor binary", type=str
    )
    args = parser.parse_args()

    config = TraceProcessorConfig(bin_path=args.binary)

    processor = TraceProcessor(trace='./trace_0', config=config)

    with open("./cpu_load.sql", "r") as file:
        query = file.read()

    for _ in range(5):
        res_it = processor.query(query)
        for row in res_it:
            print(row)

    processor.close()


if __name__ == "__main__":
    main()
