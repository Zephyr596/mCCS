#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <pthread.h>
#include <rdma/rdma_cma.h>
#include <arpa/inet.h>

#define MSG_SIZE (64 * 1024)
#define TARGET_BW (9.4e9)
#define INTERVAL_NS ((uint64_t)(1e9 * MSG_SIZE / TARGET_BW)) // 每线程目标速率（默认线程数=1）

struct send_thread_args {
    struct ibv_qp *qp;
    struct ibv_mr *mr;
    char *buf;
    int thread_id;
    int total_threads;
    uint32_t lkey;
};

void *send_thread(void *arg_ptr) {
    struct send_thread_args *args = (struct send_thread_args *)arg_ptr;
    struct timespec next;
    clock_gettime(CLOCK_MONOTONIC, &next);
    size_t sent = 0;

    while (1) {
        snprintf(args->buf, 64, "Thread %d Pkt %ld", args->thread_id, sent++);

        struct ibv_sge sge = {
            .addr = (uintptr_t)args->buf,
            .length = MSG_SIZE,
            .lkey = args->lkey,
        };

        struct ibv_send_wr wr = {
            .wr_id = sent,
            .sg_list = &sge,
            .num_sge = 1,
            .opcode = IBV_WR_SEND,
            .send_flags = (sent % 64 == 0) ? IBV_SEND_SIGNALED : 0,
        };

        struct ibv_send_wr *bad_wr;
        ibv_post_send(args->qp, &wr, &bad_wr);

        if (sent % 64 == 0) {
            struct ibv_wc wc;
            while (ibv_poll_cq(args->qp->send_cq, 1, &wc) < 1);
        }

        // 控制速率
        next.tv_nsec += INTERVAL_NS / args->total_threads;
        while (next.tv_nsec >= 1e9) {
            next.tv_nsec -= 1e9;
            next.tv_sec += 1;
        }
        clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &next, NULL);
    }
    return NULL;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <receiver_ip> [num_threads]\n", argv[0]);
        return 1;
    }

    int num_threads = (argc >= 3) ? atoi(argv[2]) : 4;

    struct rdma_cm_id *cm_id = NULL;
    struct rdma_event_channel *ec = rdma_create_event_channel();
    rdma_create_id(ec, &cm_id, NULL, RDMA_PS_TCP);

    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(20000);
    inet_pton(AF_INET, argv[1], &addr.sin_addr);

    rdma_resolve_addr(cm_id, NULL, (struct sockaddr *)&addr, 2000);
    struct rdma_cm_event *event;
    rdma_get_cm_event(ec, &event); rdma_ack_cm_event(event);
    rdma_resolve_route(cm_id, 2000);
    rdma_get_cm_event(ec, &event); rdma_ack_cm_event(event);

    struct ibv_pd *pd = ibv_alloc_pd(cm_id->verbs);
    struct ibv_cq *cq = ibv_create_cq(cm_id->verbs, 256, NULL, NULL, 0);

    struct ibv_qp_init_attr qp_attr = {
        .send_cq = cq,
        .recv_cq = cq,
        .qp_type = IBV_QPT_RC,
        .cap = {
            .max_send_wr = 256,
            .max_recv_wr = 0,
            .max_send_sge = 1,
            .max_recv_sge = 0,
        },
    };
    rdma_create_qp(cm_id, pd, &qp_attr);

    struct rdma_conn_param conn_param = {
        .initiator_depth = 1,
        .responder_resources = 1,
        .retry_count = 7,
    };
    rdma_connect(cm_id, &conn_param);
    rdma_get_cm_event(ec, &event); rdma_ack_cm_event(event);

    printf("Connected. Launching %d threads for ~%.2f GB/s total...\n",
           num_threads, 9.4 * num_threads / 4.0);

    // 分配线程与缓冲
    pthread_t threads[num_threads];
    struct send_thread_args args[num_threads];

    for (int i = 0; i < num_threads; ++i) {
        args[i].buf = malloc(MSG_SIZE);
        args[i].mr = ibv_reg_mr(pd, args[i].buf, MSG_SIZE, IBV_ACCESS_LOCAL_WRITE);
        args[i].qp = cm_id->qp;
        args[i].thread_id = i;
        args[i].total_threads = num_threads;
        args[i].lkey = args[i].mr->lkey;
        pthread_create(&threads[i], NULL, send_thread, &args[i]);
    }

    // join 保持主线程不退出
    for (int i = 0; i < num_threads; ++i) {
        pthread_join(threads[i], NULL);
    }

    return 0;
}

