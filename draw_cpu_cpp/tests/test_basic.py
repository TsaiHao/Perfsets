import cmake_example as m


def test_main():
    trace_start_ns = [0, 88, 112, 150]
    trace_end_ns = [110, 180, 200, 180]
    ucpu = [0, 1, 2, 3]
    trace_duration = 200
    window_size = 100
    window_step = 10

    res = m.calculate_cpu_load(trace_start_ns, trace_end_ns, ucpu, trace_duration, window_size, window_step)
    print(res)


if __name__ == "__main__":
    test_main()
