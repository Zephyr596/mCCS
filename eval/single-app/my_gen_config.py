import toml
import os

# Hostname or IP address of each VM
addrs = {
    "host1": "10.33.120.103",
    "host2": "10.33.120.104",
}


class BenchArgs:
    def __init__(self, root_addr, rank, num_ranks, cuda_dev, size, comm, round) -> None:
        self.root_addr = root_addr
        self.rank = rank
        self.num_ranks = num_ranks
        self.cuda_dev = cuda_dev
        self.size = size
        self.comm = comm
        self.round = round

    def get_args(self):
        # Format the arguments for CLI usage
        return f"--root-addr {self.root_addr} --rank {self.rank} " \
               f"--num-ranks {self.num_ranks} --cuda-device-idx {self.cuda_dev} " \
               f"--size {self.size} --communicator {self.comm} --round {self.round} --size-in-byte"


def convert_size(size: str):
    # Convert human-readable size string to integer bytes
    if size.endswith("K"):
        return int(size[:-1]) * 1024
    elif size.endswith("M"):
        return int(size[:-1]) * 1024 * 1024
    elif size.endswith("G"):
        return int(size[:-1]) * 1024 * 1024 * 1024
    return int(size)


def generate_2vm_config(
    name: str,
    binary: str,
    daemon_args: str,
    size_list,
    comm_id: int = 42,
    round: int = 20,
    out_dir: str = "output",
):
    os.makedirs(out_dir, exist_ok=True)

    root = "vm1"  # The root node used for communication
    machines = [("vm1", 1), ("vm2", 1)]  # Each VM uses 1 GPU

    for size_str in size_list:
        size_bytes = convert_size(size_str)
        config = {
            "name": name,
            "group": name,
            "worker": []
        }

        # Add mccs daemons (one per VM)
        for vm_name, _ in machines:
            config["worker"].append({
                "host": vm_name,
                "bin": "mccs",
                "args": f"--host {vm_name} {daemon_args}",
                "weak": True,
                "dependencies": [],
            })

        # Add benchmark workers (e.g., allreduce_bench)
        total_ranks = sum(g for _, g in machines)
        global_rank = 0
        for vm_name, gpu_cnt in machines:
            for local_rank in range(gpu_cnt):
                args = BenchArgs(
                    root_addr=addrs[root],
                    rank=global_rank,
                    num_ranks=total_ranks,
                    cuda_dev=local_rank,
                    size=size_bytes,
                    comm=comm_id,
                    round=round,
                )
                config["worker"].append({
                    "host": vm_name,
                    "bin": binary,
                    "args": args.get_args(),
                    "dependencies": [0, 1],  # indexes of daemons
                })
                global_rank += 1

        # Save the TOML file
        out_path = f"{out_dir}/{name}_{binary}_{size_str}.toml"
        with open(out_path, "w") as f:
            toml.dump(config, f)
        print(f"✅ Saved: {out_path}")


# ✨ Run to generate TOML config files
generate_2vm_config(
    name="2VM_1NODE",
    binary="allreduce_bench",
    daemon_args="--config eval/single-app/2vm.toml",
    size_list=["32K", "128K", "512K", "2M", "8M", "32M", "128M", "512M"],
    comm_id=42,
)
