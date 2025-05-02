import toml
import os

host_addrs = {
    1: "10.200.2.2",
    2: "10.200.2.1",
    3: "10.200.2.3",
    4: "10.200.2.4"
}


class BenchArgs:
    def __init__(self, root_addr, rank, num_ranks, cuda_dev, size, comm, round):
        self.root_addr = root_addr
        self.rank = rank
        self.num_ranks = num_ranks
        self.cuda_dev = cuda_dev
        self.size = size
        self.comm = comm
        self.round = round

    def get_args(self):
        return f"--root-addr {self.root_addr} --rank {self.rank} " \
               f"--num-ranks {self.num_ranks} --cuda-device-idx {self.cuda_dev} " \
               f"--size {self.size} --communicator {self.comm} --round {self.round} --size-in-byte"


def convert_size(size_str):
    if size_str.endswith("K"):
        return int(size_str[:-1]) * 1024
    elif size_str.endswith("M"):
        return int(size_str[:-1]) * 1024 * 1024
    elif size_str.endswith("G"):
        return int(size_str[:-1]) * 1024 * 1024 * 1024
    else:
        return int(size_str)


def generate_config(name, group, binary, root_id, machine_map, size, comm, daemon_args=""):
    def gen_daemon(machine_id):
        return {
            "host": f"host{machine_id}",
            "bin": "mccs",
            "args": f"--host {machine_id} {daemon_args}",
            "weak": True,
            "dependencies": [],
        }

    root_addr = host_addrs[root_id]
    num_ranks = sum([gpu_cnt for _, gpu_cnt in machine_map])
    workers = [gen_daemon(mid) for mid, _ in machine_map]
    dep = [i for i in range(len(machine_map))]

    global_rank = 0
    for mid, gpu_cnt in machine_map:
        for local_rank in range(gpu_cnt):
            args = BenchArgs(
                root_addr=root_addr,
                rank=global_rank,
                num_ranks=num_ranks,
                cuda_dev=local_rank,
                size=size,
                comm=comm,
                round=20,
            )
            workers.append({
                "host": f"host{mid}",
                "bin": binary,
                "args": args.get_args(),
                "dependencies": dep,
            })
            global_rank += 1

    return {
        "name": name,
        "group": group,
        "worker": workers,
    }


def generate():
    os.makedirs("output", exist_ok=True)

    size_list = ["512M"]
    command = ["allreduce", "allgather"]
    node_config = [(1, 1), (2, 1), (3, 1), (4, 1)]  # host 0 and 1, each with 1 GPU
    root_node_id = 1
    group_name = "4GPU_TEST"
    config_path = "eval/single-app/4gpu.toml"
    communicator = 42

    for comm in command:
        for size in size_list:
            config = generate_config(
                name=f"{group_name}/{comm}/{size}",
                group=group_name,
                binary=comm + "_bench",
                root_id=root_node_id,
                machine_map=node_config,
                size=convert_size(size),
                comm=communicator,
                daemon_args=f"--config {config_path}",
            )
            with open(f"output/{group_name}_{comm}_{size}.toml", "w") as f:
                toml.dump(config, f)

generate()
