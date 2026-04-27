#include <memory>
#include <algorithm>
#include <time.h>

#include "BOAStar.h"

static void trace_vec_boa(std::ofstream &out, const std::vector<size_t> &v) {
    out << "[";
    for (size_t i = 0; i < v.size(); ++i) {
        if (i > 0) out << ",";
        out << v[i];
    }
    out << "]";
}

BOAStar::BOAStar(const AdjacencyMatrix &adj_matrix, Pair<double> eps, const LoggerPtr logger) :
    AbstractSolver(adj_matrix, {eps[0], eps[1]}, logger) {}

void BOAStar::operator()(size_t source, size_t target, Heuristic &heuristic, SolutionSet &solutions, unsigned int time_limit) {

    trace_step_ = 0;

    if (!trace_filename_.empty()) {
        trace_.open(trace_filename_);
        trace_ << "{\"type\":\"meta\",\"solver\":\"BOAStar\"}\n";
    }

    // int time_limit = 300;
    start_time = std::clock();
    this->start_logging(source, target);

    NodePtr node;
    NodePtr next;

    // Saving all the unused NodePtrs in a vector improves performace for some reason
    std::vector<NodePtr> closed;

    // Vector to hold mininum cost of 2nd criteria per node
    std::vector<size_t> min_g2(this->adj_matrix.size()+1, MAX_COST);

    // Init open heap
    Node::more_than_full_cost more_than;
    std::vector<NodePtr> open;
    std::make_heap(open.begin(), open.end(), more_than);

    node = std::make_shared<Node>(source, std::vector<size_t>(2,0), heuristic(source));
    open.push_back(node);
    std::push_heap(open.begin(), open.end(), more_than);

    while (open.empty() == false) {
        if ((std::clock() - start_time)/CLOCKS_PER_SEC > time_limit){
            if (trace_.is_open()) {
                trace_ << "{\"type\":\"final_solutions\",\"step\":" << trace_step_
                    << ",\"solutions\":[";
                bool first = true;

                for (auto solution = solutions.begin(); solution != solutions.end(); ++solution) {
                    if (!first) trace_ << ",";

                    trace_ << "{\"state\":" << (*solution)->id << ",\"f\":";
                    trace_vec_boa(trace_, (*solution)->f);
                    trace_ << "}";

                    first = false;
                }

                trace_ << "]}\n";
                trace_.close();
            }

            this->end_logging(solutions, false);
            return;
        }

        // Pop min from queue and process
        std::pop_heap(open.begin(), open.end(), more_than);
        node = open.back();
        open.pop_back();
        num_generation +=1;

        // Dominance check
        if ((((1+this->eps[1])*node->f[1]) >= min_g2[target]) ||
            (node->g[1] >= min_g2[node->id])) {
            closed.push_back(node);
            continue;
        }

        min_g2[node->id] = node->g[1];
        num_expansion += 1;


        if (node->id == target) {
            solutions.push_back(node);
            log_solution(node);
            continue;
        }

        // Check to which neighbors we should extend the paths
        const std::vector<Edge> &outgoing_edges = adj_matrix[node->id];
        for(auto p_edge = outgoing_edges.begin(); p_edge != outgoing_edges.end(); p_edge++) {
            size_t next_id = p_edge->target;
            std::vector<size_t> next_g = {node->g[0]+p_edge->cost[0], node->g[1]+p_edge->cost[1]};
            auto next_h = heuristic(next_id);

            // Dominance check
            if ((((1+this->eps[1])*(next_g[1]+next_h[1])) >= min_g2[target]) ||
                (next_g[1] >= min_g2[next_id])) {
                continue;
            }

            // If not dominated create node and push to queue
            // Creation is defered after dominance check as it is
            // relatively computational heavy and should be avoided if possible
            next = std::make_shared<Node>(next_id, next_g, next_h, node);

            open.push_back(next);
            std::push_heap(open.begin(), open.end(), more_than);

            closed.push_back(node);
        }
    }

    if (trace_.is_open()) {
        trace_ << "{\"type\":\"final_solutions\",\"step\":" << trace_step_
            << ",\"solutions\":[";
        bool first = true;

        for (auto solution = solutions.begin(); solution != solutions.end(); ++solution) {
            if (!first) trace_ << ",";

            trace_ << "{\"state\":" << (*solution)->id << ",\"f\":";
            trace_vec_boa(trace_, (*solution)->f);
            trace_ << "}";

            first = false;
        }

        trace_ << "]}\n";
        trace_.close();
    }

    this->end_logging(solutions);
}


inline bool is_dominated(SolutionSet & solutions, NodePtr node, Pair<double> eps = {0,0}){
    for (auto sol: solutions){
        if (sol->g[0] <= (1 + eps[0]) * node->g[0] + node->h[0] &&
            sol->g[1] <= (1 + eps[1]) * node->g[1] + node->h[1]
            ){
            return true;
        }
    }
    return false;
}




void BOAStar::log_solution(NodePtr node){
    solution_log.push_back({std::clock() - start_time, node});
}
