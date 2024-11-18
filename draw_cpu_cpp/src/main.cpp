#include <atomic>
#include <queue>
#include <vector>
#include <algorithm>
#include <cstdint>
#include <memory>
#include <iostream>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <mutex>
#include <condition_variable>
#include <thread>

#define STRINGIFY(x) #x
#define MACRO_STRINGIFY(x) STRINGIFY(x)

namespace py = pybind11;

inline int64_t ceil_div(int64_t a, int64_t b) {
    return (a + b - 1) / b;
}

struct TraceDetail {
    int64_t trace_duration_ns;
    int64_t window_size_ns;
    int64_t window_step_ns;
    int64_t num_windows;
};

static TraceDetail g_detail;

static void calculate_one_slice(
        int64_t start_ns,
        int64_t end_ns,
        std::vector<float> *result) {
    // Clamp slice within trace duration
    if(start_ns >= g_detail.trace_duration_ns || end_ns <=0) {
        return; // Slice is outside the trace
    }
    start_ns = std::max(int64_t(0), start_ns);
    end_ns = std::min(g_detail.trace_duration_ns, end_ns);
    if(start_ns >= end_ns) return;

    // Find window indices that overlap with [start_ns, end_ns)
    // i_start: first window where window_end > start_ns
    int64_t i_start;
    if(start_ns < g_detail.window_size_ns) {
        i_start = 0;
    }
    else {
        i_start = ceil_div(start_ns - g_detail.window_size_ns + 1, g_detail.window_step_ns);
    }
    // i_end: last window where window_start < end_ns
    int64_t i_end = (end_ns - 1) / g_detail.window_step_ns;

    // Clamp window indices
    i_start = std::max(int64_t(0), i_start);
    i_end = std::min(i_end, g_detail.num_windows - 1);

    if(i_start > i_end) return; // No overlapping windows

    for(int64_t w = i_start; w <= i_end; ++w) {
        int64_t window_start = w * g_detail.window_step_ns;
        int64_t window_end = window_start + g_detail.window_size_ns;

        // Calculate overlap between [start_ns, end_ns) and [window_start, window_end)
        int64_t overlap_start = std::max(start_ns, window_start);
        int64_t overlap_end = std::min(end_ns, window_end);
        if(overlap_start >= overlap_end) continue; // No overlap

        int64_t overlap = overlap_end - overlap_start;
        // Accumulate load
        result->at(w) += static_cast<float>(overlap) / g_detail.window_size_ns * 100.0f;
    }
}

class Executor {
public:
    struct Task {
        int64_t start_ns;
        int64_t end_ns;
    };

    explicit Executor(std::vector<float>* result);

    Executor(const Executor&) = delete;
    Executor& operator=(const Executor&) = delete;
    Executor(Executor&&) = delete;
    Executor& operator=(Executor&&) = delete;

    ~Executor();

    void start();
    void add_task(Task task);
    void wait_until_finish();
private:
    std::thread m_thread;
    std::queue<Task> m_tasks;
    std::mutex m_mutex;
    std::condition_variable m_condition;

    std::atomic<bool> m_done;
    std::vector<float>* m_result;
};

Executor::Executor(std::vector<float>* result): m_done(false), m_result(result) {
}

Executor::~Executor() {
    if (!m_done) {
        wait_until_finish();
    }
}

void Executor::start() {
    m_thread = std::thread([this] {
        while (true) {
            Task task;
            {
                std::unique_lock<std::mutex> lock(m_mutex);
                m_condition.wait(lock, [this] { return m_done || !m_tasks.empty(); });

                if (m_done && m_tasks.empty())
                    break;

                task = m_tasks.front();
                m_tasks.pop();
            }
            calculate_one_slice(task.start_ns, task.end_ns, m_result);
        }
    });
}

void Executor::add_task(Task task) {
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_tasks.push(task);
    }
    m_condition.notify_one();
}

void Executor::wait_until_finish() {
    {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_done = true;
    }
    m_condition.notify_all();
    if (m_thread.joinable())
        m_thread.join();
}

std::vector<std::vector<float>> calculate_cpu_load(
        const std::vector<int64_t> &slice_start_ns,
        const std::vector<int64_t> &slice_end_ns,
        const std::vector<int64_t> &ucpu_id,
        int64_t trace_duration_ns,
        int64_t window_size_ns,
        int64_t window_step_ns) {
    if (slice_start_ns.empty() || slice_start_ns.size() != slice_end_ns.size() || slice_start_ns.size() != ucpu_id.size()) {
        return {};
    }

    int64_t max_cpu_id = *std::max_element(ucpu_id.begin(), ucpu_id.end());
    int64_t num_cpus = max_cpu_id + 1;
    if (max_cpu_id > 32) {
        std::cerr << "Error: CPU ID is too large: " << max_cpu_id << std::endl;
        return {};
    }

    if(window_step_ns <=0 || window_size_ns <=0 || trace_duration_ns <=0) {
        return {};
    }
    
    int64_t num_windows = 1 + (trace_duration_ns >= window_size_ns ? 
                                (trace_duration_ns - window_size_ns) / window_step_ns : 0);
    
    std::vector<std::vector<float>> result(num_cpus + 2, std::vector<float>(num_windows, 0.0f));
    // layout: | cpu0 | cpu1 | ... | cpuN | overall | timestamp |

    g_detail = {trace_duration_ns, window_size_ns, window_step_ns, num_windows};

    std::cout << "Going to calculate load for " << num_windows << " windows" << std::endl;
    std::vector<std::unique_ptr<Executor>> executors;
    for (int i = 0; i < num_cpus; ++i) {
        std::unique_ptr<Executor> executor = std::make_unique<Executor>(&result[i]);
        executor->start();
        executors.push_back(std::move(executor));
    }

    for(size_t i = 0; i < slice_start_ns.size(); ++i) {
        executors[ucpu_id[i]]->add_task(Executor::Task{slice_start_ns[i], slice_end_ns[i]});
    }

    // fill up the timestamp column while waiting for the executors to finish
    for (int64_t w = 0; w < num_windows; ++w) {
        result[num_cpus + 1][w] = w * window_step_ns;
    }
    for (auto &executor : executors) {
        executor->wait_until_finish();
    }

    for (int64_t w = 0; w < num_windows; ++w) {
        float accumulated = 0.0f;
        for (int cpu = 0; cpu <= max_cpu_id; ++cpu) {
            // Todo: Not cache friendly
            accumulated += result[cpu][w];
        }
        float full_window = static_cast<float>(window_size_ns * num_cpus);
        accumulated = std::min(accumulated, full_window);
        result[num_cpus][w] = (accumulated / full_window) * 100.0f;
    }
    
    return result;
}


PYBIND11_MODULE(cpu_load_plugin, m) {
    m.doc() = R"pbdoc(
        C++ plugin for calculating CPU load from slices
        -----------------------

        .. currentmodule:: cpu_load_plugin

        .. autosummary::
           :toctree: _generate

        calculate_cpu_load
    )pbdoc";

    m.def("calculate_cpu_load", &calculate_cpu_load, R"pbdoc(
        Calculate overall and per-core cpu loads percentage
    )pbdoc");

#ifdef VERSION_INFO
    m.attr("__version__") = MACRO_STRINGIFY(VERSION_INFO);
#else
    m.attr("__version__") = "dev";
#endif
}
