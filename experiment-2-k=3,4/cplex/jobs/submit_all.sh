#!/bin/bash
# Batch submission script for all generated SLURM jobs (experiment-2, k=3,4)
# Total jobs: 8

echo 'Submitting jobslurm-3_QP_SE_CPLEX (Job: 3QSC, k=3, QP, SE, CPLEX, parallel=10)...'
sbatch jobslurm-3_QP_SE_CPLEX
sleep 1

echo 'Submitting jobslurm-3_DW_SE_CPLEX (Job: 3DSC, k=3, DW, SE, CPLEX, parallel=10)...'
sbatch jobslurm-3_DW_SE_CPLEX
sleep 1

echo 'Submitting jobslurm-3_IW_SE_CPLEX (Job: 3ISC, k=3, IW, SE, CPLEX, parallel=10)...'
sbatch jobslurm-3_IW_SE_CPLEX
sleep 1

echo 'Submitting jobslurm-3_BIN_SE_CPLEX (Job: 3BSC, k=3, BIN, SE, CPLEX, parallel=10)...'
sbatch jobslurm-3_BIN_SE_CPLEX
sleep 1

echo 'Submitting jobslurm-4_QP_SE_CPLEX (Job: 4QSC, k=4, QP, SE, CPLEX, parallel=10)...'
sbatch jobslurm-4_QP_SE_CPLEX
sleep 1

echo 'Submitting jobslurm-4_DW_SE_CPLEX (Job: 4DSC, k=4, DW, SE, CPLEX, parallel=10)...'
sbatch jobslurm-4_DW_SE_CPLEX
sleep 1

echo 'Submitting jobslurm-4_IW_SE_CPLEX (Job: 4ISC, k=4, IW, SE, CPLEX, parallel=10)...'
sbatch jobslurm-4_IW_SE_CPLEX
sleep 1

echo 'Submitting jobslurm-4_BIN_SE_CPLEX (Job: 4BSC, k=4, BIN, SE, CPLEX, parallel=10)...'
sbatch jobslurm-4_BIN_SE_CPLEX
sleep 1

