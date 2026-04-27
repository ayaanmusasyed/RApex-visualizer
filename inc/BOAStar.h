#ifndef BI_CRITERIA_BOA_STAR_H
#define BI_CRITERIA_BOA_STAR_H

#include <vector>
#include <fstream>
#include "Utils/Definitions.h"
#include "Utils/Logger.h"
#include "AbstractSolver.h"

class BOAStar: public AbstractSolver {
protected:
    std::clock_t start_time;

    std::vector<std::pair<std::clock_t, NodePtr>> solution_log;
    void log_solution(NodePtr);

    std::ofstream trace_;
    std::string trace_filename_;
    int trace_step_ = 0;
public:
    virtual std::string get_solver_name() {return "BOA*"; }

    BOAStar(const AdjacencyMatrix &adj_matrix, Pair<double> eps, const LoggerPtr logger=nullptr);

    void operator()(size_t source, size_t target, Heuristic &heuristic, SolutionSet &solutions, unsigned int time_limit=UINT_MAX);

    std::vector<std::pair<std::clock_t, NodePtr>> get_sol_log(){return solution_log;}

    void set_trace_file(const std::string &fname) {
        trace_filename_ = fname;
    }

};




#endif //BI_CRITERIA_BOA_STAR_H
