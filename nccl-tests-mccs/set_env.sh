export CUDA_HOME=/usr/local/cuda-12.1
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

export NCCL_HOME=/home/caoz0a/nccl/build
export LD_LIBRARY_PATH=$NCCL_HOME/lib:$LD_LIBRARY_PATH

# Add missing CUDA driver libraries
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH
