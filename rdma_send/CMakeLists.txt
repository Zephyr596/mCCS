cmake_minimum_required(VERSION 3.10)
project(rdma_send_demo C)

set(CMAKE_C_STANDARD 99)

add_executable(sender sender.c)
add_executable(receiver receiver.c)

target_link_libraries(sender rdmacm ibverbs)
target_link_libraries(receiver rdmacm ibverbs)

