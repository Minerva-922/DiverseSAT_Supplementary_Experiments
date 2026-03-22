#!/bin/bash
# Batch submission script for all generated SLURM jobs
# Generated with FEWEST_TESTS mode enabled
# Total jobs: 15

echo 'Submitting jobslurm-2_QP_SE_CPLEX (Job: 2QSC, k=2, QP, SE, CPLEX, parallel=10)...'
sbatch jobslurm-2_QP_SE_CPLEX
sleep 1

echo 'Submitting jobslurm-2_DW_SE_CPLEX (Job: 2DSC, k=2, DW, SE, CPLEX, parallel=10)...'
sbatch jobslurm-2_DW_SE_CPLEX
sleep 1

echo 'Submitting jobslurm-2_IW_SE_CPLEX (Job: 2ISC, k=2, IW, SE, CPLEX, parallel=10)...'
sbatch jobslurm-2_IW_SE_CPLEX
sleep 1

echo 'Submitting jobslurm-2_BIN_SE_CPLEX (Job: 2BSC, k=2, BIN, SE, CPLEX, parallel=10)...'
sbatch jobslurm-2_BIN_SE_CPLEX
sleep 1

echo 'Submitting jobslurm-2_BIN_noSE_CPLEX (Job: 2BnC, k=2, BIN, noSE, CPLEX, parallel=10)...'
sbatch jobslurm-2_BIN_noSE_CPLEX
sleep 1

echo 'Submitting jobslurm-5_QP_SE_CPLEX (Job: 5QSC, k=5, QP, SE, CPLEX, parallel=10)...'
sbatch jobslurm-5_QP_SE_CPLEX
sleep 1

echo 'Submitting jobslurm-5_DW_SE_CPLEX (Job: 5DSC, k=5, DW, SE, CPLEX, parallel=10)...'
sbatch jobslurm-5_DW_SE_CPLEX
sleep 1

echo 'Submitting jobslurm-5_IW_SE_CPLEX (Job: 5ISC, k=5, IW, SE, CPLEX, parallel=10)...'
sbatch jobslurm-5_IW_SE_CPLEX
sleep 1

echo 'Submitting jobslurm-5_BIN_SE_CPLEX (Job: 5BSC, k=5, BIN, SE, CPLEX, parallel=10)...'
sbatch jobslurm-5_BIN_SE_CPLEX
sleep 1

echo 'Submitting jobslurm-5_BIN_noSE_CPLEX (Job: 5BnC, k=5, BIN, noSE, CPLEX, parallel=10)...'
sbatch jobslurm-5_BIN_noSE_CPLEX
sleep 1

echo 'Submitting jobslurm-10_QP_SE_CPLEX (Job: 10QSC, k=10, QP, SE, CPLEX, parallel=10)...'
sbatch jobslurm-10_QP_SE_CPLEX
sleep 1

echo 'Submitting jobslurm-10_DW_SE_CPLEX (Job: 10DSC, k=10, DW, SE, CPLEX, parallel=10)...'
sbatch jobslurm-10_DW_SE_CPLEX
sleep 1

echo 'Submitting jobslurm-10_IW_SE_CPLEX (Job: 10ISC, k=10, IW, SE, CPLEX, parallel=10)...'
sbatch jobslurm-10_IW_SE_CPLEX
sleep 1

echo 'Submitting jobslurm-10_BIN_SE_CPLEX (Job: 10BSC, k=10, BIN, SE, CPLEX, parallel=10)...'
sbatch jobslurm-10_BIN_SE_CPLEX
sleep 1

echo 'Submitting jobslurm-10_BIN_noSE_CPLEX (Job: 10BnC, k=10, BIN, noSE, CPLEX, parallel=10)...'
sbatch jobslurm-10_BIN_noSE_CPLEX
sleep 1

