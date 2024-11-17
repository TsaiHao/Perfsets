#include <vector>
#include <unordered_map>
#include <algorithm>
#include <set>
#include <cstdint>

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#define STRINGIFY(x) #x
#define MACRO_STRINGIFY(x) STRINGIFY(x)

namespace py = pybind11;


// Helper function to compute ceil division
inline int64_t ceil_div(int64_t a, int64_t b) {
    return (a + b - 1) / b;
}

std::vector<std::vector<float>> calculate_cpu_load(
        const std::vector<int64_t> &slice_start_ns,
        const std::vector<int64_t> &slice_end_ns,
        const std::vector<int64_t> &ucpu_id,
        int64_t trace_duration_ns,
        int64_t window_size_ns,
        int64_t window_step_ns) {
    
    // Step 1: Identify unique CPU IDs and sort them
    std::vector<int64_t> unique_cpu_ids = ucpu_id;
    std::sort(unique_cpu_ids.begin(), unique_cpu_ids.end());
    unique_cpu_ids.erase(std::unique(unique_cpu_ids.begin(), unique_cpu_ids.end()), unique_cpu_ids.end());
    int num_cpus = unique_cpu_ids.size();
    
    // Map CPU ID to index
    std::unordered_map<int64_t, int> cpu_id_to_index;
    for(int i = 0; i < num_cpus; ++i) {
        cpu_id_to_index[unique_cpu_ids[i]] = i;
    }
    
    // Step 2: Calculate number of windows
    if(window_step_ns <=0 || window_size_ns <=0 || trace_duration_ns <=0) {
        // Invalid parameters, return empty result
        return {};
    }
    
    int64_t num_windows = 1 + (trace_duration_ns >= window_size_ns ? 
                                (trace_duration_ns - window_size_ns) / window_step_ns : 0);
    
    // Initialize result vectors
    std::vector<std::vector<float>> result(num_cpus + 1, std::vector<float>(num_windows, 0.0f));
    // Last vector is for overall load
    
    // Step 3: Iterate through each slice and accumulate load
    for(size_t i = 0; i < slice_start_ns.size(); ++i) {
        int64_t S = slice_start_ns[i];
        int64_t E = slice_end_ns[i];
        int64_t cpu_id = ucpu_id[i];
        
        // Clamp slice within trace duration
        if(S >= trace_duration_ns || E <=0) {
            continue; // Slice is outside the trace
        }
        S = std::max(int64_t(0), S);
        E = std::min(trace_duration_ns, E);
        if(S >= E) continue;
        
        // Find window indices that overlap with [S, E)
        // i_start: first window where window_end > S
        int64_t i_start;
        if(S < window_size_ns) {
            i_start = 0;
        }
        else {
            i_start = ceil_div(S - window_size_ns + 1, window_step_ns);
        }
        // i_end: last window where window_start < E
        int64_t i_end = (E - 1) / window_step_ns;
        
        // Clamp window indices
        i_start = std::max(int64_t(0), i_start);
        i_end = std::min(i_end, num_windows - 1);
        
        if(i_start > i_end) continue; // No overlapping windows
        
        // Get CPU index
        auto it = cpu_id_to_index.find(cpu_id);
        if(it == cpu_id_to_index.end()) continue; // Unknown CPU ID
        int cpu_index = it->second;
        
        for(int64_t w = i_start; w <= i_end; ++w) {
            int64_t window_start = w * window_step_ns;
            int64_t window_end = window_start + window_size_ns;
            
            // Calculate overlap between [S, E) and [window_start, window_end)
            int64_t overlap_start = std::max(S, window_start);
            int64_t overlap_end = std::min(E, window_end);
            if(overlap_start >= overlap_end) continue; // No overlap
            
            int64_t overlap = overlap_end - overlap_start;
            // Accumulate load
            result[cpu_index][w] += static_cast<float>(overlap);
            result[num_cpus][w] += static_cast<float>(overlap); // Overall
        }
    }
    
    // Step 4: Convert accumulated times to percentages
    float window_size_f = static_cast<float>(window_size_ns);
    for(int cpu = 0; cpu < num_cpus; ++cpu) {
        for(int64_t w = 0; w < num_windows; ++w) {
            float accumulated = std::min(result[cpu][w], window_size_f);
            result[cpu][w] = (accumulated / window_size_f) * 100.0f;
        }
    }

    for (int64_t w = 0; w < num_windows; ++w) {
        float accumulated = std::min(result[num_cpus][w], window_size_f * num_cpus);
        result[num_cpus][w] = (accumulated / (window_size_f * num_cpus)) * 100.0f;
    }
    
    return result;
}


PYBIND11_MODULE(cmake_example, m) {
    m.doc() = R"pbdoc(
        Pybind11 example plugin
        -----------------------

        .. currentmodule:: cmake_example

        .. autosummary::
           :toctree: _generate

           add
           subtract
    )pbdoc";

    m.def("calculate_cpu_load", &calculate_cpu_load, R"pbdoc(
        Calculate overall and per-core cpu loads percentage
    )pbdoc");

    m.def("subtract", [](int i, int j) { return i - j; }, R"pbdoc(
        Subtract two numbers

        Some other explanation about the subtract function.
    )pbdoc");

#ifdef VERSION_INFO
    m.attr("__version__") = MACRO_STRINGIFY(VERSION_INFO);
#else
    m.attr("__version__") = "dev";
#endif
}
