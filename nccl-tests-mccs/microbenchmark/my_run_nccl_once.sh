#!/usr/bin/env bash

# Set working directory to the directory where the script is located
WORKDIR=$(dirname "$(realpath "$0")")

# Function to print usage information
usage() {
    echo "Usage: $0 <num_gpus> <ring_type> <app>"
    echo "       num_gpus=1|2, ring_type=goodring|badring, app=allgather|allreduce"
}

# Check argument count
if [ $# -ne 3 ]; then
    usage
    exit 1
fi

# Parse arguments
num_gpus=$1
ring_type=$2
app_type=$3

# Set traffic class based on GPU count
case $num_gpus in
    1) tclass=106 ;;
    2) tclass=0 ;;
    *)
        echo "Error: num_gpus should be either '1' or '2', got $num_gpus"
        usage
        exit 1
        ;;
esac

# Show summary
echo "Num GPUs: $num_gpus"
echo "Ring type: $ring_type"
echo "App type: $app_type"
echo "Traffic class: $tclass"

# Generate hostfile
case $ring_type in
    goodring)
        cat > hostfile.$ring_type <<EOF
host1 slots=$num_gpus
host2 slots=$num_gpus
EOF
        ;;
    badring)
        cat > hostfile.$ring_type <<EOF
host2 slots=$num_gpus
host1 slots=$num_gpus
EOF
        ;;
    *)
        echo "Error: ring_type must be either 'goodring' or 'badring', got $ring_type"
        usage
        exit 1
        ;;
esac

# Select the NCCL app and datatype
case $app_type in
    allgather)
        app=all_gather_perf
        dtype=""  # AllGather doesn’t need --datatype
        ;;
    allreduce)
        app=all_reduce_perf
        dtype="--datatype=half"
        ;;
    *)
        echo "Error: app must be either 'allgather' or 'allreduce', got $app_type"
        usage
        exit 1
        ;;
esac

# Launch the NCCL test
mpirun --hostfile hostfile.$ring_type \
    -mca pml ob1 -mca btl tcp,self -mca btl_tcp_if_include rdma0 \
    -x CUDA_VISIBLE_DEVICES=$(seq -s ',' 0 $((num_gpus - 1))) \
    -x NCCL_DEBUG=INFO -x NCCL_ALGO=Ring -x NCCL_PROTO=Simple \
    -x NCCL_IB_GID_INDEX=0 -x NCCL_SOCKET_IFNAME=rdma0 \
    -x NCCL_MAX_NCHANNELS=2 -x NCCL_MIN_NCHANNELS=2 -x NCCL_IB_QPS_PER_CONNECTION=1 \
    -x NCCL_IB_TC=$tclass \
    "$WORKDIR/../build/$app" $dtype -b 32K -e 512M -f 4
