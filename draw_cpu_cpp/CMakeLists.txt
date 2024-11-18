cmake_minimum_required(VERSION 3.4...3.18)
project(cpu_load_plugin)

# generate compile_commands.json for clangd
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_BUILD_TYPE Release)

add_subdirectory(pybind11)
pybind11_add_module(cpu_load_plugin src/main.cpp)

target_compile_definitions(cpu_load_plugin
                           PRIVATE VERSION_INFO=${EXAMPLE_VERSION_INFO})

target_include_directories(cpu_load_plugin PRIVATE ThreadPool)