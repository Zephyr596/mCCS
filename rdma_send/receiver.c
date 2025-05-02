// receiver.c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <rdma/rdma_cma.h>

#define MSG_SIZE (64 * 1024)
#define RECV_BUF_NUM 64

int main() {
    struct rdma_event_channel *ec = rdma_create_event_channel();
    struct rdma_cm_id *listen_id = NULL, *cm_id = NULL;
    struct rdma_cm_event *event;

    rdma_create_id(ec, &listen_id, NULL, RDMA_PS_TCP);
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(20000);
    rdma_bind_addr(listen_id, (struct sockaddr *)&addr);
    rdma_listen(listen_id, 1);

    rdma_get_cm_event(ec, &event);
    cm_id = event->id;
    rdma_ack_cm_event(event);

    struct ibv_pd *pd = ibv_alloc_pd(cm_id->verbs);
    struct ibv_cq *cq = ibv_create_cq(cm_id->verbs, RECV_BUF_NUM, NULL, NULL, 0);

    struct ibv_qp_init_attr qp_attr = {
        .send_cq = cq,
        .recv_cq = cq,
        .qp_type = IBV_QPT_RC,
        .cap = {
            .max_send_wr = 0,
            .max_recv_wr = RECV_BUF_NUM,
            .max_send_sge = 0,
            .max_recv_sge = 1,
        },
    };
    rdma_create_qp(cm_id, pd, &qp_attr);

    char *recv_bufs[RECV_BUF_NUM];
    struct ibv_mr *recv_mrs[RECV_BUF_NUM];
    for (int i = 0; i < RECV_BUF_NUM; ++i) {
        recv_bufs[i] = malloc(MSG_SIZE);
        memset(recv_bufs[i], 0, MSG_SIZE);
        recv_mrs[i] = ibv_reg_mr(pd, recv_bufs[i], MSG_SIZE, IBV_ACCESS_LOCAL_WRITE);

        struct ibv_sge sge = {
            .addr = (uintptr_t)recv_bufs[i],
            .length = MSG_SIZE,
            .lkey = recv_mrs[i]->lkey,
        };
        struct ibv_recv_wr wr = {
            .wr_id = i,
            .sg_list = &sge,
            .num_sge = 1,
        };
        struct ibv_recv_wr *bad_wr;
        ibv_post_recv(cm_id->qp, &wr, &bad_wr);
    }

    struct rdma_conn_param conn_param = {0};
    rdma_accept(cm_id, &conn_param);
    rdma_get_cm_event(ec, &event);
    rdma_ack_cm_event(event);

    printf("[Receiver] Ready to receive...\n");

    size_t received = 0, total_bytes = 0;
    time_t last_sec = time(NULL);

    while (1) {
        struct ibv_wc wc;
        while (ibv_poll_cq(cq, 1, &wc) < 1);

        if (wc.status != IBV_WC_SUCCESS) {
            fprintf(stderr, "[Receiver] WC error: %s\n", ibv_wc_status_str(wc.status));
            continue;
        }

        int idx = wc.wr_id % RECV_BUF_NUM;
        printf("[Receiver] Received: %.20s\n", recv_bufs[idx]);
        total_bytes += MSG_SIZE;
        received++;

        struct ibv_sge sge = {
            .addr = (uintptr_t)recv_bufs[idx],
            .length = MSG_SIZE,
            .lkey = recv_mrs[idx]->lkey,
        };
        struct ibv_recv_wr wr = {
            .wr_id = idx,
            .sg_list = &sge,
            .num_sge = 1,
        };
        struct ibv_recv_wr *bad_wr;
        ibv_post_recv(cm_id->qp, &wr, &bad_wr);

        time_t now = time(NULL);
        if (now != last_sec) {
            double mbps = total_bytes / 1e6;
            printf("[Receiver] Receive rate: %.2f MB/s (%zu msgs/s)\n", mbps, received);
            total_bytes = 0;
            received = 0;
            last_sec = now;
        }
    }
    return 0;
}

