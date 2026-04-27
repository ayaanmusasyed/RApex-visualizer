#pragma once

#include <vector>
#include "Utils/Definitions.h"
#include "Utils/Logger.h"
#include "AbstractSolver.h"
#include <fstream>

class NAMOAdr: public AbstractSolver {
protected:

    std::ofstream trace_;
    std::string trace_filename_;
    int trace_step_ = 0;


public:

    NAMOAdr(const AdjacencyMatrix &adj_matrix, EPS eps, const LoggerPtr logger=nullptr):     AbstractSolver(adj_matrix, eps, logger) {}

    virtual std::string get_solver_name() {return "NAMOAdr"; }

    void operator()(size_t source, size_t target, Heuristic &heuristic, SolutionSet &solutions, unsigned int time_limit=UINT_MAX) override;

    void set_trace_file(const std::string &fname) {
        trace_filename_ = fname;
    }
};


